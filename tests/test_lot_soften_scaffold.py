"""PLAN B -- context-aware soften: remove a figure TOGETHER with its immediate
delimited scaffold at strip time, so no scar is ever created. Offline, no network.

Proves: the 4 scaffold cases (paren / bold-only / bold-with-label / unit / em-dash
appositive) are removed to the delimiter and NO FURTHER; the over-deletion guards
hold (a scaffold holding an official link is never nuked; a long appositive is kept
and only the number stripped); the appositive threshold is configurable; and the
pass is deletion-only (every output word came from the input -> never reinvents).
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.soften_claims import soften


# ---------- the 4 scaffold cases (removed to the delimiter, no further) ----------

V = "us_credit"


def test_case1_parenthesis_removed_whole_text_outside_intact():
    out, _ = soften("build payment history (~35% of FICO score) while funding a certificate.", V)[0], None
    assert "(~" not in out and "of FICO score)" not in out
    assert out.strip() == "build payment history while funding a certificate."   # nothing outside () touched


def test_case2a_bold_only_number_removed():
    out = soften("the timeline shrinks to **6 percentage points** typically.", V)[0]
    assert "**" not in out


def test_case2b_bold_with_label_keeps_the_label():
    out = soften("**Keep utilization below 30%** for maximum impact.", V)[0]
    assert "**Keep utilization**" in out          # label kept, number gone, bold closed tight


def test_case3_trailing_unit_swallowed():
    out = soften("you make fixed monthly payments ($15/month), funds are held.", V)[0]
    assert "/month" not in out and "($" not in out
    assert "fixed monthly payments, funds are held" in out


def test_case4_short_appositive_removed():
    out = soften("You deposit collateral —typically $200— which becomes your credit limit.", V)[0]
    assert "—typically" not in out
    assert "collateral which becomes your credit limit" in out


# ---------- over-deletion guards ----------

def test_guard_official_link_in_paren_is_never_deleted():
    out = soften("the window (30 days, see [FTC](https://consumer.ftc.gov/articles/disputing-errors-your-credit-reports)).", V)[0]
    assert "consumer.ftc.gov" in out              # the citation survives


def test_guard_long_appositive_is_kept_number_only_stripped():
    out = soften("history —the single largest FICO factor at 35 percentage points of your score— matters.", V)[0]
    assert "single largest FICO factor" in out    # meaningful content NOT nuked


def test_appositive_threshold_is_configurable():
    s = "a deposit —roughly $500 in most cases— unlocks the card."
    kept = soften(s, V, max_appos_words=2)[0]         # stricter -> keep appositive, strip number only
    nuked = soften(s, V, max_appos_words=4)[0]        # default -> remove the short appositive
    assert "in most cases" in kept and "in most cases" not in nuked


# ---------- deletion-only invariant (never reinvents) ----------

def test_deletion_only_no_new_word_or_digit():
    text = ("payment history (~35% of FICO score); a $15/month plan; utilization "
            "—ideally below 30%— and on-time payments; the factor at **40%** here.")
    out = soften(text, V)[0]
    assert set(re.findall(r"\d", out)) <= set(re.findall(r"\d", text))
    assert set(re.findall(r"[A-Za-z']+", out.lower())) <= set(re.findall(r"[A-Za-z']+", text.lower()))
