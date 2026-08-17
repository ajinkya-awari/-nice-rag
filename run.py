"""Local entrypoint for the import-safe Project 19 scaffold."""

from __future__ import annotations

from collections.abc import Sequence

from src.protocol import RESEARCH_DISCLAIMER


def main(argv: Sequence[str] | None = None) -> int:
    """Report scaffold status without initializing external runtime services."""
    del argv
    print("NICE-RAG local scaffold: no external data or API was used.")
    print(RESEARCH_DISCLAIMER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
