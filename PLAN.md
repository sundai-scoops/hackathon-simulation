## Hackathon Simulation Plan

### Current Snapshot

- **Plan tracker** — ✅ `PLAN.md` now doubles as the project log.
- **Modular core** — ✅ Simulation engine moved into `hackathon_simulation/` for reuse.
- **UI & exports** — ✅ Streamlit and CLI share the same summary/serialization helpers.
- **LLM insights** — ✅ Gemini hooks land multi-phase narrative riffs when keys are present (default on, capped @ 10 calls, throttled).
- **Conversation engine** — ✅ Agents chat first, form clusters organically, and hard-stop once the call budget is exhausted.
- **Roster UX** — ✅ Streamlit supports table pasting (Name | Idea | Comments) + live progress logging.
- **Roster input** — ✅ No more sample agents; UI/CLI require explicit name/role/idea lists.

### Next Moves

1. **Deepen agent behaviors**  
   - Ideas: plug in scripted critiques or lightweight LLM calls inspired by [genagents](https://github.com/joonspk-research/genagents).

2. **Persist run history**  
   - Ideas: allow saving/loading past summaries for longitudinal insights.

3. **Tighten evaluation**  
   - Ideas: add automated tests for scoring math and ensure deterministic seeds stay stable.

### Reference Links

- https://github.com/joonspk-research/genagents
- https://github.com/microsoft/autogen
