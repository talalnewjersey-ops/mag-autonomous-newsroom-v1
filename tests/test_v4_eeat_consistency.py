"""
NEXUS-14 V4 - tests/test_v4_eeat_consistency.py

CHARACTERIZATION tests for the EEAT consistency debt (Track 2).

These tests do NOT change any decision logic. They pin the CURRENT, REAL
behaviour of the two EEAT definitions so that the documented divergence
between them is explicit and any future drift is caught by CI:

  * scripts/quality_gate_v4.py  -> THRESHOLDS["eeat_required_elements"] (6 keys)
  * services/eeat_enrichment.py -> REQUIRED_ELEMENTS (8 keys)

The enrichment module claims to "mirror" the gate list. In reality it is a
STRICT SUPERSET: it additionally requires `author_credentials` and
`editorial_note`. That is recorded here as known technical debt; the gate
remains the authoritative publication decision and is left unchanged.
"""

import importlib

import pytest

from services.eeat_enrichment import (
    REQUIRED_ELEMENTS as ENRICH_REQUIRED,
    build_eeat_fields,
    validate_eeat,
)


def _gate_required():
    """Read the gate's required EEAT elements without running argparse/main."""
    qg = importlib.import_module("scripts.quality_gate_v4")
    return list(qg.THRESHOLDS["eeat_required_elements"])


# ---------------------------------------------------------------------------
# 1. Characterize the two lists exactly as they are today.
# ---------------------------------------------------------------------------

def test_gate_requires_exactly_six_elements():
    gate = _gate_required()
    assert gate == [
        "author", "review_date", "update_date",
        "official_references", "disclosure", "related_articles",
    ]
    assert len(gate) == 6


def test_enrichment_requires_exactly_eight_elements():
    assert ENRICH_REQUIRED == [
        "author", "author_credentials", "review_date", "update_date",
        "official_references", "related_articles", "disclosure", "editorial_note",
    ]
    assert len(ENRICH_REQUIRED) == 8


# ---------------------------------------------------------------------------
# 2. Pin the relationship: gate list is a SUBSET of the enrichment list,
#    and the divergence is exactly {author_credentials, editorial_note}.
# ---------------------------------------------------------------------------

def test_gate_elements_are_subset_of_enrichment():
    gate = set(_gate_required())
    enrich = set(ENRICH_REQUIRED)
    assert gate.issubset(enrich)


def test_enrichment_extra_elements_are_documented_debt():
    """The enrichment module enforces TWO elements the gate does not."""
    extra = set(ENRICH_REQUIRED) - set(_gate_required())
    assert extra == {"author_credentials", "editorial_note"}


def test_mirror_comment_is_not_literally_accurate():
    """eeat_enrichment claims to mirror the gate list; pin that it is a
    strict superset, not an equal set (this is the Track 2 debt)."""
    assert set(ENRICH_REQUIRED) != set(_gate_required())
    assert len(ENRICH_REQUIRED) > len(_gate_required())


# ---------------------------------------------------------------------------
# 3. Pin build_eeat_fields(): it must emit every key the GATE requires.
# ---------------------------------------------------------------------------

RICH_ARTICLE = {
    "author": "Jane Expert",
    "author_bio": "CFA, 10 years in cross-border payments",
    "review_date": "2026-01-10",
    "update_date": "2026-01-15",
    "editorial_note": "Reviewed by the editorial team.",
}
RICH_BODY = (
    "Sending money abroad is covered here. See the official guidance at "
    "https://www.irs.gov/individuals/international-taxpayers and "
    "https://www.canada.ca/en/services/taxes.html for details. "
    "Related reading: https://moneyabroadguide.com/best-transfer and "
    "https://moneyabroadguide.com/fees . Affiliate disclosure: we may earn "
    "a commission. This is general information only."
)


def test_build_fields_emits_all_gate_keys():
    fields = build_eeat_fields(RICH_ARTICLE, markdown=RICH_BODY)
    for key in _gate_required():
        assert key in fields, f"build_eeat_fields missing gate key: {key}"
        assert fields[key] not in (None, "", False, [], {})


def test_build_fields_extracts_official_references():
    fields = build_eeat_fields(RICH_ARTICLE, markdown=RICH_BODY)
    refs = fields["official_references"]
    assert any("irs.gov" in r for r in refs)
    assert any("canada.ca" in r for r in refs)


def test_build_fields_detects_disclosure_and_related():
    fields = build_eeat_fields(RICH_ARTICLE, markdown=RICH_BODY)
    assert fields["disclosure"] is True
    assert fields["related_articles"] is True


def test_build_fields_defaults_dates_when_absent():
    minimal = {"author": "A", "author_bio": "bio", "editorial_note": "note"}
    fields = build_eeat_fields(minimal, markdown="no links here")
    # dates fall back to today (ISO string), never empty.
    assert fields["review_date"]
    assert fields["update_date"]


# ---------------------------------------------------------------------------
# 4. Pin validate_eeat(): structural pass/fail + /8 score behaviour.
# ---------------------------------------------------------------------------

def test_validate_eeat_passes_on_complete_fields():
    fields = build_eeat_fields(RICH_ARTICLE, markdown=RICH_BODY)
    result = validate_eeat(fields)
    assert result["passed"] is True
    assert result["eeat_score"] == 100.0
    assert result["missing_elements"] == []


def test_validate_eeat_blocks_when_enrichment_extra_missing():
    """A meta that satisfies the GATE (6/6) can still FAIL the enrichment
    validator, because the latter also requires author_credentials +
    editorial_note. This is the concrete manifestation of the debt."""
    gate_only = {
        "author": "Jane Expert",
        "review_date": "2026-01-10",
        "update_date": "2026-01-15",
        "official_references": ["https://www.irs.gov/x"],
        "disclosure": True,
        "related_articles": True,
        # deliberately NO author_credentials, NO editorial_note
    }
    result = validate_eeat(gate_only)
    assert result["passed"] is False
    assert set(result["missing_elements"]) == {"author_credentials", "editorial_note"}


def test_validate_eeat_score_is_out_of_eight():
    """Score granularity is 100/8 = 12.5 per element; pin that scale."""
    one_missing = build_eeat_fields(RICH_ARTICLE, markdown=RICH_BODY)
    one_missing["editorial_note"] = ""
    result = validate_eeat(one_missing)
    assert result["passed"] is False
    assert result["eeat_score"] == 87.5  # 7/8 elements present
    assert result["missing_elements"] == ["editorial_note"]
