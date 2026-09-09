from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

import src.open_ingest as open_ingest
from src.open_ingest import (
    OpenEvidenceError,
    create_staging_corpus,
    load_local_open_articles,
    promote_staging_corpus,
    resolve_promoted_corpus,
    split_open_sections,
    store_validated_raw_record,
    validate_and_extract_record,
    write_sanitized_manifest,
)
from src.open_registry import OPEN_EVIDENCE_SOURCES
from src.pmc_client import PMC_OAI_BASE_URL, PmcResponse


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "pmc_record.xml"
SOURCE = OPEN_EVIDENCE_SOURCES[0]
RETRIEVED_AT = "2026-09-09T12:00:00Z"


def fixture_bytes(**replacements: str) -> bytes:
    value = FIXTURE_PATH.read_text(encoding="utf-8")
    for original, replacement in replacements.items():
        value = value.replace(original, replacement)
    return value.encode("utf-8")


def response(body: bytes | None = None) -> PmcResponse:
    return PmcResponse(
        body=body or FIXTURE_PATH.read_bytes(),
        status=200,
        content_type="text/xml",
        final_url=PMC_OAI_BASE_URL,
    )


def validated_article():
    return validate_and_extract_record(SOURCE, response(), RETRIEVED_AT)


def test_validate_extracts_narrative_with_complete_provenance() -> None:
    article = validated_article()

    assert article.source == SOURCE
    assert article.source_sha256 == hashlib.sha256(FIXTURE_PATH.read_bytes()).hexdigest()
    assert article.byte_count == len(FIXTURE_PATH.read_bytes())
    assert article.license_uri == "https://creativecommons.org/licenses/by/4.0/"
    assert tuple(section.metadata["section_title"] for section in article.sections) == (
        "Article body",
        "Fictional methods",
        "Fictional nested analysis",
    )
    combined = " ".join(section.text for section in article.sections)
    assert "FICTIONAL_BODY_OVERVIEW" in combined
    assert "FICTIONAL_METHODS_TOKEN" in combined
    assert "FICTIONAL_NESTED_TOKEN" in combined
    assert not any(
        token in combined
        for token in (
            "FICTIONAL_LICENSE_PROSE_NOT_FOR_OUTPUT",
            "fictional.author@example.invalid",
            "EXCLUDED_FIGURE_CAPTION_TOKEN",
            "EXCLUDED_TABLE_TOKEN",
            "EXCLUDED_FORMULA_TOKEN",
            "EXCLUDED_MEDIA_TOKEN",
            "EXCLUDED_SUPPLEMENT_TOKEN",
            "EXCLUDED_ACKNOWLEDGEMENT_TOKEN",
            "EXCLUDED_REFERENCE_ARTICLE_TITLE",
            "EXCLUDED_REFERENCE_TOKEN",
        )
    )
    required = {
        "corpus",
        "topic_key",
        "pmcid",
        "doi",
        "article_title",
        "section_title",
        "section_index",
        "canonical_url",
        "license_uri",
        "retrieved_at_utc",
        "source_sha256",
    }
    assert all(required <= section.metadata.keys() for section in article.sections)
    assert all(section.metadata["corpus"] == "pmc_open_evidence" for section in article.sections)


def test_validate_canonicalizes_allowlisted_cc_uri_and_accepts_cc0_companion() -> None:
    body = fixture_bytes(
        **{
            "licenses/by/4.0/": "licenses/by/4.0",
            "</license>": (
                '<ext-link xmlns:xlink="http://www.w3.org/1999/xlink" '
                'xlink:href="https://creativecommons.org/publicdomain/zero/1.0/"/>'
                "</license>"
            ),
        }
    )

    article = validate_and_extract_record(SOURCE, response(body), RETRIEVED_AT)

    assert article.license_uri == "https://creativecommons.org/licenses/by/4.0/"


@pytest.mark.parametrize(
    ("replacements", "message"),
    (
        (
            {"<GetRecord>": '<error code="idDoesNotExist">missing</error><GetRecord>'},
            "OAI error",
        ),
        ({"<header>": '<header status="deleted">'}, "deleted"),
        ({"PMC5256065": "PMC5256066"}, "PMCID"),
        ({"10.3389/fendo.2017.00006": "10.1/wrong"}, "DOI"),
        ({"Clinical Review of Antidiabetic Drugs": "Different Article"}, "title"),
        ({"licenses/by/4.0/": "licenses/by-nc/4.0/"}, "licence"),
        (
            {' article-type="review-article"': ' article-type="retracted-article"'},
            "retract",
        ),
        (
            {
                "<body>": (
                    '<related-article related-article-type="expression-of-concern"/>'
                    "<body>"
                )
            },
            "concern",
        ),
    ),
)
def test_validate_rejects_identity_rights_and_lifecycle_failures(
    replacements: dict[str, str], message: str
) -> None:
    with pytest.raises(OpenEvidenceError, match=message):
        validate_and_extract_record(
            SOURCE, response(fixture_bytes(**replacements)), RETRIEVED_AT
        )


def test_validate_rejects_malformed_or_missing_full_text() -> None:
    with pytest.raises(OpenEvidenceError, match="Malformed XML"):
        validate_and_extract_record(SOURCE, response(b"<broken>"), RETRIEVED_AT)
    without_body = fixture_bytes(**{"<body>": "<not-body>", "</body>": "</not-body>"})
    with pytest.raises(OpenEvidenceError, match="body"):
        validate_and_extract_record(SOURCE, response(without_body), RETRIEVED_AT)


def test_split_copies_provenance_before_adding_chunk_index() -> None:
    article = validated_article()

    chunks = split_open_sections(article.sections, chunk_size=35, chunk_overlap=5)

    assert len(chunks) > len(article.sections)
    for chunk in chunks:
        assert chunk.metadata["pmcid"] == SOURCE.pmcid
        assert chunk.metadata["source_sha256"] == article.source_sha256
        assert isinstance(chunk.metadata["chunk_index"], int)


@pytest.mark.parametrize(
    ("chunk_size", "overlap", "message"),
    ((0, 0, "chunk_size"), (10, -1, "chunk_overlap"), (10, 10, "chunk_overlap")),
)
def test_split_rejects_invalid_bounds(
    chunk_size: int, overlap: int, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        split_open_sections(
            validated_article().sections,
            chunk_size=chunk_size,
            chunk_overlap=overlap,
        )


def test_raw_storage_is_atomic_idempotent_and_never_overwrites(tmp_path: Path) -> None:
    article = validated_article()
    raw_directory = tmp_path / "raw"

    first_path = store_validated_raw_record(
        article, FIXTURE_PATH.read_bytes(), raw_directory
    )
    first_mtime = first_path.stat().st_mtime_ns
    second_path = store_validated_raw_record(
        article, FIXTURE_PATH.read_bytes(), raw_directory
    )

    assert first_path == second_path
    assert first_path.read_bytes() == FIXTURE_PATH.read_bytes()
    assert second_path.stat().st_mtime_ns == first_mtime
    with pytest.raises(OpenEvidenceError, match="different hash"):
        store_validated_raw_record(article, b"different", raw_directory)


def test_transactional_corpus_paths_promote_only_new_complete_staging(
    tmp_path: Path,
) -> None:
    evidence_root = tmp_path / "open_evidence"
    acquisition_id = "20260909T164500Z"

    staging = create_staging_corpus(evidence_root, acquisition_id)
    (staging / "PMC5256065.xml").write_bytes(b"invented fixture bytes")
    promoted = promote_staging_corpus(evidence_root, staging, acquisition_id)

    assert not staging.exists()
    assert promoted == evidence_root / "corpora" / acquisition_id
    assert (promoted / "PMC5256065.xml").read_bytes() == b"invented fixture bytes"
    assert resolve_promoted_corpus(evidence_root, acquisition_id) == promoted
    with pytest.raises(OpenEvidenceError, match="Staging corpus is missing"):
        promote_staging_corpus(evidence_root, staging, acquisition_id)


@pytest.mark.parametrize("acquisition_id", ("../outside", "bad/id", "plain-text"))
def test_transactional_corpus_paths_reject_unsafe_acquisition_ids(
    tmp_path: Path, acquisition_id: str
) -> None:
    with pytest.raises(OpenEvidenceError, match="acquisition"):
        create_staging_corpus(tmp_path / "open_evidence", acquisition_id)
    with pytest.raises(OpenEvidenceError, match="acquisition"):
        resolve_promoted_corpus(tmp_path / "open_evidence", acquisition_id)


def test_transactional_corpus_paths_reject_symlinked_staging_root(
    tmp_path: Path,
) -> None:
    evidence_root = tmp_path / "open_evidence"
    staging_root = evidence_root / "staging"
    outside = tmp_path / "outside"
    evidence_root.mkdir()
    outside.mkdir()
    try:
        staging_root.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    with pytest.raises(OpenEvidenceError, match="symlink"):
        create_staging_corpus(evidence_root, "20260909T180000Z")


def test_promotion_never_overwrites_a_file_collision_created_mid_promotion(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    evidence_root = tmp_path / "open_evidence"
    acquisition_id = "20260909T181000Z"
    staging = create_staging_corpus(evidence_root, acquisition_id)
    source_file = staging / "PMC5256065.xml"
    source_file.write_bytes(b"staged")
    original_link = open_ingest.os.link

    def create_collision(source: str | Path, target: str | Path) -> None:
        Path(target).write_bytes(b"existing")
        original_link(source, target)

    monkeypatch.setattr(open_ingest.os, "link", create_collision)

    with pytest.raises(OpenEvidenceError, match="collision"):
        promote_staging_corpus(evidence_root, staging, acquisition_id)

    promoted_file = evidence_root / "corpora" / acquisition_id / source_file.name
    assert source_file.read_bytes() == b"staged"
    assert promoted_file.read_bytes() == b"existing"


def test_manifest_contains_metadata_but_no_extracted_text(tmp_path: Path) -> None:
    article = validated_article()
    manifest_path = tmp_path / "open_evidence_manifest.json"

    write_sanitized_manifest(
        (article,),
        manifest_path,
        source_revision="abc123",
        acquisition_id="20260909T170000Z",
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    serialized = json.dumps(manifest)

    assert manifest["source_revision"] == "abc123"
    assert manifest["acquisition_id"] == "20260909T170000Z"
    assert manifest["sources"][0]["pmcid"] == SOURCE.pmcid
    assert manifest["sources"][0]["sha256"] == article.source_sha256
    assert "FICTIONAL_BODY_OVERVIEW" not in serialized
    assert "text" not in manifest["sources"][0]


def test_manifest_write_replaces_a_temporary_file_atomically(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    article = validated_article()
    manifest_path = tmp_path / "open_evidence_manifest.json"
    replace_calls: list[tuple[Path, Path]] = []
    original_replace = open_ingest.os.replace

    def capture_replace(source: str | Path, target: str | Path) -> None:
        replace_calls.append((Path(source), Path(target)))
        original_replace(source, target)

    monkeypatch.setattr(open_ingest.os, "replace", capture_replace)

    write_sanitized_manifest(
        (article,),
        manifest_path,
        source_revision="abc123",
        acquisition_id="20260909T180000Z",
    )

    assert len(replace_calls) == 1
    assert replace_calls[0][1] == manifest_path
    assert replace_calls[0][0].parent == manifest_path.parent
    assert manifest_path.is_file()


def test_local_loader_rejects_partial_corpus(tmp_path: Path) -> None:
    raw_directory = tmp_path / "raw"
    raw_directory.mkdir()
    (raw_directory / f"{SOURCE.pmcid}.xml").write_bytes(FIXTURE_PATH.read_bytes())

    with pytest.raises(OpenEvidenceError, match="missing local evidence"):
        load_local_open_articles(
            OPEN_EVIDENCE_SOURCES,
            raw_directory,
            retrieved_at_utc=RETRIEVED_AT,
        )


def test_validator_rejects_registry_source_mismatch_even_with_valid_xml() -> None:
    wrong_source = replace(SOURCE, pmcid="PMC9999999", canonical_url="https://pmc.ncbi.nlm.nih.gov/articles/PMC9999999/")
    with pytest.raises(OpenEvidenceError, match="PMCID"):
        validate_and_extract_record(wrong_source, response(), RETRIEVED_AT)
