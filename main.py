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
    parser.add_argument("--profiles", type=str, default=None, help="Optional path to JSON profile definitions.")
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
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    profiles = load_profiles(args.profiles)
    min_size, max_size = parse_team_size(args.team_size)
    config = SimulationConfig(
        runs=args.runs,
        min_team_size=min_size,
        max_team_size=max_size,
        seed=args.seed,
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
