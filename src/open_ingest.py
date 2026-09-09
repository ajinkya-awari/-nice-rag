"""Fail-closed JATS validation and provenance-first open-evidence ingestion."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import xml.etree.ElementTree as ET

from src.open_registry import (
    ALLOWED_LICENSE_URIS,
    OPEN_EVIDENCE_SOURCES,
    OpenEvidenceSource,
)
from src.pmc_client import PMC_OAI_BASE_URL, PmcResponse


OPEN_EVIDENCE_CORPUS = "pmc_open_evidence"
EXCLUDED_JATS_ELEMENTS = frozenset(
    {
        "ack",
        "author-notes",
        "caption",
        "disp-formula",
        "email",
        "fig",
        "fn-group",
        "graphic",
        "inline-formula",
        "media",
        "ref-list",
        "supplementary-material",
        "table",
        "table-wrap",
    }
)
_RETRACTION_RELATION_TYPES = frozenset(
    {"corrected-article", "expression-of-concern", "retracted-article"}
)


class OpenEvidenceError(RuntimeError):
    """Raised when source evidence violates identity, rights, or safety rules."""


@dataclass(frozen=True, slots=True)
class OpenSection:
    text: str
    metadata: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class OpenChunk:
    text: str
    metadata: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class ValidatedOpenArticle:
    source: OpenEvidenceSource
    sections: tuple[OpenSection, ...]
    source_sha256: str
    retrieved_at_utc: str
    byte_count: int
    license_uri: str
    http_status: int
    content_type: str
    retrieval_url: str


def _local_name(value: str) -> str:
    return value.rsplit("}", 1)[-1]


def _normalized_text(element: ET.Element) -> str:
    return " ".join("".join(element.itertext()).split())


def _elements(root: ET.Element, name: str) -> list[ET.Element]:
    return [element for element in root.iter() if _local_name(element.tag) == name]


def _children(root: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in root if _local_name(child.tag) == name]


def _required_path(root: ET.Element, names: tuple[str, ...], label: str) -> ET.Element:
    current = root
    for name in names:
        current = _required_single(_children(current, name), label)
    return current


def _required_single(elements: list[ET.Element], label: str) -> ET.Element:
    if len(elements) != 1:
        raise OpenEvidenceError(f"Expected exactly one {label}; found {len(elements)}")
    return elements[0]


def _normalize_doi(value: str) -> str:
    normalized = value.strip().casefold()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if normalized.startswith(prefix):
            normalized = normalized.removeprefix(prefix)
    return normalized


def _normalize_license_uri(value: str) -> str:
    normalized = value.strip()
    if normalized.startswith("http://creativecommons.org/"):
        normalized = "https://" + normalized.removeprefix("http://")
    return normalized


def _verified_license_uri(article: ET.Element, source: OpenEvidenceSource) -> str:
    candidates: set[str] = set()
    for license_element in _elements(article, "license"):
        for element in license_element.iter():
            for attribute, value in element.attrib.items():
                if _local_name(attribute) == "href" and "creativecommons.org/" in value:
                    candidates.add(_normalize_license_uri(value))
    if source.expected_license_uri not in candidates:
        observed = ", ".join(sorted(candidates)) or "missing"
        raise OpenEvidenceError(
            f"Machine-verifiable licence mismatch for {source.pmcid}: {observed}"
        )
    if not candidates <= ALLOWED_LICENSE_URIS:
        raise OpenEvidenceError(f"Disallowed licence metadata for {source.pmcid}")
    return source.expected_license_uri


def _validate_lifecycle(root: ET.Element, article: ET.Element) -> None:
    header = _required_single(_elements(root, "header"), "OAI header")
    if header.attrib.get("status", "").casefold() == "deleted":
        raise OpenEvidenceError("OAI record is deleted")
    if article.attrib.get("article-type", "").casefold() == "retracted-article":
        raise OpenEvidenceError("Article is marked as retracted")
    for related in _elements(article, "related-article"):
        relation = related.attrib.get("related-article-type", "").casefold()
        if relation in _RETRACTION_RELATION_TYPES:
            if relation == "expression-of-concern":
                raise OpenEvidenceError("Article has expression-of-concern metadata")
            raise OpenEvidenceError(f"Article has {relation} lifecycle metadata")


def _safe_element_text(element: ET.Element) -> str:
    pieces: list[str] = []

    def walk(node: ET.Element) -> None:
        if _local_name(node.tag) in EXCLUDED_JATS_ELEMENTS:
            return
        if node.text:
            pieces.append(node.text)
        for child in node:
            walk(child)
            if child.tail:
                pieces.append(child.tail)

    walk(element)
    return " ".join("".join(pieces).split())


def _direct_narrative_paragraphs(container: ET.Element) -> list[str]:
    paragraphs: list[str] = []

    def walk(node: ET.Element) -> None:
        for child in node:
            name = _local_name(child.tag)
            if name in EXCLUDED_JATS_ELEMENTS or name == "sec":
                continue
            if name == "p":
                text = _safe_element_text(child)
                if text:
                    paragraphs.append(text)
                continue
            walk(child)

    walk(container)
    return paragraphs


def _direct_title(section: ET.Element) -> str:
    for child in section:
        if _local_name(child.tag) == "title":
            return _normalized_text(child) or "Untitled section"
    return "Untitled section"


def _build_sections(
    body: ET.Element,
    source: OpenEvidenceSource,
    *,
    license_uri: str,
    retrieved_at_utc: str,
    source_sha256: str,
) -> tuple[OpenSection, ...]:
    section_values: list[tuple[str, str]] = []
    body_text = " ".join(_direct_narrative_paragraphs(body))
    if body_text:
        section_values.append(("Article body", body_text))

    def visit_sections(container: ET.Element) -> None:
        for child in container:
            if _local_name(child.tag) != "sec":
                continue
            text = " ".join(_direct_narrative_paragraphs(child))
            if text:
                section_values.append((_direct_title(child), text))
            visit_sections(child)

    visit_sections(body)
    sections: list[OpenSection] = []
    for section_index, (section_title, text) in enumerate(section_values):
        metadata: dict[str, object] = {
            "corpus": OPEN_EVIDENCE_CORPUS,
            "topic_key": source.topic_key,
            "pmcid": source.pmcid,
            "doi": source.doi,
            "article_title": source.title,
            "section_title": section_title,
            "section_index": section_index,
            "canonical_url": source.canonical_url,
            "license_uri": license_uri,
            "retrieved_at_utc": retrieved_at_utc,
            "source_sha256": source_sha256,
        }
        sections.append(OpenSection(text=text, metadata=metadata))
    if not sections:
        raise OpenEvidenceError("Article body contains no narrative text")
    return tuple(sections)


def validate_and_extract_record(
    source: OpenEvidenceSource,
    response: PmcResponse,
    retrieved_at_utc: str,
) -> ValidatedOpenArticle:
    """Validate one OAI/JATS record and extract narrative sections in memory."""
    if response.status != 200:
        raise OpenEvidenceError(f"Unexpected HTTP status: {response.status}")
    if response.content_type not in {"application/xml", "text/xml"}:
        raise OpenEvidenceError(f"Unexpected content type: {response.content_type}")
    if not retrieved_at_utc.strip():
        raise OpenEvidenceError("retrieved_at_utc is required")
    try:
        root = ET.fromstring(response.body)
    except ET.ParseError as exc:
        raise OpenEvidenceError("Malformed XML response") from exc

    errors = _elements(root, "error")
    if errors:
        code = errors[0].attrib.get("code", "unknown")
        raise OpenEvidenceError(f"OAI error: {code}")
    article = _required_single(_elements(root, "article"), "JATS article")
    article_meta = _required_path(
        article, ("front", "article-meta"), "JATS front article metadata"
    )
    _validate_lifecycle(root, article)

    header_identifier = _normalized_text(
        _required_single(_elements(root, "identifier"), "OAI identifier")
    )
    expected_identifier = f"oai:pubmedcentral.nih.gov:{source.pmcid.removeprefix('PMC')}"
    if header_identifier != expected_identifier:
        raise OpenEvidenceError("OAI PMCID identifier mismatch")

    article_ids = _children(article_meta, "article-id")
    pmc_values = [
        _normalized_text(element)
        for element in article_ids
        if element.attrib.get("pub-id-type", "").casefold() in {"pmc", "pmcid"}
    ]
    normalized_pmc_values = [
        value.upper() if value.upper().startswith("PMC") else f"PMC{value}"
        for value in pmc_values
    ]
    if normalized_pmc_values != [source.pmcid]:
        raise OpenEvidenceError("JATS PMCID mismatch")

    doi_values = [
        _normalize_doi(_normalized_text(element))
        for element in article_ids
        if element.attrib.get("pub-id-type", "").casefold() == "doi"
    ]
    if doi_values != [source.doi]:
        raise OpenEvidenceError("JATS DOI mismatch")

    title = _normalized_text(
        _required_path(
            article_meta,
            ("title-group", "article-title"),
            "front-matter article title",
        )
    )
    if title != " ".join(source.title.split()):
        raise OpenEvidenceError("JATS article title mismatch")

    license_uri = _verified_license_uri(article_meta, source)
    body = _required_single(_children(article, "body"), "JATS body")
    source_sha256 = hashlib.sha256(response.body).hexdigest()
    sections = _build_sections(
        body,
        source,
        license_uri=license_uri,
        retrieved_at_utc=retrieved_at_utc,
        source_sha256=source_sha256,
    )
    return ValidatedOpenArticle(
        source=source,
        sections=sections,
        source_sha256=source_sha256,
        retrieved_at_utc=retrieved_at_utc,
        byte_count=len(response.body),
        license_uri=license_uri,
        http_status=response.status,
        content_type=response.content_type,
        retrieval_url=response.final_url,
    )


def split_open_sections(
    sections: Iterable[OpenSection],
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> tuple[OpenChunk, ...]:
    """Split narrative sections while retaining all pre-attached provenance."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be non-negative and smaller than chunk_size")
    step = chunk_size - chunk_overlap
    chunks: list[OpenChunk] = []
    for section in sections:
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
        if not required <= section.metadata.keys():
            raise OpenEvidenceError("Section provenance must be attached before splitting")
        for chunk_index, start in enumerate(range(0, len(section.text), step)):
            end = min(start + chunk_size, len(section.text))
            metadata = dict(section.metadata)
            metadata["chunk_index"] = chunk_index
            chunks.append(OpenChunk(section.text[start:end], metadata))
            if end == len(section.text):
                break
    return tuple(chunks)


def store_validated_raw_record(
    article: ValidatedOpenArticle,
    body: bytes,
    raw_directory: Path,
) -> Path:
    """Atomically store validated bytes without replacing different evidence."""
    body_hash = hashlib.sha256(body).hexdigest()
    if body_hash != article.source_sha256:
        raise OpenEvidenceError("Refusing raw bytes with a different hash")
    raw_directory = Path(raw_directory)
    raw_directory.mkdir(parents=True, exist_ok=True)
    target = raw_directory / f"{article.source.pmcid}.xml"
    if target.exists():
        existing_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        if existing_hash == body_hash:
            return target
        raise OpenEvidenceError(f"Existing {article.source.pmcid} has a different hash")

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=raw_directory,
            prefix=f".{article.source.pmcid}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(body)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, target)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return target


def load_local_open_articles(
    sources: Iterable[OpenEvidenceSource] = OPEN_EVIDENCE_SOURCES,
    raw_directory: Path = Path("data/open_evidence/raw"),
    *,
    retrieved_at_utc: str,
) -> tuple[ValidatedOpenArticle, ...]:
    """Load and revalidate an exact local corpus without network access."""
    expected_sources = tuple(sources)
    raw_directory = Path(raw_directory)
    missing = [
        source.pmcid
        for source in expected_sources
        if not (raw_directory / f"{source.pmcid}.xml").is_file()
    ]
    if missing:
        raise OpenEvidenceError(f"missing local evidence: {', '.join(missing)}")
    unexpected = sorted(
        path.stem
        for path in raw_directory.glob("*.xml")
        if path.stem not in {source.pmcid for source in expected_sources}
    )
    if unexpected:
        raise OpenEvidenceError(f"unexpected local evidence: {', '.join(unexpected)}")

    articles: list[ValidatedOpenArticle] = []
    for source in expected_sources:
        body = (raw_directory / f"{source.pmcid}.xml").read_bytes()
        articles.append(
            validate_and_extract_record(
                source,
                PmcResponse(
                    body=body,
                    status=200,
                    content_type="application/xml",
                    final_url=PMC_OAI_BASE_URL,
                ),
                retrieved_at_utc,
            )
        )
    return tuple(articles)


def write_sanitized_manifest(
    articles: Iterable[ValidatedOpenArticle],
    path: Path,
    *,
    source_revision: str,
) -> None:
    """Write metadata-only acquisition evidence with no extracted prose."""
    article_values = tuple(articles)
    manifest = {
        "schema_version": 1,
        "source_revision": source_revision,
        "corpus": OPEN_EVIDENCE_CORPUS,
        "retrieval_method": "PMC OAI-PMH GetRecord metadataPrefix=pmc",
        "sources": [
            {
                "topic_key": article.source.topic_key,
                "pmcid": article.source.pmcid,
                "doi": article.source.doi,
                "title": article.source.title,
                "canonical_url": article.source.canonical_url,
                "license_uri": article.license_uri,
                "retrieved_at_utc": article.retrieved_at_utc,
                "http_status": article.http_status,
                "content_type": article.content_type,
                "byte_count": article.byte_count,
                "sha256": article.source_sha256,
                "section_count": len(article.sections),
                "chunk_count": len(split_open_sections(article.sections)),
                "excluded_components": sorted(EXCLUDED_JATS_ELEMENTS),
                "validation_status": "validated",
            }
            for article in article_values
        ],
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
