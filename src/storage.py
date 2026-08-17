"""Declarative persistent-vector-store configuration for Project 19."""

from types import MappingProxyType

from src.protocol import CHROMA_DIRECTORY, EMBEDDING_MODEL


_CHROMA_CONFIG = MappingProxyType(
    {
        "persist_directory": CHROMA_DIRECTORY.as_posix(),
        "embedding_model": EMBEDDING_MODEL,
    }
)


def build_chroma_config() -> dict[str, str]:
    """Return future build settings without creating a store or directory."""
    return dict(_CHROMA_CONFIG)


def load_chroma_config() -> dict[str, str]:
    """Return future load settings without rebuilding or touching the store."""
    return dict(_CHROMA_CONFIG)
