"""Local entrypoint for import-safe Project 19 offline checks."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import sys

from src.evaluation import render_offline_evaluation_plan
from src.offline_cpu import render_cpu_stress_report, run_cpu_stress_check
from src.protocol import RESEARCH_DISCLAIMER


def main(argv: Sequence[str] | None = None) -> int:
    """Run local checks without initializing external runtime services."""
    parser = argparse.ArgumentParser(description="NICE-RAG offline entrypoint")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--list-scenarios",
        action="store_true",
        help="list the five fixture scenarios without live execution",
    )
    modes.add_argument(
        "--cpu-smoke",
        action="store_true",
        help="run the in-memory synthetic CPU stress check",
    )
    parser.add_argument(
        "--documents",
        type=int,
        default=1_000,
        help="synthetic document count for --cpu-smoke (default: 1000)",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=1,
        help="query repetitions per canonical scenario (default: 1)",
    )
    parser.add_argument("query", nargs="*", help="legacy local scaffold query text")
    arguments = parser.parse_args(list(argv or ()))

    if arguments.list_scenarios:
        print(render_offline_evaluation_plan())
        return 0
    if arguments.cpu_smoke:
        report = run_cpu_stress_check(arguments.documents, arguments.repeats)
        print(render_cpu_stress_report(report))
        return 0

    print("NICE-RAG local scaffold: no external data or API was used.")
    print(RESEARCH_DISCLAIMER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
