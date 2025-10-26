## Hackathon Simulation Sandbox

This project stress-tests hackathon ideas by simulating short iterative rounds. Each run assembles teams from rich participant profiles, models ideation and critique dynamics, applies pivot pressure, and scores the outcomes. Re-running the simulation surfaces consistent winners, highlights why they work, and produces six-hour execution plans teams can actually follow.

### Why it’s useful
- Explore team formation dynamics before the hackathon starts.
- Compare idea resilience under critique, pivots, and research pressure.
- Generate crisp summaries, leaderboards, and action plans you can share.

### Quick start
- System Python (no virtualenv):
  ```bash
  python3 -m pip install --upgrade pip
  python3 -m pip install streamlit langchain langchain-google-genai
  export GOOGLE_API_KEY=your_key  # required for Gemini-backed simulation
  python3 main.py --runs 2 --seed 13 --profiles data/profiles.json
  ```
- Optional isolated setup:
  ```bash
  python3 -m venv .venv && source .venv/bin/activate
  pip install -e .
  export GOOGLE_API_KEY=your_key
  python3 main.py --runs 2 --seed 13 --profiles data/profiles.json
  ```

### CLI options
- `--profiles path/to/profiles.json` — required; JSON list of participants.
- `--team-size 3-5` — min/max team size.
- `--runs 8` and `--seed 99` — control reproducibility.
- `--json-out results/run.json` or `--markdown-out results/summary.md` — export data for sharing.
- `--llm-call-cap 250` — adjust the per-simulation Gemini request budget (default 500).

### Streamlit dashboard
```bash
streamlit run streamlit_app/app.py
```
You’ll get sliders for run counts, team ranges, pivot pressure, and research appetite. Enter each participant’s name, role, and idea directly in the roster form (no defaults). The app renders:
- Per-run breakdowns with conversations, pivots, and scoring.
- Aggregated leaderboard with reasoning highlights.
- Download buttons for the same JSON/Markdown exports as the CLI.

### LLM-powered insights (optional)
- Requires a Google Generative AI key (`GOOGLE_API_KEY`).
- CLI example:
  ```bash
  export GOOGLE_API_KEY=your_key
  python3 main.py --runs 2 --llm-model gemini-1.5-flash --profiles data/profiles.json
  ```
- Each run now calls Gemini at every major phase (alignment, blending, critique, pivot, research, wrap-up) to surface dynamic agent chatter—very similar to the `genagents` style loops. A call budget (default 500) avoids runaway costs.
- Streamlit: paste your `GOOGLE_API_KEY`, choose model/temperature/budget, and run.
- Missing keys or misconfigured dependencies now stop the run immediately so you never read heuristic placeholders.

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
