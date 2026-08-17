"""Local entrypoint for the import-safe Project 19 scaffold."""

from __future__ import annotations

from collections.abc import Sequence
import sys

from src.evaluation import render_offline_evaluation_plan
from src.protocol import RESEARCH_DISCLAIMER


def main(argv: Sequence[str] | None = None) -> int:
    """Report scaffold status without initializing external runtime services."""
    arguments = list(argv or ())
    if arguments == ["--list-scenarios"]:
        print(render_offline_evaluation_plan())
        return 0

    print("NICE-RAG local scaffold: no external data or API was used.")
    print(RESEARCH_DISCLAIMER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
