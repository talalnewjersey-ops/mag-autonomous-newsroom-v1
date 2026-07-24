"""Regression lock: agent_03's fallback title/heading generation must not
produce broken-case acronyms or an awkward "Best" prefix on question-form
keywords -- both real bugs found by human review (2026-07-24):
  - posts 48997/49005 (and, via GATE D's own scan_title, 48870/48854):
    "Best Essential First Documents In Canada Sin", "...Ssn Itin" -- Python's
    bare str.title() has no concept of acronyms.
  - posts 48982/49047: "Best Does My Home Country Credit Score Transfer",
    "Best How To Get Your Free Credit Report In The USA" -- "Best" doesn't
    combine naturally with an already-question-form keyword.

Offline: no network, no API key.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents._placeholder_scan import smart_title_case, scan_title
from agents.agent_03_content_planner import _norm_kw, _title_lead, _build_fallback_outline


# ---------------- smart_title_case ----------------

def test_smart_title_case_fixes_all_four_real_broken_acronyms():
    cases = {
        "essential first documents in canada sin": "SIN",
        "essential documents for new immigrants ssn itin": "SSN",
        "how to get your free credit report in the usa": "USA",
        "how to rent an apartment without ssn or credit": "SSN",
    }
    for kw, acronym in cases.items():
        out = smart_title_case(kw)
        assert acronym in out.split(), f"{kw!r} -> {out!r}, missing bare {acronym!r}"
        # and never the broken Title-Case form
        assert acronym.capitalize() not in out.split()


def test_smart_title_case_leaves_ordinary_words_alone():
    assert smart_title_case("renters insurance") == "Renters Insurance"


def test_smart_title_case_output_never_trips_gate_d_title_scan():
    # closes the loop: the generator's own output must satisfy the detector
    # scan_title() was built to catch this bug class in the first place.
    for kw in (
        "essential first documents in canada sin",
        "essential documents for new immigrants ssn itin",
        "how to get your free credit report in the usa",
    ):
        title = f"Best {smart_title_case(kw)}: Complete Guide for USA Immigrants (2026)"
        assert not scan_title(title), f"{title!r} still trips scan_title()"


# ---------------- _norm_kw ----------------

def test_norm_kw_fixes_acronyms_and_strips_leading_best():
    assert _norm_kw("best essential documents ssn itin") == "Essential Documents SSN ITIN"
    assert _norm_kw("essential first documents in canada sin") == "Essential First Documents In Canada SIN"


def test_norm_kw_collapses_duplicate_words():
    assert _norm_kw("bank bank account") == "Bank Account"


# ---------------- _title_lead ----------------

def test_title_lead_omits_best_for_question_form_keywords():
    cases = [
        "How To Get Your Free Credit Report In The USA",
        "Does My Home Country Credit Score Transfer",
        "What Is A Credit Builder Loan",
        "Can I Open A Bank Account Without An SSN",
    ]
    for kw in cases:
        assert _title_lead(kw) == kw, f"{kw!r} should not get a 'Best ' prefix"


def test_title_lead_keeps_best_for_ordinary_noun_phrases():
    assert _title_lead("Renters Insurance") == "Best Renters Insurance"
    assert _title_lead("Credit Builder Loans") == "Best Credit Builder Loans"


# ---------------- end-to-end fallback outline ----------------

def test_fallback_outline_title_matches_real_49047_shape_correctly():
    topic = {"keyword": "how to get your free credit report in the usa", "market": "USA"}
    outline = _build_fallback_outline(topic)
    assert outline["title"].startswith("How To Get Your Free Credit Report In The USA:")
    assert "Best How To" not in outline["title"]
    assert not scan_title(outline["title"])


def test_fallback_outline_title_matches_real_48997_49005_shape_correctly():
    topic = {"keyword": "essential first documents in canada sin", "market": "Canada"}
    outline = _build_fallback_outline(topic)
    assert "Sin" not in outline["title"].replace(":", " ").split()
    assert "SIN" in outline["title"].replace(":", " ").split()
    assert not scan_title(outline["title"])


def test_fallback_outline_ordinary_keyword_still_gets_best_prefix():
    topic = {"keyword": "renters insurance", "market": "USA"}
    outline = _build_fallback_outline(topic)
    assert outline["title"].startswith("Best Renters Insurance:")
