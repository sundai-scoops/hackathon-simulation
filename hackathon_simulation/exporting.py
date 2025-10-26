from __future__ import annotations

import json
from dataclasses import asdict
from typing import Dict, List

from .models import SimulationSummary


def print_summary(summary: SimulationSummary) -> None:
    print("\n=== Hackathon Simulation Runs ===")
    for run in summary.runs:
        print(f"\nRun {run.run_index} (seed {run.seed}):")
        for team in run.teams:
            status = "Pivoted" if team.pivoted else "Stayed course"
            research = "✅ user research" if team.research_done else "⚠️ skipped research"
            print(f"  {team.run_rank}. {team.team_name} — {status}, {research}")
            print(f"     Final idea: {team.final_idea}")
            for note in team.conversation_log:
                print(f"       - {note}")
            breakdown = ", ".join(f"{k}: {v:.2f}" for k, v in team.score_breakdown.items())
            print(f"     Score breakdown → {breakdown}; total {team.total_score:.2f}")
    print("\n=== Aggregated Leaderboard Across Runs ===")
    for idx, entry in enumerate(summary.leaderboard, start=1):
        print(f"{idx}. {entry.idea_name}")
        print(
            f"   Avg score {entry.avg_score:.2f} across {entry.appearances} runs, "
            f"{entry.wins} simulated wins. Best showing: {entry.best_team} in run {entry.best_run}."
        )
        if entry.best_reason:
            print(f"   Highlight: {entry.best_reason}")
        print("   Suggested 6-hour plan sample:")
        for step in entry.sample_plan:
            print(f"     • {step}")


def summary_to_dict(summary: SimulationSummary) -> Dict[str, object]:
    return asdict(summary)


def summary_to_markdown(summary: SimulationSummary) -> str:
    lines: List[str] = ["# Hackathon Simulation Summary", "", "## Runs"]
    for run in summary.runs:
        lines.append(f"### Run {run.run_index} (seed {run.seed})")
        for team in run.teams:
            status = "Pivoted" if team.pivoted else "Stayed course"
            research = "✅ user research" if team.research_done else "⚠️ skipped research"
            lines.append(
                f"- **{team.run_rank}. {team.team_name}** — {status}, {research}<br>"
                f"  Final idea: {team.final_idea}"
            )
            for note in team.conversation_log:
                lines.append(f"  - {note}")
            breakdown = ", ".join(f"{k}: {v:.2f}" for k, v in team.score_breakdown.items())
            lines.append(f"  - Scores → {breakdown}; total **{team.total_score:.2f}**")
            lines.append("")
    lines.append("## Leaderboard")
    for idx, entry in enumerate(summary.leaderboard, start=1):
        lines.append(f"### {idx}. {entry.idea_name}")
        lines.append(
            f"- Avg score **{entry.avg_score:.2f}** across {entry.appearances} runs; "
            f"{entry.wins} simulated wins."
        )
        lines.append(f"- Best showing: {entry.best_team} (run {entry.best_run}).")
        if entry.best_reason:
            lines.append(f"- Highlight: {entry.best_reason}")
        lines.append("- Six-hour plan:")
        for step in entry.sample_plan:
            lines.append(f"  - {step}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"
