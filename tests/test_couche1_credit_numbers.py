"""Couche 1: the six us_credit facts added 2026-07-04 to kill the residual
invented-number scar class (draft 48438). Each was verbatim-verified on a .gov page.

This test LOCKS them against drift and, critically, against the two distortion traps
already seen: (a) a hard number that no source states (FICO-weight lesson) and
(b) an absolute pulled from a comparison (the credit-builder "60 points more than"
between-group figure). The only hard numbers allowed are 30 (CFPB en-318 utilization)
and 21 (CFPB en-20 under-21). Offline: no network, no API key.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents._vertical_facts import VERTICAL_FACTS
from agents._sources import _classify_url

FACTS = {f["claim"]: f for f in VERTICAL_FACTS["us_credit"]}
NEW = ["Credit utilization guidance", "Hard inquiry impact", "Credit card age rule (under 21)",
       "Credit-builder loan benefit", "Most impactful credit factor", "Credit-invisible US adults"]


def test_all_six_present():
    for c in NEW:
        assert c in FACTS, f"missing fact: {c}"


def test_every_source_is_allowlist_gov():
    for c in NEW:
        assert _classify_url(FACTS[c]["source_url"]) == "official", c   # cite protects from soften


def test_only_utilization_and_under21_carry_a_hard_number():
    # every OTHER new fact's value must be digit-free (no fabricated / distorted figure)
    for c in NEW:
        v = FACTS[c].get("value")
        if c in ("Credit utilization guidance", "Credit card age rule (under 21)"):
            continue
        assert not (v and re.search(r"\d", v)), f"{c} must not carry a number: {v!r}"


def test_utilization_number_is_the_sourced_30_percent():
    v = FACTS["Credit utilization guidance"]["value"]
    assert re.findall(r"\d+", v) == ["30"] and "30%" in v          # CFPB en-318 verbatim: 30 percent


def test_under21_number_is_only_21():
    v = FACTS["Credit card age rule (under 21)"]["value"]
    assert set(re.findall(r"\d+", v)) == {"21"} and "18" not in v  # page says under 21, never 18


def test_credit_builder_has_no_absolute_point_figure():
    # the "60 points" is a BETWEEN-GROUP comparison -> must never appear as an absolute
    v = FACTS["Credit-builder loan benefit"]["value"]
    assert "60" not in v and "point" not in v.lower()
    assert "can help" in v.lower()                                 # only the qualitative claim


def test_credit_invisible_is_volatile_source_only():
    f = FACTS["Credit-invisible US adults"]
    assert f["status"] == "VOLATILE" and f["value"] is None        # never a dated count (26M lesson)


def test_most_impactful_factor_is_qualitative_ranking():
    v = FACTS["Most impactful credit factor"]["value"]
    assert "greatest impact" in v and not re.search(r"\d", v)      # CFPB wording, no percentage
