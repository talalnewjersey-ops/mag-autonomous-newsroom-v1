"""LEVIER C -- commercial-figure qualification (table-scoped) + image-caption
leak fix. Offline, no network, no LLM.

Context: reading two published articles surfaced that unsourced COMMERCIAL
figures (bank rates, insurance prices -- never engraved in Couche 1, which only
holds government facts) were handled well in prose (strip-and-keep-clause,
already proven) but badly in a COMPARISON TABLE on one article: the same rate
stated inconsistently across sections/rows, presented as a firm fact. Fix,
table-scoped only: scripts/soften_claims.py's table-cell softening now inserts
a FIXED, constant phrase ("varies by provider — confirm directly") instead of
a bare "varies" -- literal, never templated/generated, so it can never itself
invent or vary a figure. Verified here: it never varies text-to-text, and it
does not conflict with G3 (agents/_claims and scripts/g3_repetition_gate.py),
even when repeated many times within one table.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.soften_claims import soften, _TABLE_QUALIFIER
from scripts.g3_repetition_gate import evaluate as g3_evaluate

V = "canada_newcomer"  # no us_credit-specific fact could ever cover a bank rate anyway


def test_qualifier_is_the_documented_fixed_phrase():
    assert _TABLE_QUALIFIER == "varies by provider — confirm directly"


def test_uncovered_commercial_rate_in_table_gets_the_fixed_qualifier():
    row = "| EQ Bank | 2.75% | no monthly fee |"
    out, rep = soften(row, V)
    assert "2.75%" not in out
    assert _TABLE_QUALIFIER in out
    assert rep["table_cells_softened"] >= 1


def test_qualifier_never_varies_across_different_commercial_figures():
    # Different rates/prices in different cells -> the EXACT SAME literal phrase
    # every time -- proof it is a constant, never generated from the cell content.
    cases = [
        "| EQ Bank | 2.75% | monthly |",
        "| Wealthsimple | $500 minimum | no fee |",
        "| Tangerine | up to 3.00% | promo rate |",
    ]
    outputs = [soften(row, V)[0] for row in cases]
    for out in outputs:
        assert _TABLE_QUALIFIER in out
    # every occurrence, across every case, is byte-identical
    import re
    all_occurrences = [m for out in outputs for m in re.findall(r"varies by provider.*?directly", out)]
    assert len(set(all_occurrences)) == 1


def test_qualifier_has_no_digit_and_is_not_reflagged_as_unsourced():
    # The qualifier itself must never become a NEW unsourced claim (it has no
    # digit, so _NUM_RE cannot match it -- confirmed by re-softening the output).
    row = "| EQ Bank | 2.75% | monthly |"
    out, _ = soften(row, V)
    twice, rep2 = soften(out, V)
    assert twice == out and rep2["unsourced_found"] == 0


def test_no_g3_conflict_even_with_many_repetitions_in_one_table():
    # Empirically run G3 (not just reasoned about): the same fixed 4-content-word
    # phrase repeated 12+ times inside one comparison table must still PASS --
    # G3's duplicate-phrase check requires >=8 content words AND two DIFFERENT
    # sections; a within-table repeat of a 4-word phrase satisfies neither.
    table = "\n".join(f"| Bank {i} | {_TABLE_QUALIFIER} | {_TABLE_QUALIFIER} |" for i in range(6))
    md = f"""## Overview
Some intro text about savings accounts for newcomers in Canada, covering the basics
of what to look for for.

## Comparison
{table}

## Frequently Asked Questions
### Do rates change?
Yes, {_TABLE_QUALIFIER}.
"""
    result = g3_evaluate(md)
    assert result["decision"] == "PASS"
    assert result["blocking_dup_count"] == 0
    assert result["max_pairwise_cosine"] < result["cosine_threshold"]


def test_prose_qualification_unchanged_table_scope_only():
    # Short prose keeps the EXISTING strip-and-keep-clause behavior (already
    # proven on the insurance article) -- the fixed qualifier is NEVER inserted
    # into prose, only table cells.
    text = "Rates at this bank run about 2.75% for new customers with no history."
    out, rep = soften(text, V)
    assert _TABLE_QUALIFIER not in out
    assert "2.75%" not in out
    assert rep["stripped"] >= 1
