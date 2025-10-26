from __future__ import annotations


import os
import sys
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
)
from pydantic import BaseModel, Field, validator, model_validator
from starlette.staticfiles import StaticFiles

# Ensure project root is importable
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

# Import simulation core
from hackathon_simulation import (  # noqa: E402
    AgentProfile,
    HackathonSimulator,
    SimulationConfig,
    summary_to_dict,
)

# ------------------------------------------------------------------------------
# App setup
# ------------------------------------------------------------------------------

app = FastAPI(
    title="Hackathon Simulation API",
    version="0.1.0",
    description=(
        "FastAPI server for running hackathon simulations. "
        "POST /simulate with participants and options; open / to load the web UI."
    ),
)

# CORS for local development and embedding
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional static mounting (place your index.html and assets in ./static)
STATIC_DIR = ROOT / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ------------------------------------------------------------------------------
# Request/Response models
# ------------------------------------------------------------------------------


class Participant(BaseModel):
    name: str = Field(..., description="Participant's name")
    idea: Optional[str] = Field(None, description="Initial idea")
    role: Optional[str] = Field(None, description="Role or short tagline")
    comments: Optional[str] = Field(
        None, description="Optional comments, can be used as idea fallback"
    )

    @model_validator(mode="after")
    def ensure_idea_or_comments(self):
        name = (self.name or "").strip()
        idea = (self.idea or "").strip()
        comments = (self.comments or "").strip()
        if not name:
            raise ValueError("Participant name is required.")
        if not idea and not comments:
            raise ValueError(f"Participant '{name}' needs either an idea or comments.")
        return self


class SimulationOptions(BaseModel):
    runs: int = Field(3, ge=1, le=20)
    min_team_size: int = Field(2, ge=1, le=10)
    max_team_size: int = Field(4, ge=1, le=10)
    pivot_base_chance: float = Field(0.35, ge=0.0, le=1.0)
    research_trigger: float = Field(0.45, ge=0.0, le=1.0)
    seed: int = Field(42, ge=0, le=100_000)
    llm_model: str = Field("gemini-flash-latest")
    llm_temperature: float = Field(0.9, ge=0.0, le=1.5)
    llm_call_cap: int = Field(10, ge=1, le=10_000)
    conversation_rounds: int = Field(6, ge=1, le=24)

    @validator("max_team_size")
    def validate_team_range(cls, v, values):
        min_team = values.get("min_team_size", 1)
        if v < min_team:
            raise ValueError("max_team_size must be >= min_team_size")
        return v


class SimulationRequest(BaseModel):
    participants: List[Participant]
    options: SimulationOptions = Field(default_factory=SimulationOptions)
    google_api_key: Optional[str] = Field(
        None,
        description="Google Generative AI API key. Required unless already provided via env (GOOGLE_API_KEY or GEMINI_API_KEY).",
    )


class SimulationResponse(BaseModel):
    ok: bool
    summary: dict
    progress: List[str] = Field(default_factory=list)
    message: Optional[str] = None


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------


def _build_profiles(participants: List[Participant]) -> List[AgentProfile]:
    profiles: List[AgentProfile] = []
    for p in participants:
        name = (p.name or "").strip()
        idea = (p.idea or "").strip()
        comments = (p.comments or "").strip()
        role = (p.role or "").strip()

        final_idea = idea or comments
        final_role = role or comments or "Contributor"

        profiles.append(
            AgentProfile(
                name=name,
                role=final_role,
                idea=final_idea,
                skills=[],
                personality="Adaptive Collaborator",
                motivation="Ship a standout hackathon project fast.",
                xp_level="mid",
            )
        )
    return profiles


def _ensure_api_key(key_from_request: Optional[str]) -> None:
    key = (
        key_from_request
        or os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
    )
    if not key:
        raise HTTPException(
            status_code=400,
            detail="Missing API key. Provide google_api_key in request or set GOOGLE_API_KEY/GEMINI_API_KEY in the environment.",
        )
    # Prefer GOOGLE_API_KEY; the library will accept either
    os.environ["GOOGLE_API_KEY"] = key
    os.environ["GEMINI_API_KEY"] = key


def _build_config(opts: SimulationOptions) -> SimulationConfig:
    return SimulationConfig(
        runs=opts.runs,
        min_team_size=opts.min_team_size,
        max_team_size=opts.max_team_size,
        pivot_base_chance=opts.pivot_base_chance,
        research_trigger=opts.research_trigger,
        seed=opts.seed,
        llm_model=opts.llm_model,
        llm_temperature=opts.llm_temperature,
        llm_call_cap=opts.llm_call_cap,
        conversation_rounds=opts.conversation_rounds,
    )


def _default_index_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Hackathon Simulation</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    :root {{
      --bg: #0b1020;
      --panel: #131a2e;
      --text: #e6ecff;
      --muted: #a7b0d8;
      --accent: #6aa6ff;
      --accent-2: #9b6bff;
      --ok: #60d394;
      --warn: #f7b955;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; padding: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
      color: var(--text); background: radial-gradient(1200px 800px at 10% 0%, #0f1630, #070b19 60%);
      min-height: 100vh; display: flex; align-items: center; justify-content: center;
    }}
    .wrap {{ width: 100%; max-width: 1100px; padding: 24px; }}
    .card {{
      background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 16px; padding: 20px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.4), inset 0 0 50px rgba(255,255,255,0.03);
      backdrop-filter: blur(6px);
    }}
    h1 {{ margin: 0 0 6px; letter-spacing: 0.5px; font-weight: 700; }}
    p.lead {{ color: var(--muted); margin: 0 0 18px; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    .grid > div {{ padding: 12px; background: rgba(255,255,255,0.03); border-radius: 12px; border: 1px solid rgba(255,255,255,0.06);}}
    label {{ display: block; font-size: 12px; color: var(--muted); margin-bottom: 6px; }}
    input, textarea, select {{
      width: 100%; padding: 10px 12px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.08);
      background: #0c1226; color: var(--text); outline: none; font-size: 14px;
    }}
    textarea {{ min-height: 58px; resize: vertical; }}
    button {{
      padding: 10px 14px; border-radius: 10px; border: 0; font-weight: 600; cursor: pointer; color: #0b1020;
      background: linear-gradient(135deg, var(--accent), var(--accent-2)); box-shadow: 0 8px 20px rgba(106,166,255,0.35);
    }}
    .row {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }}
    .muted {{ color: var(--muted); font-size: 12px; }}
    .status {{ margin-top: 10px; font-size: 13px; }}
    .ok {{ color: var(--ok); }}
    .warn {{ color: var(--warn); }}
    pre {{
      white-space: pre-wrap; word-break: break-word; font-size: 12px; background: #0a0f22;
      border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 12px; max-height: 420px; overflow: auto;
    }}
    .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>Hackathon Simulation</h1>
      <p class="lead">Bring a roster, run multi-round sims, and see which ideas stick. Powered by Gemini insights.</p>

      <div class="grid" style="margin-bottom: 14px;">
        <div>
          <label>Google API Key</label>
          <input id="apiKey" type="password" placeholder="GOOGLE_API_KEY or GEMINI_API_KEY" />
          <div class="muted">Your key is used only for the simulation request.</div>
        </div>
        <div>
          <label>Options</label>
          <div class="row">
            <input id="runs" type="number" min="1" max="20" value="3" />
            <input id="rounds" type="number" min="1" max="24" value="6" />
            <input id="seed" type="number" min="0" max="100000" value="42" />
          </div>
          <div class="row" style="margin-top: 6px;">
            <input id="model" value="gemini-flash-latest" />
            <input id="temp" type="number" step="0.05" min="0" max="1.5" value="0.9" />
            <input id="cap" type="number" min="1" max="5000" value="10" />
          </div>
        </div>
      </div>

      <div class="grid">
        <div>
          <label>Participants (Name | Idea | Comments)</label>
          <textarea id="roster" placeholder="Casey Vega | Agentic QA bot interviewing power users nightly | Exploring QA automation for support teams
Avery Lin | AI-driven sprint reviewer | —"></textarea>
          <div class="muted">Enter each on a new line. At least an idea or comments is required.</div>
        </div>
        <div>
          <label>&nbsp;</label>
          <button id="run">Run simulation</button>
          <div id="status" class="status"></div>
        </div>
      </div>

      <div class="two-col" style="margin-top:16px;">
        <div>
          <label>Progress</label>
          <pre id="progress"></pre>
        </div>
        <div>
          <label>Summary (JSON)</label>
          <pre id="output"></pre>
        </div>
      </div>
    </div>
  </div>

  <script>
    function parseRoster(text) {{
      const lines = (text || "").split(/\\n+/).map(s => s.trim()).filter(Boolean);
      return lines.map(line => {{
        const parts = line.split("|").map(s => s.trim());
        const [name, idea = "", comments = ""] = parts.length === 3
          ? [parts[0], parts[1], parts[2]]
          : [parts[0], parts[1] || "", parts[2] || ""];
        return {{ name, idea, comments }};
      }}).filter(p => p.name);
    }}

    async function run() {{
      const statusEl = document.getElementById("status");
      const apiKey = document.getElementById("apiKey").value.trim();
      const runs = parseInt(document.getElementById("runs").value || "3", 10);
      const rounds = parseInt(document.getElementById("rounds").value || "6", 10);
      const seed = parseInt(document.getElementById("seed").value || "42", 10);
      const model = document.getElementById("model").value || "gemini-flash-latest";
      const temp = parseFloat(document.getElementById("temp").value || "0.9");
      const cap = parseInt(document.getElementById("cap").value || "10", 10);
      const participants = parseRoster(document.getElementById("roster").value);

      if (!participants.length) {{
        statusEl.textContent = "Please enter at least one participant.";
        statusEl.className = "status warn";
        return;
      }}
      statusEl.textContent = "Running...";
      statusEl.className = "status";

      const body = {{
        participants,
        google_api_key: apiKey || null,
        options: {{
          runs, conversation_rounds: rounds, seed, llm_model: model, llm_temperature: temp, llm_call_cap: cap,
          min_team_size: 2, max_team_size: 4, pivot_base_chance: 0.35, research_trigger: 0.45
        }}
      }};
      try {{
        const resp = await fetch("/simulate", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(body)
        }});
        const data = await resp.json();
        if (!resp.ok || !data.ok) {{
          throw new Error(data.message || (data.detail && data.detail[0]?.msg) || "Simulation failed");
        }}
        document.getElementById("output").textContent = JSON.stringify(data.summary, null, 2);
        document.getElementById("progress").textContent = (data.progress || []).slice(-120).map(s => "- " + s).join("\\n");
        statusEl.textContent = "Done";
        statusEl.className = "status ok";
      }} catch (err) {{
        statusEl.textContent = "Error: " + err.message;
        statusEl.className = "status warn";
      }}
    }}

    document.getElementById("run").addEventListener("click", run);
  </script>
</body>
</html>
"""  # noqa: E501


# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------


@app.get("/healthz")
def health() -> JSONResponse:
    return JSONResponse({"ok": True, "status": "healthy"})


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    """
    Try serving ./static/index.html if present; otherwise render a built-in UI.
    """
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return HTMLResponse(_default_index_html())


@app.post("/simulate", response_model=SimulationResponse)
def simulate(payload: SimulationRequest, request: Request) -> JSONResponse:
    # Ensure API key presence (request-body or environment)
    _ensure_api_key(payload.google_api_key)

    # Build profiles and config
    try:
        profiles = _build_profiles(payload.participants)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    config = _build_config(payload.options)

    # Run simulation with progress capture
    simulator = HackathonSimulator(profiles, config=config)
    progress: List[str] = []

    def hook(message: str) -> None:
        # Keep last N for response size control
        progress.append(message)
        if len(progress) > 500:
            del progress[:200]

    simulator.set_progress_hook(hook)

    try:
        summary = simulator.run()
    except Exception as exc:
        # Surface clean error to client
        return JSONResponse(
            status_code=400,
            content=SimulationResponse(
                ok=False,
                summary={},
                progress=progress,
                message=str(exc),
            ).dict(),
        )

    return JSONResponse(
        SimulationResponse(
            ok=True,
            summary=summary_to_dict(summary),
            progress=progress,
            message=None,
        ).dict()
    )


# ------------------------------------------------------------------------------
# Local dev entrypoint
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    # To run locally:
    #   pip install fastapi uvicorn pydantic[dotenv] "starlette>=0.36.0"
    #   export GOOGLE_API_KEY=your_key  # or pass google_api_key in request body
    #   uvicorn server:app --reload --port 8000
    try:
        import uvicorn  # type: ignore
    except Exception:  # pragma: no cover
        print(
            "Uvicorn is not installed. Install with:\n"
            "  python3 -m pip install uvicorn fastapi starlette pydantic\n"
            "Then run:\n"
            "  uvicorn server:app --reload --port 8000",
            file=sys.stderr,
        )
        raise SystemExit(1)
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        reload=True,
    )
