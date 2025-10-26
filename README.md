## Hackathon Simulation Sandbox

This project stress-tests hackathon ideas by simulating short iterative rounds. Each run assembles teams from rich participant profiles, models ideation and critique dynamics, applies pivot pressure, and scores the outcomes. Re-running the simulation surfaces consistent winners, highlights why they work, and produces six-hour execution plans teams can actually follow.

### Why it’s useful
- Explore team formation dynamics before the hackathon starts.
- Compare idea resilience under critique, pivots, and research pressure.
- Generate crisp summaries, leaderboards, and action plans you can share.

### Quick start
```bash
uv sync   # or pip install -r requirements if you prefer
python3 main.py --runs 2 --seed 13
```

### CLI options
- `--profiles path/to/profiles.json` — custom participant roster.
- `--team-size 3-5` — min/max team size.
- `--runs 8` and `--seed 99` — control reproducibility.
- `--json-out results/run.json` or `--markdown-out results/summary.md` — export data for sharing.

### Streamlit dashboard
```bash
streamlit run streamlit_app/app.py
```
You’ll get sliders for run counts, team ranges, pivot pressure, and research appetite. Upload a custom JSON roster or use the built-in sample. The app renders:
- Per-run breakdowns with conversations, pivots, and scoring.
- Aggregated leaderboard with reasoning highlights.
- Download buttons for the same JSON/Markdown exports as the CLI.

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
