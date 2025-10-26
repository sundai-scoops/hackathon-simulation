## Hackathon Simulation Sandbox

This project stress-tests hackathon ideas by simulating organic conversation loops. Participants arrive with their own concepts, riff together, decide when to join forces, and evolve (or abandon) ideas based on live Gemini feedback. Re-running the simulation surfaces ideas that keep momentum, highlights why teams pivot, and produces six-hour execution plans hackers can actually follow.

### Why it’s useful
- Watch how conversations organically form (or fizzle) before a hackathon begins.
- Compare idea resilience under critique, research pressure, and pivot conversations.
- Generate crisp summaries, leaderboards, and action plans you can share.

### Quick start
- System Python (no virtualenv):
  ```bash
  python3 -m pip install --upgrade pip
  python3 -m pip install streamlit google-genai
  export GEMINI_API_KEY=your_key  # or GOOGLE_API_KEY
  python3 main.py --runs 2 --seed 13 --profiles data/profiles.json
  ```
- Optional isolated setup:
  ```bash
  python3 -m venv .venv && source .venv/bin/activate
  pip install -e .
  export GEMINI_API_KEY=your_key
  python3 main.py --runs 2 --seed 13 --profiles data/profiles.json
  ```

### CLI options
- `--profiles path/to/profiles.json` — required; JSON list of participants.
- `--runs 8` and `--seed 99` — run count and deterministic base seed.
- `--rounds 6` — conversation rounds per run.
- `--json-out results/run.json` or `--markdown-out results/summary.md` — export data for sharing.
- `--llm-call-cap 10` — adjust the per-simulation Gemini request budget (default 10).

### Streamlit dashboard
```bash
streamlit run streamlit_app/app.py
```
You’ll get controls for participant count, conversation rounds, Gemini model/budget, and base seed. Enter each participant’s name, role, and idea directly in the roster form (no defaults). The app renders:
- Per-run breakdowns with conversations, pivots, and scoring.
- Aggregated leaderboard with reasoning highlights.
- Download buttons for the same JSON/Markdown exports as the CLI.

### LLM-powered insights (optional)
- Requires a Google Generative AI key (`GEMINI_API_KEY` or `GOOGLE_API_KEY`).
- CLI example:
  ```bash
  export GOOGLE_API_KEY=your_key
  python3 main.py --runs 2 --llm-model gemini-flash-latest --profiles data/profiles.json
  ```
- Each run now calls Gemini at every major phase (alignment, blending, critique, pivot, research, wrap-up) to surface dynamic agent chatter—very similar to the `genagents` style loops. A call budget (default 10) avoids runaway costs, requests are throttled to one every two seconds, and the simulation ends early with partial results once the budget is exhausted.
- Streamlit: paste your `GEMINI_API_KEY` (or `GOOGLE_API_KEY`), choose model/temperature/budget (default `gemini-flash-latest`), and run.
- Missing keys or misconfigured dependencies now stop the run immediately so you never read heuristic placeholders.
- Tip: run `curl -H "Authorization: Bearer $GOOGLE_API_KEY" https://generativelanguage.googleapis.com/v1beta/models` to confirm the exact model ids your key can access.

### Custom profiles
The CLI expects a JSON array where each entry contains at least:
```jsonc
{
  "name": "Casey Vega",
  "role": "AI Product Manager",
  "idea": "Agentic QA bot interviewing power users nightly.",
  "skills": ["product", "prompt_engineering", "analysis"],
  "personality": "Systems Thinker",
  "motivation": "Keep the roadmap honest.",
  "xp_level": "senior"
}
```
Only `name`, `role`, and `idea` are required; additional fields are optional.

### How the simulation flows
- **Conversation rounds** *(default 6)* — every round, the simulator pairs or triads people based on idea affinity and complementary skills, then captures a Gemini-scribed recap.
- **Emergent clusters** — when conversations go well, participants align on a new consensus idea and become a cluster; others continue exploring solo.
- **Hard interaction budget** — the Gemini call cap (default 10) is treated as the global interaction budget. When it runs out, the simulation stops immediately and returns the partial state.
- **Determinism** — set `--seed` (CLI) or the “Base seed” slider (Streamlit) to replay the same conversational arc with the same roster.
- **Table-friendly input** — In Streamlit you can paste a tabular roster (e.g., copy/paste from Google Sheets with columns `Name`, `Role`, `Idea`) and import it directly into the form.

### Project layout
- `hackathon_simulation/` — modular core (models, profiles, engine, exports, helpers).
- `main.py` — CLI entry point.
- `streamlit_app/app.py` — interactive dashboard.
- `PLAN.md` — living roadmap with status notes and inspiration links.

### Next exploration ideas
1. Layer real LLM conversations on top of the scoring engine (see `genagents`, `autogen` repos).
2. Add persistence for run histories and auto-generated briefs.
3. Plug in real user-research transcripts to tighten validation loops.

---
Questions or ideas? Drop them in `PLAN.md`, run a new simulation, and iterate. Happy hacking!
