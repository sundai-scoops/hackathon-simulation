from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Iterable, List

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from hackathon_simulation import (  # noqa: E402
    AgentProfile,
    HackathonSimulator,
    SimulationConfig,
    summary_to_dict,
    summary_to_markdown,
)

st.set_page_config(page_title="Hackathon Simulation", layout="wide")


def ensure_agent_state(count: int) -> None:
    count = int(count)
    if "agent_count" not in st.session_state:
        st.session_state.agent_count = count
    if "agent_count" in st.session_state and st.session_state.agent_count != count:
        st.session_state.agent_count = count
    for idx in range(st.session_state.agent_count):
        for field in ("name", "role", "idea"):
            key = f"agent_{field}_{idx}"
            if key not in st.session_state:
                st.session_state[key] = ""
    tracked_prefixes = ("agent_name_", "agent_role_", "agent_idea_")
    keys_to_remove = [
        key
        for key in list(st.session_state.keys())
        if key.startswith(tracked_prefixes)
        and int(key.split("_")[-1]) >= st.session_state.agent_count
    ]
    for key in keys_to_remove:
        del st.session_state[key]


def build_profiles(count: int) -> List[AgentProfile]:
    profiles: List[AgentProfile] = []
    for idx in range(count):
        name = st.session_state.get(f"agent_name_{idx}", "").strip()
        role = st.session_state.get(f"agent_role_{idx}", "").strip()
        idea = st.session_state.get(f"agent_idea_{idx}", "").strip()
        if not name or not role or not idea:
            raise ValueError(f"Participant {idx + 1} needs name, role, and idea.")
        profiles.append(
            AgentProfile(
                name=name,
                role=role,
                idea=idea,
                skills=[],
                personality="Adaptive Collaborator",
                motivation="Ship a standout hackathon project fast.",
                xp_level="mid",
            )
        )
    return profiles


def render_conversation(logs: Iterable[str]) -> None:
    for entry in logs:
        st.markdown(f"- {entry}")


def render_plan(plan: List[str]) -> None:
    st.markdown("**Six-hour sprint outline:**")
    for step in plan:
        st.markdown(f"- {step}")


def main() -> None:
    st.title("Hackathon Simulation Sandbox")
    st.caption("Bring your team roster, explore multi-round simulations, and see what ideas survive.")

    if "simulation_summary" not in st.session_state:
        st.session_state.simulation_summary = None
    if "simulation_json" not in st.session_state:
        st.session_state.simulation_json = ""
    if "simulation_markdown" not in st.session_state:
        st.session_state.simulation_markdown = ""
    if "profile_count" not in st.session_state:
        st.session_state.profile_count = 0
    if "agent_count" not in st.session_state:
        st.session_state.agent_count = 3

    with st.sidebar:
        st.header("Controls")
        participant_count = st.number_input("Participants", min_value=1, max_value=30, value=st.session_state.agent_count)
        ensure_agent_state(participant_count)

        st.subheader("Simulation")
        runs = st.slider("Runs", min_value=1, max_value=10, value=3)
        team_range = st.slider("Team size range", min_value=1, max_value=6, value=(2, 4))
        seed = st.number_input("Base seed", min_value=0, max_value=10_000, value=42, step=1)

        st.subheader("LLM")
        llm_model = st.text_input("Model", value="gemini-1.5-flash")
        llm_temperature = st.slider("Temperature", min_value=0.0, max_value=1.5, value=0.9, step=0.05)
        llm_call_cap = st.number_input("Call budget", min_value=1, max_value=5000, value=500, step=50)
        llm_key = st.text_input("GOOGLE_API_KEY", type="password")

        run_simulation = st.button("Run simulation", type="primary")

    st.subheader("Participant Roster")
    st.write("Provide each person's name, role, and headline idea. The simulation uses this roster verbatim.")
    for idx in range(st.session_state.agent_count):
        st.markdown(f"**Participant {idx + 1}**")
        cols = st.columns(3)
        cols[0].text_input("Name", key=f"agent_name_{idx}", placeholder="Casey Vega")
        cols[1].text_input("Role", key=f"agent_role_{idx}", placeholder="Product Manager")
        cols[2].text_input("Idea", key=f"agent_idea_{idx}", placeholder="Agentic QA bot interviewing power users...")
        st.divider()

    if run_simulation:
        try:
            profiles = build_profiles(st.session_state.agent_count)
            if not llm_key.strip():
                raise ValueError("GOOGLE_API_KEY is required to run the simulation.")
            os.environ["GOOGLE_API_KEY"] = llm_key.strip()
            config = SimulationConfig(
                runs=runs,
                min_team_size=team_range[0],
                max_team_size=team_range[1],
                pivot_base_chance=0.35,
                research_trigger=0.45,
                seed=int(seed),
                llm_model=llm_model,
                llm_temperature=llm_temperature,
                llm_call_cap=int(llm_call_cap),
            )
            simulator = HackathonSimulator(profiles, config=config)
            summary = simulator.run()
        except Exception as err:
            st.error(str(err))
            summary = None
        if summary:
            st.session_state.simulation_summary = summary
            st.session_state.simulation_json = json.dumps(summary_to_dict(summary), indent=2)
            st.session_state.simulation_markdown = summary_to_markdown(summary)
            st.session_state.profile_count = len(profiles)
            st.success(
                f"Ran {runs} simulation run(s) with {st.session_state.profile_count} participants and team range {team_range[0]}-{team_range[1]}."
            )

    summary = st.session_state.simulation_summary

    if summary:
        st.subheader("Simulation Output")
        st.caption(
            f"{len(summary.runs)} run(s) computed. Showing team conversations, LLM insights, and leaderboard highlights."
        )

        tabs = st.tabs(["Runs", "Leaderboard", "Raw Data"])

        with tabs[0]:
            for run in summary.runs:
                expanded = run.run_index == 1
                with st.expander(f"Run {run.run_index} • seed {run.seed}", expanded=expanded):
                    for team in run.teams:
                        st.markdown(f"### {team.run_rank}. {team.team_name}")
                        status = "Pivoted" if team.pivoted else "Stayed course"
                        research = "✅ user research" if team.research_done else "⚠️ skipped research"
                        st.markdown(
                            f"*Final idea:* {team.final_idea}<br>"
                            f"*Origin:* {team.idea_origin} • *Status:* {status} • {research}",
                            unsafe_allow_html=True,
                        )
                        render_conversation(team.conversation_log)
                        breakdown = ", ".join(f"{k}: {v:.2f}" for k, v in team.score_breakdown.items())
                        st.markdown(f"**Scores** → {breakdown}")
                        render_plan(team.six_hour_plan)
                        st.markdown("---")

        with tabs[1]:
            st.markdown("### Aggregated Leaderboard")
            for idx, entry in enumerate(summary.leaderboard, start=1):
                st.markdown(f"#### {idx}. {entry.idea_name}")
                st.markdown(
                    f"*Avg score:* {entry.avg_score:.2f} across {entry.appearances} runs • "
                    f"*Wins:* {entry.wins} • *Best team:* {entry.best_team} (run {entry.best_run})"
                )
                if entry.best_reason:
                    st.markdown(f"- Highlight: {entry.best_reason}")
                st.markdown("**Sample six-hour plan:**")
                for step in entry.sample_plan:
                    st.markdown(f"- {step}")
                st.markdown("---")

        with tabs[2]:
            st.download_button(
                "Download JSON",
                st.session_state.simulation_json.encode("utf-8"),
                file_name="hackathon_simulation_summary.json",
                mime="application/json",
            )
            st.download_button(
                "Download Markdown",
                st.session_state.simulation_markdown.encode("utf-8"),
                file_name="hackathon_simulation_summary.md",
                mime="text/markdown",
            )
            st.text_area("Summary JSON", value=st.session_state.simulation_json, height=300)
            st.text_area("Summary Markdown", value=st.session_state.simulation_markdown, height=300)
    else:
        st.info("Fill in your participant roster and hit Run simulation to see results here.")


if __name__ == "__main__":
    main()
