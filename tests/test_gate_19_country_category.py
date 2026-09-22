#!/usr/bin/env python3
"""Unit tests for Gate 19 country/category validation.
Run: pytest tests/test_gate_19_country_category.py -q
Pure-function tests; no network or WordPress calls required.
"""

import importlib.util
from pathlib import Path

MOD_PATH = Path(__file__).resolve().parents[1] / "scripts" / "gate_19_country_category.py"
spec = importlib.util.spec_from_file_location("gate_19", MOD_PATH)
gate_19 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate_19)

CMAP = gate_19.DEFAULT_CATEGORY_COUNTRY_MAP
USA_CAT = {"id": 17, "slug": "newcomers-to-the-usa"}
CAN_CAT = {"id": 18, "slug": "newcomers-to-canada"}
BANKING = {"id": 7, "slug": "banking"}
UNMAPPED = {"id": 99, "slug": "some-new-category"}


def test_usa_article_in_usa_category_passes():
    r = gate_19.validate("ITIN and SSN guidance for newcomers.",
                         "Best Banks for ITIN Holders in the USA",
                         "best-banks-itin-usa", [USA_CAT], CMAP, mode="blocking")
    assert r["verdict"] == "PASS"
    assert r["blocking"] is False


def test_usa_article_in_canada_category_fails():
    r = gate_19.validate("ITIN and SSN guidance, IRS rules for newcomers.",
                         "Best Banks for ITIN Holders in the USA",
                         "best-banks-itin-usa", [CAN_CAT], CMAP, mode="blocking")
    assert r["verdict"] == "FAIL"
    assert r["blocking"] is True


def test_canada_article_in_usa_category_fails():
    r = gate_19.validate("RRSP, TFSA and CRA rules for newcomers to Canada.",
                         "RRSP Guide for Newcomers to Canada",
                         "rrsp-guide-canada", [USA_CAT], CMAP, mode="blocking")
    assert r["verdict"] == "FAIL"
    assert r["blocking"] is True


def test_neutral_category_never_conflicts():
    r = gate_19.validate("ITIN and IRS guidance.", "USA Banking Basics",
                         "usa-banking-basics", [BANKING], CMAP, mode="blocking")
    assert r["verdict"] == "PASS"


def test_unmapped_category_routes_to_manual_review():
    r = gate_19.validate("ITIN and IRS guidance.", "USA Banking Basics",
                         "usa-banking-basics", [UNMAPPED], CMAP, mode="blocking")
    assert r["verdict"] == "MANUAL_REVIEW"
    assert r["blocking"] is True


def test_unknown_country_routes_to_manual_review():
    r = gate_19.validate("General budgeting tips.", "How to Budget Monthly",
                         "how-to-budget", [BANKING], CMAP, mode="blocking")
    assert r["detected_country"] == "UNKNOWN"
    assert r["verdict"] == "MANUAL_REVIEW"


def test_warning_mode_never_blocks_even_on_fail():
    r = gate_19.validate("RRSP and CRA rules for Canada.",
                         "RRSP Guide for Newcomers to Canada",
                         "rrsp-guide-canada", [USA_CAT], CMAP, mode="warning")
    assert r["verdict"] == "FAIL"
    assert r["blocking"] is False  # warning mode observes but does not block


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
