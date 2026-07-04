"""Couche 1 CAS (b): the us_credit "Credit score factors" fact -- factors ONLY, no
percentages, no ranking, sourced to a verified allow-list .gov page (usa.gov, which
lists the factors but states NO weights and NO hierarchy -- verbatim-verified).

Offline. This test LOCKS the fact against drift: no digit / percentage, no positive
hierarchy claim, source-faithful terms (not FICO marketing names), .gov allow-list.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents._vertical_facts import VERTICAL_FACTS
from agents._sources import _classify_url


def _fact():
    return next(f for f in VERTICAL_FACTS["us_credit"] if f["claim"] == "Credit score factors")


def test_fact_exists_and_is_stable():
    f = _fact()
    assert f["status"] == "STABLE" and f["last_reviewed"]


def test_no_percentage_or_weight_number_engraved():
    # CAS (b): the exact percentages are NOT on any verified .gov page -> never engrave one.
    assert not re.search(r"\d", _fact()["value"])


def test_no_positive_hierarchy_claim():
    v = _fact()["value"]
    assert not re.search(r"most important|most significant|largest factor|biggest|primary factor|top factor", v, re.I)
    assert "without ranking" in v  # the explicit no-hierarchy guard is present


def test_uses_source_terms_not_fico_marketing():
    v = _fact()["value"]
    assert "outstanding balances" in v and "types of credit accounts" in v
    assert "amounts owed" not in v and "credit mix" not in v


def test_source_is_a_verified_allowlist_gov_page():
    f = _fact()
    assert f["source_url"] == "https://www.usa.gov/credit-score"
    assert _classify_url(f["source_url"]) == "official"   # in the .gov allow-list -> protects the cite from soften


def test_lists_all_five_factors():
    v = _fact()["value"].lower()
    for factor in ("payment history", "outstanding balances", "length of credit history",
                   "applications for new credit", "types of credit accounts"):
        assert factor in v
