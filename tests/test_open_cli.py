import hashlib
import json
from pathlib import Path

import pytest

import run
from src.open_ingest import OpenEvidenceError, OpenSection, ValidatedOpenArticle
from src.open_registry import OPEN_EVIDENCE_SOURCES
from src.open_retrieval import OPEN_VALIDATION_QUERIES
from src.pmc_client import PMC_OAI_BASE_URL, PmcClientError, PmcResponse


PRIVATE_PATH_PREFIX = "E:" + "\\" + "appli" + "cation"


def fake_article(source, body: bytes, retrieved_at: str) -> ValidatedOpenArticle:
    source_hash = hashlib.sha256(body).hexdigest()
    return ValidatedOpenArticle(
        source=source,
        sections=(
            OpenSection(
                text=(
                    "Fictional CLI orchestration text "
                    f"{OPEN_VALIDATION_QUERIES[source.topic_key]}."
                ),
                metadata={
                    "corpus": "pmc_open_evidence",
                    "topic_key": source.topic_key,
                    "pmcid": source.pmcid,
                    "doi": source.doi,
                    "article_title": source.title,
                    "section_title": "Fictional section",
                    "section_index": 0,
                    "canonical_url": source.canonical_url,
                    "license_uri": source.expected_license_uri,
                    "retrieved_at_utc": retrieved_at,
                    "source_sha256": source_hash,
                },
            ),
        ),
        source_sha256=source_hash,
        retrieved_at_utc=retrieved_at,
        byte_count=len(body),
        license_uri=source.expected_license_uri,
        http_status=200,
        content_type="text/xml",
        retrieval_url=PMC_OAI_BASE_URL,
    )


def test_list_open_sources_is_offline_and_lists_exact_registry(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        run,
        "fetch_pmc_record",
        lambda source: (_ for _ in ()).throw(AssertionError("network called")),
        raising=False,
    )

    exit_code = run.main(["--list-open-sources"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert output.count("PMC") == 5
    assert all(source.pmcid in output for source in OPEN_EVIDENCE_SOURCES)
    assert all(source.topic_key in output for source in OPEN_EVIDENCE_SOURCES)
    assert "article text" not in output.casefold()


def test_new_modes_are_mutually_exclusive() -> None:
    with pytest.raises(SystemExit) as exc_info:
        run.main(["--list-open-sources", "--fetch-open-evidence"])
    assert exc_info.value.code == 2


def test_fetch_mode_is_sequential_paced_and_writes_only_after_validation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    events: list[str] = []

    def fetch(source):
        events.append(f"fetch:{source.pmcid}")
        return PmcResponse(
            body=source.pmcid.encode(),
            status=200,
            content_type="text/xml",
            final_url=PMC_OAI_BASE_URL,
        )

    def validate(source, response, retrieved_at):
        events.append(f"validate:{source.pmcid}")
        return fake_article(source, response.body, retrieved_at)

    def store(article, body, raw_directory):
        events.append(f"store:{article.source.pmcid}")
        raw_directory.mkdir(parents=True, exist_ok=True)
        path = raw_directory / f"{article.source.pmcid}.xml"
        path.write_bytes(body)
        return path

    monkeypatch.setattr(run, "fetch_pmc_record", fetch, raising=False)
    monkeypatch.setattr(run, "validate_and_extract_record", validate, raising=False)
    monkeypatch.setattr(run, "store_validated_raw_record", store, raising=False)
    monkeypatch.setattr(
        run,
        "sleep",
        lambda seconds: events.append(f"sleep:{seconds}"),
        raising=False,
    )
    monkeypatch.setattr(
        run, "OPEN_EVIDENCE_ROOT", tmp_path / "open_evidence", raising=False
    )
    monkeypatch.setattr(
        run, "OPEN_EVIDENCE_MANIFEST", tmp_path / "manifest.json", raising=False
    )
    monkeypatch.setattr(
        run, "_acquisition_id", lambda: "20260909T171800Z", raising=False
    )
    monkeypatch.setattr(run, "_source_revision", lambda: "test-revision", raising=False)

    exit_code = run.main(["--fetch-open-evidence"])
    output = capsys.readouterr().out

    assert exit_code == 0
    expected_events: list[str] = []
    for index, source in enumerate(OPEN_EVIDENCE_SOURCES):
        expected_events.extend(
            [f"fetch:{source.pmcid}", f"validate:{source.pmcid}", f"store:{source.pmcid}"]
        )
        if index < 4:
            expected_events.append("sleep:0.4")
    assert events == expected_events
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_revision"] == "test-revision"
    assert len(manifest["sources"]) == 5
    assert "Fictional CLI orchestration text" not in json.dumps(manifest)
    assert "OPEN-EVIDENCE-VERIFIED" not in output


def test_fetch_promotes_only_a_complete_staged_corpus(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fetch(source):
        return PmcResponse(
            body=source.pmcid.encode(),
            status=200,
            content_type="text/xml",
            final_url=PMC_OAI_BASE_URL,
        )

    monkeypatch.setattr(run, "fetch_pmc_record", fetch, raising=False)
    monkeypatch.setattr(
        run,
        "validate_and_extract_record",
        lambda source, response, retrieved_at: fake_article(
            source, response.body, retrieved_at
        ),
        raising=False,
    )
    monkeypatch.setattr(run, "sleep", lambda seconds: None, raising=False)
    monkeypatch.setattr(
        run, "OPEN_EVIDENCE_ROOT", tmp_path / "open_evidence", raising=False
    )
    monkeypatch.setattr(
        run, "OPEN_EVIDENCE_MANIFEST", tmp_path / "manifest.json", raising=False
    )
    monkeypatch.setattr(
        run, "_acquisition_id", lambda: "20260909T170000Z", raising=False
    )
    monkeypatch.setattr(run, "_source_revision", lambda: "test-revision", raising=False)

    assert run.main(["--fetch-open-evidence"]) == 0

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    promoted = tmp_path / "open_evidence" / "corpora" / "20260909T170000Z"
    assert manifest["acquisition_id"] == "20260909T170000Z"
    assert {path.stem for path in promoted.glob("*.xml")} == {
        source.pmcid for source in OPEN_EVIDENCE_SOURCES
    }
    assert not (tmp_path / "open_evidence" / "staging").exists()


def test_fetch_stops_on_first_failure_without_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[str] = []

    def fail(source):
        calls.append(source.pmcid)
        raise PmcClientError("bounded failure")

    monkeypatch.setattr(run, "fetch_pmc_record", fail, raising=False)
    monkeypatch.setattr(
        run, "OPEN_EVIDENCE_MANIFEST", tmp_path / "manifest.json", raising=False
    )

    exit_code = run.main(["--fetch-open-evidence"])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert calls == [OPEN_EVIDENCE_SOURCES[0].pmcid]
    assert not (tmp_path / "manifest.json").exists()
    assert OPEN_EVIDENCE_SOURCES[0].pmcid in output
    assert "bounded failure" in output


def test_fetch_failure_preserves_existing_promoted_corpus(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    evidence_root = tmp_path / "open_evidence"
    existing = evidence_root / "corpora" / "20260909T160000Z"
    existing.mkdir(parents=True)
    sentinel = existing / "existing.xml"
    sentinel.write_bytes(b"preserved")
    calls: list[str] = []

    def fetch(source):
        calls.append(source.pmcid)
        if len(calls) == 2:
            raise PmcClientError("bounded failure")
        return PmcResponse(
            body=source.pmcid.encode(),
            status=200,
            content_type="text/xml",
            final_url=PMC_OAI_BASE_URL,
        )

    monkeypatch.setattr(run, "fetch_pmc_record", fetch, raising=False)
    monkeypatch.setattr(
        run,
        "validate_and_extract_record",
        lambda source, response, retrieved_at: fake_article(
            source, response.body, retrieved_at
        ),
        raising=False,
    )
    monkeypatch.setattr(run, "sleep", lambda seconds: None, raising=False)
    monkeypatch.setattr(run, "OPEN_EVIDENCE_ROOT", evidence_root, raising=False)
    monkeypatch.setattr(
        run, "OPEN_EVIDENCE_MANIFEST", tmp_path / "manifest.json", raising=False
    )
    monkeypatch.setattr(
        run, "_acquisition_id", lambda: "20260909T180000Z", raising=False
    )

    assert run.main(["--fetch-open-evidence"]) == 1
    assert calls == [source.pmcid for source in OPEN_EVIDENCE_SOURCES[:2]]
    assert sentinel.read_bytes() == b"preserved"
    assert not (evidence_root / "staging" / "20260909T180000Z").exists()
    assert not (tmp_path / "manifest.json").exists()


def test_fetch_does_not_echo_private_path_from_storage_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = OPEN_EVIDENCE_SOURCES[0]
    body = source.pmcid.encode()
    monkeypatch.setattr(
        run,
        "fetch_pmc_record",
        lambda selected: PmcResponse(
            body=body,
            status=200,
            content_type="text/xml",
            final_url=PMC_OAI_BASE_URL,
        ),
    )
    monkeypatch.setattr(
        run,
        "validate_and_extract_record",
        lambda selected, response, retrieved_at: fake_article(
            selected, response.body, retrieved_at
        ),
    )
    monkeypatch.setattr(
        run,
        "store_validated_raw_record",
        lambda *args: (_ for _ in ()).throw(
            OSError(PRIVATE_PATH_PREFIX + r"\MS CS\private.xml")
        ),
    )
    monkeypatch.setattr(
        run, "OPEN_EVIDENCE_MANIFEST", tmp_path / "manifest.json"
    )

    exit_code = run.main(["--fetch-open-evidence"])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert source.pmcid in output
    assert "local storage operation failed" in output
    assert PRIVATE_PATH_PREFIX not in output


def test_fetch_fails_safely_when_manifest_write_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        run,
        "fetch_pmc_record",
        lambda source: PmcResponse(
            body=source.pmcid.encode(),
            status=200,
            content_type="text/xml",
            final_url=PMC_OAI_BASE_URL,
        ),
    )
    monkeypatch.setattr(
        run,
        "validate_and_extract_record",
        lambda source, response, retrieved_at: fake_article(
            source, response.body, retrieved_at
        ),
    )
    monkeypatch.setattr(run, "store_validated_raw_record", lambda *args: None)
    monkeypatch.setattr(run, "sleep", lambda seconds: None)
    monkeypatch.setattr(
        run, "OPEN_EVIDENCE_ROOT", tmp_path / "open_evidence", raising=False
    )
    monkeypatch.setattr(
        run, "_acquisition_id", lambda: "20260909T171700Z", raising=False
    )
    monkeypatch.setattr(
        run,
        "write_sanitized_manifest",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            OSError(PRIVATE_PATH_PREFIX + r"\MS CS\manifest.json")
        ),
    )

    exit_code = run.main(["--fetch-open-evidence"])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "ERROR open-evidence manifest" in output
    assert "local storage operation failed" in output
    assert PRIVATE_PATH_PREFIX not in output


def test_validate_mode_is_local_sanitized_and_writes_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    articles = tuple(
        fake_article(source, source.pmcid.encode(), "2026-09-09T12:00:00Z")
        for source in OPEN_EVIDENCE_SOURCES
    )
    manifest = {
        "source_revision": "test-revision",
        "acquisition_id": "20260909T170000Z",
        "sources": [
            {
                "pmcid": article.source.pmcid,
                "retrieved_at_utc": article.retrieved_at_utc,
                "sha256": article.source_sha256,
            }
            for article in articles
        ],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    report_path = tmp_path / "validation.json"
    monkeypatch.setattr(run, "OPEN_EVIDENCE_MANIFEST", manifest_path, raising=False)
    monkeypatch.setattr(run, "OPEN_EVIDENCE_VALIDATION", report_path, raising=False)
    corpus_directory = tmp_path / "open_evidence" / "corpora" / "20260909T170000Z"
    corpus_directory.mkdir(parents=True)
    monkeypatch.setattr(
        run, "OPEN_EVIDENCE_ROOT", tmp_path / "open_evidence", raising=False
    )
    loaded_directories: list[Path] = []
    monkeypatch.setattr(
        run,
        "load_local_open_articles",
        lambda _sources, raw_directory, **_kwargs: (
            loaded_directories.append(raw_directory) or articles
        ),
        raising=False,
    )
    monkeypatch.setattr(
        run,
        "fetch_pmc_record",
        lambda source: (_ for _ in ()).throw(AssertionError("network called")),
        raising=False,
    )

    exit_code = run.main(["--validate-open-evidence"])
    output = capsys.readouterr().out

    assert exit_code == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "OPEN-EVIDENCE-VERIFIED"
    assert report["source_revision"] == "test-revision"
    assert report["all_citations_valid"] is True
    assert report["all_deterministic"] is True
    assert loaded_directories == [corpus_directory]
    assert "Fictional CLI orchestration text" not in json.dumps(report)
    assert "Fictional CLI orchestration text" not in output
    assert "NICE-VERIFIED" not in output


def test_validate_mode_fails_closed_for_missing_local_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
                {
                    "source_revision": "test-revision",
                    "acquisition_id": "20260909T170000Z",
                "sources": [
                    {
                        "pmcid": source.pmcid,
                        "retrieved_at_utc": "2026-09-09T12:00:00Z",
                        "sha256": "a" * 64,
                    }
                    for source in OPEN_EVIDENCE_SOURCES
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(run, "OPEN_EVIDENCE_MANIFEST", manifest_path, raising=False)
    corpus_directory = tmp_path / "open_evidence" / "corpora" / "20260909T170000Z"
    corpus_directory.mkdir(parents=True)
    monkeypatch.setattr(
        run, "OPEN_EVIDENCE_ROOT", tmp_path / "open_evidence", raising=False
    )
    monkeypatch.setattr(
        run,
        "load_local_open_articles",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            OpenEvidenceError("missing local evidence: PMC5256065")
        ),
        raising=False,
    )

    exit_code = run.main(["--validate-open-evidence"])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "missing local evidence" in output


def test_validate_mode_rejects_unsafe_manifest_acquisition_id_before_loading(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "source_revision": "test-revision",
                "acquisition_id": "../outside",
                "sources": [
                    {
                        "pmcid": source.pmcid,
                        "retrieved_at_utc": "2026-09-09T12:00:00Z",
                        "sha256": "a" * 64,
                    }
                    for source in OPEN_EVIDENCE_SOURCES
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(run, "OPEN_EVIDENCE_MANIFEST", manifest_path, raising=False)
    monkeypatch.setattr(
        run,
        "load_local_open_articles",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("loader called")),
        raising=False,
    )

    assert run.main(["--validate-open-evidence"]) == 1
    assert "Invalid acquisition identifier" in capsys.readouterr().out


def test_default_invocation_remains_offline(capsys: pytest.CaptureFixture[str]) -> None:
    assert run.main([]) == 0
    assert "no external data or API was used" in capsys.readouterr().out
