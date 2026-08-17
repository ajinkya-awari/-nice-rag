import pytest

from src.ingest import SyntheticDocument, split_documents, tag_documents


def test_tag_documents_adds_guideline_id_without_mutating_source_metadata():
    source = SyntheticDocument(
        page_content="Synthetic diabetes guidance.",
        metadata={"page": 7, "source": "synthetic-ng28"},
    )

    tagged = tag_documents([source], "NG28")

    assert tagged[0].metadata["guideline_id"] == "NG28"
    assert tagged[0].metadata["page"] == 7
    assert "guideline_id" not in source.metadata
    assert tagged[0] is not source


def test_tag_documents_rejects_unsupported_guideline_id():
    document = SyntheticDocument("Synthetic content.", {"page": 1})

    with pytest.raises(ValueError, match="Unsupported guideline_id"):
        tag_documents([document], "UNKNOWN")


def test_split_documents_requires_guideline_id_before_splitting():
    document = SyntheticDocument("Synthetic content.", {"page": 1})

    with pytest.raises(ValueError, match="guideline_id must be attached before splitting"):
        split_documents([document], chunk_size=10, chunk_overlap=2)


@pytest.mark.parametrize(
    ("chunk_size", "chunk_overlap"),
    [(0, 0), (10, -1), (10, 10), (10, 11)],
)
def test_split_documents_rejects_invalid_chunk_parameters(chunk_size, chunk_overlap):
    document = SyntheticDocument("Synthetic content.", {"guideline_id": "NG28"})

    with pytest.raises(ValueError):
        split_documents([document], chunk_size=chunk_size, chunk_overlap=chunk_overlap)


def test_split_documents_preserves_guideline_and_page_metadata_on_every_chunk():
    source = SyntheticDocument(
        page_content="0123456789ABCDEFGHIJ",
        metadata={"guideline_id": "NG28", "page": 4, "source": "synthetic-ng28"},
    )

    chunks = split_documents([source], chunk_size=10, chunk_overlap=2)

    assert [chunk.page_content for chunk in chunks] == [
        "0123456789",
        "89ABCDEFGH",
        "GHIJ",
    ]
    assert len(chunks) == 3
    assert [chunk.metadata["chunk_index"] for chunk in chunks] == [0, 1, 2]
    assert all(chunk.metadata["guideline_id"] == "NG28" for chunk in chunks)
    assert all(chunk.metadata["page"] == 4 for chunk in chunks)
    assert all(chunk.metadata["source"] == "synthetic-ng28" for chunk in chunks)
