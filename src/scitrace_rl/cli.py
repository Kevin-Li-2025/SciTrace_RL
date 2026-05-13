from __future__ import annotations

import argparse
from pathlib import Path

from .runner import run_task


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the SciTrace-RL scientific-agent demo.")
    parser.add_argument(
        "--task",
        type=Path,
        default=Path("data/tasks/electrolyte_additive_screen.json"),
        help="Path to the task JSON file.",
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        default=Path("data/corpus/scientific_sources.json"),
        help="Path to the local evidence corpus.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("outputs"),
        help="Output directory for trace artifacts.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    trace = run_task(args.task, args.corpus, args.out)
    print(f"trace_id={trace['trace_id']}")
    print(f"reward={trace['reward']['reward']}")
    print(f"dashboard={args.out / 'demo_dashboard.html'}")


if __name__ == "__main__":
    main()

