"""Couche 1 — injection of verified .gov facts into agent_04. Offline: no network,
no API key. Proves the SUPPLY mechanism (real figures handed to the writer) and,
critically, that VOLATILE facts are SOURCE-ONLY -- the withheld moving figure is
never re-injected via the value OR the internal note, and the writer is not invited
to invent one to fill the gap.

Reminder encoded here: this layer does NOT block hallucination (the writer can
ignore any prompt); the deterministic blockers are Couche 2 (soften) + Couche 3
(G-Substance). These tests only assert the supply/injection is correct.
"""
import inspect
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents import agent_04_article_writer as a4
from agents._vertical_facts import VERTICAL_FACTS

build = a4._build_facts_block


# ---------------- supply (STABLE) ----------------

def test_known_vertical_returns_nonempty_block():
    block = build("us_auto")
    assert block and "VERIFIED FACTS" in block


def test_stable_value_and_url_are_co_present():
    # For a STABLE fact the writer must get BOTH the figure and its .gov URL on the
    # same line so it can cite inline -> Sprint 10 detection then sees the link and
    # does not flag it.
    block = build("us_auto")
    tx = [l for l in block.splitlines() if "Texas" in l][0]
    assert "$30,000" in tx and "tdi.texas.gov" in tx


def test_stable_qualitative_uses_note_not_a_number():
    # value=None + STABLE => the safe qualitative note carries the content.
    block = build("us_auto")
    fl = [l for l in block.splitlines() if "foreign license" in l.lower()][0]
    assert "state driver's license" in fl and "usa.gov" in fl


# ---------------- VOLATILE golden (the guardrail the user asked for) ----------------

def test_volatile_fact_is_source_only_and_withholds_the_number():
    # CA minimum liability is VOLATILE. The withheld figure "30/60/25" lives only in
    # the internal note and must NOT reach the prompt; the source MUST still be
    # referenceable; the writer must be told to stay qualitative.
    block = build("us_auto")
    ca = [l for l in block.splitlines() if "California" in l][0]
    assert "insurance.ca.gov" in ca                      # source is referenceable
    assert "do NOT state a specific number" in ca        # not invited to invent
    # The CA figure must not reach the CA line (it lives only in the internal note).
    # NB: "30/60/25" legitimately appears elsewhere as Texas's STABLE sourced value,
    # so scope the withholding assertion to the California line itself.
    assert "30/60/25" not in ca
    assert not re.search(r"\$\s?\d", ca)                 # no dollar figure on the line


def test_volatile_regcc_threshold_not_leaked():
    block = build("us_banking")
    assert "federalreserve.gov" in block                 # source referenceable
    assert "$275" not in block and "$225" not in block   # inflation-adjusted figure withheld


def test_every_volatile_fact_line_has_no_bare_dollar_or_percent_figure():
    # Generalised: no VOLATILE line may hand the model a $ amount or a % value.
    for vert, facts in VERTICAL_FACTS.items():
        block = build(vert)
        for f in facts:
            if f.get("status") != "VOLATILE":
                continue
            line = [l for l in block.splitlines() if f["claim"] in l][0]
            assert not re.search(r"\$\s?\d", line), f"{vert}:{f['claim']} leaked a $ figure"
            assert not re.search(r"\d+\s?%", line), f"{vert}:{f['claim']} leaked a % figure"


# ---------------- routing / fallback ----------------

def test_unknown_vertical_returns_empty_block():
    assert build("us_default") == ""
    assert build("does_not_exist") == ""


def test_all_nine_verticals_render():
    for vert in VERTICAL_FACTS:
        assert build(vert).strip(), f"{vert} produced an empty facts block"


# ---------------- wiring into the prompts ----------------

def test_facts_block_wired_into_intro_and_sections():
    src = inspect.getsource(a4._write_article_standalone)
    # appended to the intro sourcing_block AND to the per-section sources block
    assert "_anti_fab + _facts_block" in src
    assert src.count("+ _facts_block") >= 2
