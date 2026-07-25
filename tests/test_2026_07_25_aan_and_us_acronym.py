"""2026-07-25: two real false positives found on the first real cron run and
regeneration after CASE 5 shipped -- both blocked otherwise-clean content.

Offline: no network, no API key.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents._placeholder_scan import scan_body, smart_title_case  # noqa: E402


def _a_an_findings(text):
    return [f for f in scan_body(text) if f["type"] == "a_an_disagreement"]


def test_usable_and_useful_are_not_flagged():
    # post 48982 regeneration: "a usable U.S. credit score"
    assert not _a_an_findings("How long will it take to build a usable U.S. credit score?")
    # post 48982 regeneration: "a useful bridge"
    assert not _a_an_findings("Treat Nova Credit as a useful bridge where available.")


def test_hyphenated_compound_headed_by_a_known_exception_is_not_flagged():
    # post 48957, first real scheduled cron run after reactivation:
    # "a university-issued ID" -- "university" alone was already excepted,
    # but the hyphenated compound wasn't matched before this fix.
    text = "institutions that accept a foreign passport, a university-issued ID."
    assert not _a_an_findings(text)


def test_usd_letter_name_abbreviation_is_not_flagged():
    assert not _a_an_findings("Wise gives you a USD account number and routing number.")


def test_genuine_a_an_scar_is_still_caught_after_these_fixes():
    # must not have over-corrected into blanket-allowing every u-word
    assert _a_an_findings("a newcomer facing a emergency might use a payday loan")


def test_smart_title_case_uppercases_bare_us():
    # post 48957: "How To Open A Us Bank Account Without An SSN"
    out = smart_title_case("how to open a us bank account without an ssn")
    assert "US Bank" in out
    assert "Us Bank" not in out


def test_smart_title_case_us_acronym_does_not_break_usa():
    # "us" and "usa" are both in the acronym set -- confirm the longer match
    # (usa) still wins where it applies, not doubly-mangled.
    out = smart_title_case("credit building tips for usa immigrants")
    assert "USA" in out
