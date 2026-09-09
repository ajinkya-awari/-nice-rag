"""Immutable identity and rights registry for the PMC open-evidence benchmark."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import re


PMC_ARTICLE_BASE_URL = "https://pmc.ncbi.nlm.nih.gov/articles"
ALLOWED_LICENSE_URIS = frozenset(
    {
        "https://creativecommons.org/licenses/by/4.0/",
        "https://creativecommons.org/publicdomain/zero/1.0/",
    }
)

_PMC_ID_PATTERN = re.compile(r"PMC[0-9]+")
_DOI_PATTERN = re.compile(r"10\.[0-9]{4,9}/\S+")
_NICE_ID_PATTERN = re.compile(r"(?:NG|CG)[0-9]+")


@dataclass(frozen=True, slots=True)
class OpenEvidenceSource:
    """Expected identity and machine-verifiable rights for one PMC record."""

    topic_key: str
    future_comparison_target: str
    pmcid: str
    doi: str
    title: str
    canonical_url: str
    expected_license_uri: str


def normalize_pmcid(value: str) -> str:
    """Normalize a PMCID while rejecting non-PMC namespaces."""
    normalized = value.strip().upper()
    if _PMC_ID_PATTERN.fullmatch(normalized) is None:
        raise ValueError(f"Invalid PMCID: {value!r}")
    return normalized


def validate_open_evidence_registry(
    sources: Iterable[OpenEvidenceSource],
) -> tuple[OpenEvidenceSource, ...]:
    """Validate and freeze a collection of open-evidence source contracts."""
    validated = tuple(sources)
    seen_topics: set[str] = set()
    seen_pmcids: set[str] = set()
    seen_dois: set[str] = set()

    for source in validated:
        if not source.topic_key.strip():
            raise ValueError("Open-evidence topic key must not be blank")
        if source.topic_key in seen_topics:
            raise ValueError(f"duplicate topic key: {source.topic_key}")
        seen_topics.add(source.topic_key)

        pmcid = normalize_pmcid(source.pmcid)
        if pmcid != source.pmcid:
            raise ValueError(f"PMCID must be canonical uppercase form: {source.pmcid}")
        if pmcid in seen_pmcids:
            raise ValueError(f"duplicate PMCID: {pmcid}")
        seen_pmcids.add(pmcid)

        if _NICE_ID_PATTERN.fullmatch(source.future_comparison_target) is None:
            raise ValueError(
                "future comparison target must use an NG or CG NICE identifier"
            )
        if source.future_comparison_target == pmcid:
            raise ValueError("PMCID and future comparison target must be separate")

        if _DOI_PATTERN.fullmatch(source.doi) is None or source.doi != source.doi.lower():
            raise ValueError(f"DOI must be canonical lowercase form: {source.doi}")
        if source.doi in seen_dois:
            raise ValueError(f"duplicate DOI: {source.doi}")
        seen_dois.add(source.doi)

        if not source.title.strip():
            raise ValueError("Open-evidence title must not be blank")
        expected_url = f"{PMC_ARTICLE_BASE_URL}/{pmcid}/"
        if source.canonical_url != expected_url:
            raise ValueError(f"Invalid canonical URL for {pmcid}")
        if source.expected_license_uri not in ALLOWED_LICENSE_URIS:
            raise ValueError(f"Disallowed or ambiguous licence for {pmcid}")

    return validated


OPEN_EVIDENCE_SOURCES = validate_open_evidence_registry(
    (
        OpenEvidenceSource(
            topic_key="type_2_diabetes",
            future_comparison_target="NG28",
            pmcid="PMC5256065",
            doi="10.3389/fendo.2017.00006",
            title=(
                "Clinical Review of Antidiabetic Drugs: Implications for Type 2 "
                "Diabetes Mellitus Management"
            ),
            canonical_url="https://pmc.ncbi.nlm.nih.gov/articles/PMC5256065/",
            expected_license_uri="https://creativecommons.org/licenses/by/4.0/",
        ),
        OpenEvidenceSource(
            topic_key="pregnancy_hypertension",
            future_comparison_target="NG133",
            pmcid="PMC7886065",
            doi="10.12703/b/9-10",
            title="Recent advances in the diagnosis and management of pre-eclampsia",
            canonical_url="https://pmc.ncbi.nlm.nih.gov/articles/PMC7886065/",
            expected_license_uri="https://creativecommons.org/licenses/by/4.0/",
        ),
        OpenEvidenceSource(
            topic_key="neuropathic_pain",
            future_comparison_target="CG173",
            pmcid="PMC10741625",
            doi="10.3390/biom13121802",
            title=(
                "Combination Drug Therapy for the Management of Chronic Neuropathic "
                "Pain"
            ),
            canonical_url="https://pmc.ncbi.nlm.nih.gov/articles/PMC10741625/",
            expected_license_uri="https://creativecommons.org/licenses/by/4.0/",
        ),
        OpenEvidenceSource(
            topic_key="adult_sepsis",
            future_comparison_target="NG253",
            pmcid="PMC4410741",
            doi="10.1186/s12916-015-0335-2",
            title="Recognizing and managing sepsis: what needs to be done?",
            canonical_url="https://pmc.ncbi.nlm.nih.gov/articles/PMC4410741/",
            expected_license_uri="https://creativecommons.org/licenses/by/4.0/",
        ),
        OpenEvidenceSource(
            topic_key="adult_safeguarding",
            future_comparison_target="NG189",
            pmcid="PMC9261065",
            doi="10.1186/s12877-022-03243-9",
            title="Staff-to-resident abuse in nursing homes: a scoping review",
            canonical_url="https://pmc.ncbi.nlm.nih.gov/articles/PMC9261065/",
            expected_license_uri="https://creativecommons.org/licenses/by/4.0/",
        ),
    )
)
