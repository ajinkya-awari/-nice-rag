"""Synthetic, dependency-free ingestion contracts for Project 19.

The production PDF and vector-store integrations are intentionally deferred.
This module proves the provenance rule with local documents only: guideline
identity is attached before splitting, and page metadata is copied to chunks.
"""

from dataclasses import dataclass
from typing import Iterable

from src.protocol import GUIDELINE_IDS


@dataclass(frozen=True)
class SyntheticDocument:
    """Small local stand-in for a source document or split chunk."""

    page_content: str
    metadata: dict[str, object]


def tag_documents(
    documents: Iterable[SyntheticDocument], guideline_id: str
) -> list[SyntheticDocument]:
    """Copy documents and attach a validated guideline ID before splitting."""
    if guideline_id not in GUIDELINE_IDS:
        raise ValueError(f"Unsupported guideline_id: {guideline_id}")

    tagged = []
    for document in documents:
        metadata = dict(document.metadata)
        metadata["guideline_id"] = guideline_id
        tagged.append(SyntheticDocument(document.page_content, metadata))
    return tagged


def split_documents(
    documents: Iterable[SyntheticDocument],
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> list[SyntheticDocument]:
    """Split tagged documents while copying all source metadata to each chunk."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be non-negative and smaller than chunk_size")

    step = chunk_size - chunk_overlap
    chunks = []
    for document in documents:
        guideline_id = document.metadata.get("guideline_id")
        if guideline_id is None:
            raise ValueError("guideline_id must be attached before splitting")
        if guideline_id not in GUIDELINE_IDS:
            raise ValueError(f"Unsupported guideline_id: {guideline_id}")

        for chunk_index, start in enumerate(range(0, len(document.page_content), step)):
            end = min(start + chunk_size, len(document.page_content))
            metadata = dict(document.metadata)
            metadata["chunk_index"] = chunk_index
            chunks.append(SyntheticDocument(document.page_content[start:end], metadata))
            if end == len(document.page_content):
                break

    return chunks
