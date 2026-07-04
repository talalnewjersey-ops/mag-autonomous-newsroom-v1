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
