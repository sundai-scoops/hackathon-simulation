from __future__ import annotations

import argparse
import json

from hackathon_simulation import (
    HackathonSimulator,
    SimulationConfig,
    ensure_parent_dir,
    load_profiles,
    print_summary,
    summary_to_dict,
    summary_to_markdown,
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run hackathon idea simulations.")
    parser.add_argument("--profiles", type=str, required=True, help="Path to participant profile JSON.")
    parser.add_argument("--runs", type=int, default=5, help="Number of simulation runs to execute.")
    parser.add_argument("--seed", type=int, default=42, help="Base random seed.")
    parser.add_argument("--json-out", type=str, default=None, help="Optional path to write summary JSON.")
    parser.add_argument("--markdown-out", type=str, default=None, help="Optional path to write summary Markdown.")
    parser.add_argument("--llm-model", type=str, default="gemini-flash-latest", help="LLM model id.")
    parser.add_argument("--llm-temperature", type=float, default=0.9, help="Sampling temperature for LLM output.")
    parser.add_argument("--llm-call-cap", type=int, default=10, help="Maximum LLM calls per simulation run.")
    parser.add_argument("--rounds", type=int, default=6, help="Conversation rounds per run.")
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    try:
        profiles = load_profiles(args.profiles)
    except Exception as exc:
        raise SystemExit(f"Failed to load profiles: {exc}")
    config = SimulationConfig(
        runs=args.runs,
        seed=args.seed,
        llm_model=args.llm_model,
        llm_temperature=args.llm_temperature,
        llm_call_cap=args.llm_call_cap,
        conversation_rounds=args.rounds,
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
