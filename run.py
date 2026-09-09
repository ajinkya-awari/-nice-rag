"""Local entrypoint for import-safe Project 19 offline checks."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
from time import sleep

from src.evaluation import render_offline_evaluation_plan
from src.offline_cpu import render_cpu_stress_report, run_cpu_stress_check
from src.open_ingest import (
    OpenEvidenceError,
    create_staging_corpus,
    load_local_open_articles,
    promote_staging_corpus,
    resolve_promoted_corpus,
    store_validated_raw_record,
    validate_and_extract_record,
    write_sanitized_manifest,
)
from src.open_registry import OPEN_EVIDENCE_SOURCES, validate_open_evidence_registry
from src.open_retrieval import validate_open_queries, write_open_validation_report
from src.pmc_client import PmcClientError, fetch_pmc_record
from src.protocol import RESEARCH_DISCLAIMER


OPEN_EVIDENCE_ROOT = Path("data/open_evidence")
OPEN_EVIDENCE_MANIFEST = Path("evidence/open_evidence_manifest.json")
OPEN_EVIDENCE_VALIDATION = Path("evidence/open_evidence_validation.json")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _source_revision() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return "unavailable"
    return completed.stdout.strip() or "unavailable"


def _acquisition_id() -> str:
    return _utc_now().replace("-", "").replace(":", "")


def _safe_error_message(exc: Exception) -> str:
    if isinstance(exc, OSError):
        return "local storage operation failed"
    return str(exc)


def _remove_new_transaction_directory(directory: Path) -> None:
    if directory.is_dir():
        shutil.rmtree(directory)


def _fetch_open_evidence() -> int:
    sources = validate_open_evidence_registry(OPEN_EVIDENCE_SOURCES)
    retrieved_at_utc = _utc_now()
    acquisition_id = _acquisition_id()
    try:
        staging_directory = create_staging_corpus(
            OPEN_EVIDENCE_ROOT, acquisition_id
        )
    except (OpenEvidenceError, OSError, ValueError) as exc:
        print(f"ERROR open-evidence acquisition: {_safe_error_message(exc)}")
        return 1
    articles = []
    for index, source in enumerate(sources):
        try:
            response = fetch_pmc_record(source)
            article = validate_and_extract_record(source, response, retrieved_at_utc)
            store_validated_raw_record(article, response.body, staging_directory)
        except (OpenEvidenceError, PmcClientError, OSError, ValueError) as exc:
            _remove_new_transaction_directory(staging_directory)
            print(f"ERROR {source.pmcid}: {_safe_error_message(exc)}")
            return 1
        articles.append(article)
        print(
            f"validated {source.pmcid} licence={article.license_uri} "
            f"bytes={article.byte_count} sha256={article.source_sha256}"
        )
        if index < len(sources) - 1:
            sleep(0.4)

    promoted_directory: Path | None = None
    try:
        promoted_directory = promote_staging_corpus(
            OPEN_EVIDENCE_ROOT, staging_directory, acquisition_id
        )
        write_sanitized_manifest(
            articles,
            OPEN_EVIDENCE_MANIFEST,
            source_revision=_source_revision(),
            acquisition_id=acquisition_id,
        )
    except (OpenEvidenceError, OSError, TypeError, ValueError) as exc:
        _remove_new_transaction_directory(promoted_directory or staging_directory)
        print(f"ERROR open-evidence manifest: {_safe_error_message(exc)}")
        return 1
    print(f"open_evidence_sources={len(articles)} acquisition_status=VALIDATED")
    return 0


def _read_manifest() -> dict[str, object]:
    if not OPEN_EVIDENCE_MANIFEST.is_file():
        raise OpenEvidenceError("open-evidence manifest is missing")
    try:
        manifest = json.loads(OPEN_EVIDENCE_MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OpenEvidenceError("open-evidence manifest JSON is invalid") from exc
    if not isinstance(manifest, dict):
        raise OpenEvidenceError("open-evidence manifest root must be an object")
    return manifest


def _validate_open_evidence() -> int:
    try:
        manifest = _read_manifest()
        source_entries = manifest.get("sources")
        if not isinstance(source_entries, list) or len(source_entries) != len(
            OPEN_EVIDENCE_SOURCES
        ):
            raise OpenEvidenceError("manifest must contain exactly five sources")
        entries_by_pmcid = {
            entry.get("pmcid"): entry
            for entry in source_entries
            if isinstance(entry, dict)
        }
        expected_pmcids = {source.pmcid for source in OPEN_EVIDENCE_SOURCES}
        if set(entries_by_pmcid) != expected_pmcids:
            raise OpenEvidenceError("manifest PMCID set differs from the fixed registry")
        retrieval_times = {
            entry.get("retrieved_at_utc") for entry in entries_by_pmcid.values()
        }
        if len(retrieval_times) != 1 or not all(
            isinstance(value, str) and value for value in retrieval_times
        ):
            raise OpenEvidenceError("manifest retrieval timestamps are inconsistent")
        retrieved_at_utc = next(iter(retrieval_times))
        acquisition_id = manifest.get("acquisition_id")
        if not isinstance(acquisition_id, str):
            raise OpenEvidenceError("manifest acquisition identifier is missing")
        raw_directory = resolve_promoted_corpus(OPEN_EVIDENCE_ROOT, acquisition_id)
        articles = load_local_open_articles(
            OPEN_EVIDENCE_SOURCES,
            raw_directory,
            retrieved_at_utc=retrieved_at_utc,
        )
        for article in articles:
            entry = entries_by_pmcid[article.source.pmcid]
            if entry.get("sha256") != article.source_sha256:
                raise OpenEvidenceError(
                    f"manifest hash mismatch for {article.source.pmcid}"
                )
        source_revision = manifest.get("source_revision")
        if not isinstance(source_revision, str) or not source_revision:
            raise OpenEvidenceError("manifest source revision is missing")
        report = validate_open_queries(
            articles,
            repeats=2,
            source_revision=source_revision,
        )
        write_open_validation_report(report, OPEN_EVIDENCE_VALIDATION)
    except (OpenEvidenceError, OSError, TypeError, ValueError) as exc:
        print(f"ERROR open-evidence validation: {_safe_error_message(exc)}")
        return 1

    print(
        f"status={report['status']} sources={report['source_count']} "
        f"scenarios={report['scenario_count']} "
        f"max_passages={report['maximum_passage_count']} "
        f"all_citations_valid={report['all_citations_valid']} "
        f"all_deterministic={report['all_deterministic']}"
    )
    return 0 if report["status"] == "OPEN-EVIDENCE-VERIFIED" else 1


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
    modes.add_argument(
        "--list-open-sources",
        action="store_true",
        help="list the fixed PMC open-evidence registry without network access",
    )
    modes.add_argument(
        "--fetch-open-evidence",
        action="store_true",
        help="explicitly fetch and validate the five fixed PMC OAI records",
    )
    modes.add_argument(
        "--validate-open-evidence",
        action="store_true",
        help="validate previously acquired local PMC records without network access",
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
    if arguments.list_open_sources:
        for source in validate_open_evidence_registry(OPEN_EVIDENCE_SOURCES):
            print(
                f"{source.topic_key}\t{source.pmcid}\t{source.doi}\t"
                f"{source.expected_license_uri}"
            )
        return 0
    if arguments.fetch_open_evidence:
        return _fetch_open_evidence()
    if arguments.validate_open_evidence:
        return _validate_open_evidence()

    print("NICE-RAG local scaffold: no external data or API was used.")
    print(RESEARCH_DISCLAIMER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
