"""Offline release-boundary helpers for Project 19."""

from os import PathLike
from pathlib import Path


RESTRICTED_SUFFIXES = frozenset(
    {".bin", ".db", ".jsonl", ".parquet", ".pdf", ".safetensors", ".sqlite"}
)
RESTRICTED_FILENAMES = frozenset(
    {"credentials.json", "credentials.yaml", "secrets.json"}
)
PROTECTED_DIRECTORIES = frozenset({"chroma_db", "pdfs"})


def restricted_path_reasons(path: str | PathLike[str]) -> tuple[str, ...]:
    """Return deterministic reasons a relative path must stay restricted."""
    candidate = Path(path)
    reasons = []
    lower_parts = {part.casefold() for part in candidate.parts}
    lower_name = candidate.name.casefold()

    for directory in sorted(PROTECTED_DIRECTORIES.intersection(lower_parts)):
        reasons.append(f"protected_directory:{directory}")
    if lower_name == ".env" or lower_name.startswith(".env."):
        reasons.append("environment_file")
    if lower_name in RESTRICTED_FILENAMES:
        reasons.append(f"restricted_filename:{lower_name}")
    if candidate.suffix.casefold() in RESTRICTED_SUFFIXES:
        reasons.append(f"restricted_suffix:{candidate.suffix.casefold()}")

    return tuple(reasons)


def is_restricted_path(path: str | PathLike[str]) -> bool:
    """Return whether a path matches a restricted artifact boundary."""
    return bool(restricted_path_reasons(path))
