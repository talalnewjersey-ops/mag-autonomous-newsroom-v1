"""PART 2 -- minimal dangle filet in polish_prose (LAST RESORT for a stripped $/APR
that Couche 1 cannot supply). Offline, deletion-only.

Proves: a ';'-isolable dangling clause is dropped while the independent clause is
kept; a non-isolable dangle drops the WHOLE sentence (never a stump); the curated
signatures fire ("represents of", "drives of", "ranging to", "averaging on") while
ambiguous / valid usage is LEFT untouched (no over-deletion); deletion-only invariant.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.polish_prose import polish


def test_semicolon_clause_is_isolated_independent_clause_kept():
    out, _ = polish("payment history represents of your FICO score; a single late mark hurts a new score.")
    assert "represents of" not in out
    assert "a single late mark hurts a new score." in out


def test_non_isolable_dangle_drops_whole_sentence_no_stump():
    # dangle in the main clause with no ';' to isolate -> whole sentence goes, no subject stump
    out, _ = polish("Thin-file consumers face APRs averaging on entry-level credit products.")
    assert out.strip() == ""


def test_no_abbreviation_stump_or_runon():
    # a dangle after "U.S." must NOT strand "...of U.S." and must NOT run into the next sentence
    text = ("Requirements include 12 to 24 months of U.S. credit history, a down payment "
            "ranging to, and a ratio. These loans are portfolio loans.")
    out, _ = polish(text)
    assert "ranging to" not in out
    assert "These loans are portfolio loans." in out          # next sentence intact
    assert not re.search(r"\bU\.S\.\s+[A-Z][a-z]", out)       # no "U.S. These" run-on stump


def test_dropped_sentence_does_not_run_into_next():
    out, _ = polish("Consumers face APRs averaging on products. Choosing wrong increases cost.")
    assert out.strip() == "Choosing wrong increases cost."    # clean standalone survivor, no orphan


def test_ranging_to_dangle_dropped():
    out, _ = polish("Requirements include a down payment ranging to, and a debt-to-income ratio.")
    assert "ranging to" not in out


def test_drives_of_dangle_dropped():
    out, _ = polish("Pay on time — payment history drives of your FICO score.")
    assert "drives of" not in out


# ---- anti over-deletion: valid usage and mild phrasing are LEFT untouched ----

def test_valid_use_of_the_limit_is_untouched():
    s = "Open a secured card, keep low use of the limit monthly, and pay in full."
    assert polish(s)[0].strip() == s          # "use of the limit" is valid English -> not a dangle


def test_mild_reaching_within_is_untouched():
    s = "Most see a scoreable FICO within 3-6 months, with scores reaching within 12 months."
    assert polish(s)[0].strip() == s          # not a curated dangle -> left (Couche 1 / human, not over-delete)


def test_clean_prose_untouched():
    s = "Payment history is one of the factors that affect your credit score."
    assert polish(s)[0].strip() == s


# ---- deletion-only invariant: never reinvents ----

def test_deletion_only_no_new_word_or_digit():
    text = ("payment history represents of your FICO score; a late mark hurts. "
            "APRs averaging on cards. A down payment ranging to, and a ratio.")
    out, _ = polish(text)
    assert set(re.findall(r"\d", out)) <= set(re.findall(r"\d", text))
    assert set(re.findall(r"[a-z']+", out.lower())) <= set(re.findall(r"[a-z']+", text.lower()))


# ---- NEW scar shapes found on the us_credit control run (2026-07-05), verbatim ----

def test_capped_at_dangle_dropped():
    out, _ = polish("Federal credit unions offer PAL products with APRs capped at. Membership is required.")
    assert "capped at" not in out
    assert "Membership is required." in out


def test_cap_object_at_dangle_dropped():
    out, _ = polish("Most lenders cap DTI at; some CDFIs extend to for borrowers with stable rental history.")
    assert "cap DTI at" not in out and "extend to" not in out


def test_range_to_verb_tense_variant_dropped():
    # sibling of the already-covered "ranging to" -- different verb tense
    out, _ = polish("Loan amounts typically range to depending on the CDFI. Ask about fees.")
    assert "range to" not in out
    assert "Ask about fees." in out


def test_spans_with_dangle_dropped():
    out, _ = polish("The path from credit-invisible to credit-established typically spans with disciplined habits.")
    assert out.strip() == ""


# ---- anti over-deletion: the SAME phrasings with a REAL number following must
# survive untouched -- these are common, legitimate English constructions, unlike
# the original curated entries ("ranging to" alone is never valid on its own).

def test_capped_at_with_real_number_is_untouched():
    s = "FDIC deposit insurance is capped at $250,000 per depositor, per bank."
    assert polish(s)[0].strip() == s


def test_cap_object_at_with_real_number_is_untouched():
    s = "The program caps DTI at 43% for most conforming loans."
    assert polish(s)[0].strip() == s


def test_extends_to_with_real_number_is_untouched():
    s = "The introductory rate extends to 12 months before reverting to standard pricing."
    assert polish(s)[0].strip() == s


# ---- orphaned quote/apostrophe scar (a stripped quoted number left its mark) ----

def test_orphaned_apostrophe_is_removed():
    out, _ = polish("Landlords in major metros routinely require ' rent upfront as a credit substitute.")
    assert "'" not in out
    assert "require rent upfront as a credit substitute." in out


def test_real_contraction_apostrophe_is_untouched():
    s = "Don't skip a payment; it's the single biggest factor in your score."
    assert polish(s)[0].strip() == s


def test_new_patterns_deletion_only_no_new_word_or_digit():
    text = ("APRs capped at. Most lenders cap DTI at; some extend to for renters. "
            "Loan amounts range to depending on the CDFI. Landlords require ' rent upfront.")
    out, _ = polish(text)
    assert set(re.findall(r"\d", out)) <= set(re.findall(r"\d", text))
    assert set(re.findall(r"[a-z']+", out.lower())) <= set(re.findall(r"[a-z']+", text.lower()))
