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
  export GOOGLE_API_KEY=your_key  # optional but unlocks richer insights
  python3 main.py --runs 2 --seed 13
  ```
- Optional isolated setup:
  ```bash
  python3 -m venv .venv && source .venv/bin/activate
  pip install -e .
  python3 main.py --runs 2 --seed 13
  ```

### CLI options
- `--profiles path/to/profiles.json` — custom participant roster.
- `--team-size 3-5` — min/max team size.
- `--runs 8` and `--seed 99` — control reproducibility.
- `--json-out results/run.json` or `--markdown-out results/summary.md` — export data for sharing.
- `--no-llm` — opt out of API calls (defaults to on).
- `--llm-call-cap 250` — adjust the per-simulation Gemini request budget (default 500).

### Streamlit dashboard
```bash
streamlit run streamlit_app/app.py
```
You’ll get sliders for run counts, team ranges, pivot pressure, and research appetite. Paste agents into the text area, upload JSON, or fall back to the sample roster. The app renders:
- Per-run breakdowns with conversations, pivots, and scoring.
- Aggregated leaderboard with reasoning highlights.
- Download buttons for the same JSON/Markdown exports as the CLI.

### LLM-powered insights (optional)
- Requires a Google Generative AI key (`GOOGLE_API_KEY`).
- CLI example:
  ```bash
  export GOOGLE_API_KEY=your_key
  python3 main.py --runs 2 --use-llm --llm-model gemini-1.5-flash
  ```
- Each run now calls Gemini at every major phase (alignment, blending, critique, pivot, research, wrap-up) to surface dynamic agent chatter—very similar to the `genagents` style loops. A call budget (default 500) avoids runaway costs.
- Streamlit: toggle **Use Gemini LLM insights** and paste the key (stored locally for the session).
- If no key is present the simulator prints a one-time warning and falls back to heuristic insights automatically.

### Custom profiles
Supply a JSON array where each entry contains:
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
Only `name`, `role`, and `idea` are required.

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
