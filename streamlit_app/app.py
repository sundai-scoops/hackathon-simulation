from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterable, List

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from hackathon_simulation import (  # noqa: E402
    AgentProfile,
    DEFAULT_PROFILES,
    HackathonSimulator,
    SimulationConfig,
    summary_to_dict,
    summary_to_markdown,
)

st.set_page_config(page_title="Hackathon Idea Simulation", layout="wide")


def load_uploaded_profiles(uploaded_file) -> List[AgentProfile]:
    if not uploaded_file:
        return DEFAULT_PROFILES
    try:
        payload = json.load(uploaded_file)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Could not parse JSON: {exc}") from exc
    if not isinstance(payload, list):
        raise ValueError("Profile file must be a list of agent definitions.")
    profiles: List[AgentProfile] = []
    for idx, entry in enumerate(payload, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"Profile at index {idx} must be an object.")
        try:
            profiles.append(
                AgentProfile(
                    name=entry["name"],
                    role=entry["role"],
                    idea=entry["idea"],
                    skills=entry.get("skills", []),
                    personality=entry.get("personality", "Curious Collaborator"),
                    motivation=entry.get("motivation", "Build something meaningful."),
                    xp_level=entry.get("xp_level", "mid"),
                )
            )
        except KeyError as missing:
            raise ValueError(f"Profile at index {idx} missing required field: {missing}") from missing
    if not profiles:
        raise ValueError("At least one profile is required.")
    return profiles


def render_conversation(logs: Iterable[str]) -> None:
    for entry in logs:
        st.markdown(f"- {entry}")


def render_score_breakdown(breakdown) -> None:
    parts = [f"{metric}: {value:.2f}" for metric, value in breakdown.items()]
    st.markdown(f"**Scores** → {', '.join(parts)}")


def render_plan(plan: List[str]) -> None:
    st.markdown("**Six-hour sprint outline:**")
    for step in plan:
        st.markdown(f"- {step}")


def main() -> None:
    st.title("Hackathon Simulation Sandbox")
    st.write(
        "Spin up simulated hackathon rounds to explore team formation, pivots, critique, and what ideas rise to the top."
    )

    if "simulation_summary" not in st.session_state:
        st.session_state.simulation_summary = None
    if "simulation_json" not in st.session_state:
        st.session_state.simulation_json = ""
    if "simulation_markdown" not in st.session_state:
        st.session_state.simulation_markdown = ""
    if "profile_count" not in st.session_state:
        st.session_state.profile_count = len(DEFAULT_PROFILES)

    with st.sidebar:
        st.header("Simulation Settings")
        runs = st.slider("Runs", min_value=1, max_value=10, value=3)
        team_range = st.slider("Team size range", min_value=1, max_value=6, value=(2, 4))
        seed = st.number_input("Base seed", min_value=0, max_value=10_000, value=42, step=1)

        st.subheader("Behavior Tweaks")
        pivot_chance = st.slider("Pivot pressure baseline", min_value=0.05, max_value=0.8, value=0.35, step=0.05)
        research_trigger = st.slider("User research trigger", min_value=0.0, max_value=1.0, value=0.45, step=0.05)

        st.subheader("Profiles")
        uploaded_profiles = st.file_uploader("Upload profiles JSON", type=["json"])
        use_default = st.checkbox("Use built-in sample profiles", value=uploaded_profiles is None)

        run_simulation = st.button("Run simulation", type="primary")

    if run_simulation:
        try:
            profiles = DEFAULT_PROFILES if use_default or not uploaded_profiles else load_uploaded_profiles(uploaded_profiles)
            config = SimulationConfig(
                runs=runs,
                min_team_size=team_range[0],
                max_team_size=team_range[1],
                pivot_base_chance=pivot_chance,
                research_trigger=research_trigger,
                seed=int(seed),
            )
            simulator = HackathonSimulator(profiles, config=config)
            summary = simulator.run()
        except ValueError as err:
            st.error(str(err))
            summary = None
        if summary:
            st.session_state.simulation_summary = summary
            st.session_state.simulation_json = json.dumps(summary_to_dict(summary), indent=2)
            st.session_state.simulation_markdown = summary_to_markdown(summary)
            st.session_state.profile_count = len(profiles)
            st.success(
                f"Ran {runs} simulation run(s) with {st.session_state.profile_count} profiles and team range {team_range[0]}-{team_range[1]}."
            )

    summary = st.session_state.simulation_summary

    if summary:
        st.subheader("Simulation Output")
        st.caption(
            f"{len(summary.runs)} run(s) computed. Showing team conversations, pivots, and leaderboard insights."
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
                        render_score_breakdown(team.score_breakdown)
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
            st.text_area(
                "Summary JSON",
                value=st.session_state.simulation_json,
                height=350,
            )
            st.text_area(
                "Summary Markdown",
                value=st.session_state.simulation_markdown,
                height=350,
            )
    else:
        st.info("Configure parameters and run the simulation to see results here.")


if __name__ == "__main__":
    main()
