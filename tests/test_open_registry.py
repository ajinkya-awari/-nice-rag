from dataclasses import FrozenInstanceError, replace

import pytest

from src.open_registry import (
    ALLOWED_LICENSE_URIS,
    OPEN_EVIDENCE_SOURCES,
    OpenEvidenceSource,
    normalize_pmcid,
    validate_open_evidence_registry,
)


EXPECTED_IDENTITIES = (
    ("type_2_diabetes", "NG28", "PMC5256065", "10.3389/fendo.2017.00006"),
    ("pregnancy_hypertension", "NG133", "PMC7886065", "10.12703/b/9-10"),
    ("neuropathic_pain", "CG173", "PMC10741625", "10.3390/biom13121802"),
    ("adult_sepsis", "NG253", "PMC4410741", "10.1186/s12916-015-0335-2"),
    ("adult_safeguarding", "NG189", "PMC9261065", "10.1186/s12877-022-03243-9"),
)


def test_fixed_registry_has_exact_unique_open_evidence_identities() -> None:
    validated = validate_open_evidence_registry(OPEN_EVIDENCE_SOURCES)

    assert tuple(
        (
            source.topic_key,
            source.future_comparison_target,
            source.pmcid,
            source.doi,
        )
        for source in validated
    ) == EXPECTED_IDENTITIES
    assert len({source.topic_key for source in validated}) == 5
    assert len({source.pmcid for source in validated}) == 5
    assert len({source.doi for source in validated}) == 5
    assert all(
        source.canonical_url
        == f"https://pmc.ncbi.nlm.nih.gov/articles/{source.pmcid}/"
        for source in validated
    )
    assert all(
        source.expected_license_uri in ALLOWED_LICENSE_URIS for source in validated
    )


def test_source_records_are_immutable() -> None:
    with pytest.raises(FrozenInstanceError):
        OPEN_EVIDENCE_SOURCES[0].pmcid = "PMC1"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("topic_key", "type_2_diabetes", "duplicate topic key"),
        ("pmcid", "PMC5256065", "duplicate PMCID"),
        ("doi", "10.3389/fendo.2017.00006", "duplicate DOI"),
    ),
)
def test_registry_rejects_duplicate_identities(
    field: str, value: str, message: str
) -> None:
    first, second = OPEN_EVIDENCE_SOURCES[:2]
    duplicate = replace(second, **{field: value})

    with pytest.raises(ValueError, match=message):
        validate_open_evidence_registry((first, duplicate))


@pytest.mark.parametrize(
    ("change", "message"),
    (
        ({"pmcid": "NG28"}, "PMCID"),
        ({"doi": "https://doi.org/10.1/example"}, "DOI"),
        ({"title": "  "}, "title"),
        ({"canonical_url": "https://example.org/articles/PMC5256065/"}, "canonical URL"),
        (
            {
                "expected_license_uri": (
                    "https://creativecommons.org/licenses/by-nc/4.0/"
                )
            },
            "licence",
        ),
    ),
)
def test_registry_rejects_invalid_source_contracts(
    change: dict[str, str], message: str
) -> None:
    invalid = replace(OPEN_EVIDENCE_SOURCES[0], **change)

    with pytest.raises(ValueError, match=message):
        validate_open_evidence_registry((invalid,))


@pytest.mark.parametrize(
    ("value", "expected"),
    (("pmc5256065", "PMC5256065"), ("  PMC7886065  ", "PMC7886065")),
)
def test_normalize_pmcid_accepts_only_pmc_numeric_identifiers(
    value: str, expected: str
) -> None:
    assert normalize_pmcid(value) == expected


@pytest.mark.parametrize("value", ("5256065", "PMC", "PMC12x", "NG28"))
def test_normalize_pmcid_rejects_non_pmc_identifiers(value: str) -> None:
    with pytest.raises(ValueError, match="PMCID"):
        normalize_pmcid(value)


def test_open_source_type_rejects_positional_namespace_confusion() -> None:
    assert all(source.pmcid != source.future_comparison_target for source in OPEN_EVIDENCE_SOURCES)
    assert all(isinstance(source, OpenEvidenceSource) for source in OPEN_EVIDENCE_SOURCES)
