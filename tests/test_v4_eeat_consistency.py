"""
NEXUS-14 V4 - tests/test_v4_eeat_consistency.py

ALIGNMENT tests for the EEAT required-element set (Approach B / B1).

Track 2 debt RESOLVED: the gate and the enrichment engine now share ONE
source of truth for the required EEAT elements:

* services/eeat_enrichment.py -> REQUIRED_EEAT_KEYS (authoritative, 8 keys)
* scripts/quality_gate_v4.py   -> THRESHOLDS["eeat_required_elements"] imports
  REQUIRED_EEAT_KEYS (no longer a hard-coded 6-key list).

These tests pin the NEW behaviour:
  1. both definitions are identical (no silent divergence possible);
  2. the canonical list is exactly the 8 keys;
  3. a meta carrying only the legacy 6 gate keys now FAILS check_eeat
     (publication behaviour is intentionally stricter under B1);
  4. build_eeat_fields() / validate_eeat() still behave on the /8 scale.

They WOULD fail if anyone reintroduced a divergent or 6-key gate list,
which is exactly the regression we want CI to catch.
"""

import importlib

import pytest

from services.eeat_enrichment import (
    REQUIRED_EEAT_KEYS,
    REQUIRED_ELEMENTS as ENRICH_REQUIRED,
    build_eeat_fields,
    validate_eeat,
)


def _gate_module():
    return importlib.import_module("scripts.quality_gate_v4")


def _gate_required():
    """Read the gate's required EEAT elements without running argparse/main."""
    return list(_gate_module().THRESHOLDS["eeat_required_elements"])


# ---------------------------------------------------------------------------
# 1. Single source of truth: gate list IS the enrichment list.
# ---------------------------------------------------------------------------

CANONICAL_KEYS = [
    "author", "author_credentials", "review_date", "update_date",
    "official_references", "related_articles", "disclosure", "editorial_note",
]


def test_canonical_list_is_exactly_eight_keys():
    assert REQUIRED_EEAT_KEYS == CANONICAL_KEYS
    assert len(REQUIRED_EEAT_KEYS) == 8


def test_enrichment_alias_points_at_canonical_list():
    # REQUIRED_ELEMENTS is kept as a backwards-compatible alias.
    assert ENRICH_REQUIRED is REQUIRED_EEAT_KEYS


def test_gate_imports_the_shared_required_keys():
    gate = _gate_module()
    # The gate threshold object must BE the shared constant (identity),
    # proving it imports rather than redeclaring its own list.
    assert gate.THRESHOLDS["eeat_required_elements"] is REQUIRED_EEAT_KEYS


def test_gate_and_enrichment_are_identical_no_divergence():
    assert _gate_required() == list(REQUIRED_EEAT_KEYS)
    assert set(_gate_required()) == set(ENRICH_REQUIRED)


def test_no_extra_or_missing_elements_between_the_two():
    diff = set(ENRICH_REQUIRED) ^ set(_gate_required())  # symmetric difference
    assert diff == set()


# ---------------------------------------------------------------------------
# 2. New publication behaviour: the gate now enforces all 8 keys.
#    A meta carrying only the legacy 6 keys must now be BLOCKED.
# ---------------------------------------------------------------------------

GATE_ONLY_LEGACY_6 = {
    "author": "Jane Expert",
    "review_date": "2026-01-10",
    "update_date": "2026-01-15",
    "official_references": ["https://www.irs.gov/x"],
    "disclosure": True,
    "related_articles": True,
    # deliberately NO author_credentials, NO editorial_note
}


def test_gate_check_eeat_blocks_legacy_six_key_meta():
    """Under B1, satisfying only the old 6 keys is no longer enough."""
    gate = _gate_module()
    result = gate.check_eeat(GATE_ONLY_LEGACY_6)
    assert result["passed"] is False
    assert set(result["missing_elements"]) == {"author_credentials", "editorial_note"}


def test_gate_check_eeat_passes_full_eight_key_meta():
    gate = _gate_module()
    full = dict(GATE_ONLY_LEGACY_6)
    full["author_credentials"] = "CFA, 10y cross-border payments"
    full["editorial_note"] = "Reviewed by the editorial team."
    result = gate.check_eeat(full)
    assert result["passed"] is True
    assert result["missing_elements"] == []


def test_build_eeat_fields_output_passes_the_gate():
    """The enrichment output is shaped to satisfy the (now 8-key) gate."""
    gate = _gate_module()
    fields = build_eeat_fields(RICH_ARTICLE, markdown=RICH_BODY)
    result = gate.check_eeat(fields)
    assert result["passed"] is True
    assert result["missing_elements"] == []


# ---------------------------------------------------------------------------
# 3. build_eeat_fields(): emits every canonical key, truthy.
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


def test_build_fields_emits_all_canonical_keys():
    fields = build_eeat_fields(RICH_ARTICLE, markdown=RICH_BODY)
    for key in REQUIRED_EEAT_KEYS:
        assert key in fields, f"build_eeat_fields missing key: {key}"
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
    assert fields["review_date"]
    assert fields["update_date"]


# ---------------------------------------------------------------------------
# 4. validate_eeat(): structural pass/fail + /8 score behaviour.
# ---------------------------------------------------------------------------

def test_validate_eeat_passes_on_complete_fields():
    fields = build_eeat_fields(RICH_ARTICLE, markdown=RICH_BODY)
    result = validate_eeat(fields)
    assert result["passed"] is True
    assert result["eeat_score"] == 100.0
    assert result["missing_elements"] == []


def test_validate_eeat_blocks_when_keys_missing():
    result = validate_eeat(GATE_ONLY_LEGACY_6)
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
