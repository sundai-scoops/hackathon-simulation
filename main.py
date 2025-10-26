from __future__ import annotations

import argparse
import json

from hackathon_simulation import (
    HackathonSimulator,
    SimulationConfig,
    ensure_parent_dir,
    load_profiles,
    parse_team_size,
    print_summary,
    summary_to_dict,
    summary_to_markdown,
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run hackathon idea simulations.")
    parser.add_argument("--profiles", type=str, required=True, help="Path to participant profile JSON.")
    parser.add_argument("--runs", type=int, default=5, help="Number of simulation runs to execute.")
    parser.add_argument("--seed", type=int, default=42, help="Base random seed.")
    parser.add_argument(
        "--team-size",
        type=str,
        default="2-4",
        help="Desired team size range, e.g., '2-4'.",
    )
    parser.add_argument("--json-out", type=str, default=None, help="Optional path to write summary JSON.")
    parser.add_argument("--markdown-out", type=str, default=None, help="Optional path to write summary Markdown.")
    parser.add_argument("--llm-model", type=str, default="gemini-1.5-flash", help="LLM model id.")
    parser.add_argument("--llm-temperature", type=float, default=0.9, help="Sampling temperature for LLM output.")
    parser.add_argument("--llm-call-cap", type=int, default=500, help="Maximum LLM calls per simulation run.")
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    try:
        profiles = load_profiles(args.profiles)
    except Exception as exc:
        raise SystemExit(f"Failed to load profiles: {exc}")
    min_size, max_size = parse_team_size(args.team_size)
    config = SimulationConfig(
        runs=args.runs,
        min_team_size=min_size,
        max_team_size=max_size,
        seed=args.seed,
        llm_model=args.llm_model,
        llm_temperature=args.llm_temperature,
        llm_call_cap=args.llm_call_cap,
    )
    simulator = HackathonSimulator(profiles, config=config)
    summary = simulator.run()
    print_summary(summary)
    if args.json_out:
        ensure_parent_dir(args.json_out)
        with open(args.json_out, "w", encoding="utf-8") as handle:
            json.dump(summary_to_dict(summary), handle, indent=2)
    if args.markdown_out:
        ensure_parent_dir(args.markdown_out)
        with open(args.markdown_out, "w", encoding="utf-8") as handle:
            handle.write(summary_to_markdown(summary))


if __name__ == "__main__":
    main()
