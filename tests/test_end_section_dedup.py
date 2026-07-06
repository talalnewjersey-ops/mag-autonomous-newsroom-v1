"""DUPLICATED END SECTIONS FIX (2026-07-06): user reported, on a real
published-bound draft, THREE "About the Author" blocks and TWO "Disclaimer"
blocks in the same article footer, plus two contradictory bio variants (one
falsely claiming MoneyAbroadGuide.com is "a licensed financial information
platform" -- contradicts the article's own disclaimer -- and using
"EEAT-compliant" jargon meaningless to a reader).

Root cause (confirmed by reading the code, not guessed): SYSTEM_PROMPT is
shared, verbatim, by every stateless per-call generation (intro, each H2
section, comparison, expert_section, faq, the word-count top-up) -- none of
which can see what any OTHER call already produced. The old prompt told
every one of those calls that a "compliance disclaimer" and "author box"
must exist "ONCE" in the article; since a stateless call has no way to
verify that, more than one independently "helpfully" added its own copy, on
top of the explicit, deliberate one requested by closing().

Fix, in two parts:
  1. SYSTEM_PROMPT no longer mentions disclaimer/author-box at all, and no
     longer claims the platform is "licensed" (was: "a licensed financial
     information platform" -> now: "an independent financial information
     platform").
  2. closing() no longer asks the LLM for an "About the Author" section at
     all -- the bio is now FIXED, human-approved text (_AUTHOR_BIO_MD),
     appended exactly once, deterministically, after this module's own
     _dedupe_reserved_end_sections() has stripped any spontaneous
     About-the-Author/Disclaimer duplicates from the LLM-generated body.
     This is the deterministic backstop -- consistent with this project's
     established anti-hallucination philosophy (rule-based gates, not
     blind trust in a prompt instruction) -- NOT just a prompt tweak.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import importlib.util
_spec = importlib.util.spec_from_file_location("agent_04_dedup_test", os.path.join(ROOT, "agents/agent_04_article_writer.py"))
agent_04 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(agent_04)

SRC = open(os.path.join(ROOT, "agents/agent_04_article_writer.py"), encoding="utf-8").read()


# ---------------------------------------------------------------- the reported real-world case

REAL_SHAPED_DRAFT = """## Expert Recommendation

Foreign drivers should consult a licensed insurance agent familiar with newcomer profiles.

---

## Compliance Disclaimer

The information provided is for general informational purposes only and does not constitute advice.

---

## About the Author

**Talal Eddaouahiri** is the founder of MoneyAbroadGuide.com, a licensed financial information
platform focused on helping newcomers navigate insurance in Canada and the United States.

## Conclusion

Securing coverage as a newcomer is achievable with the right preparation and documentation.

---

## Disclaimer

*MoneyAbroadGuide.com is an independent financial information platform and does not hold a
license.* Affiliate Disclosure: this article may contain affiliate links.

---

## About the Author

**Talal Eddaouahiri** is the founder of MoneyAbroadGuide.com, a licensed financial information
platform built for immigrants. He is committed to EEAT-compliant, regulation-grounded content.

---

## About Talal Eddaouahiri — Founder & Editor

A Moroccan immigrant who settled in the US in 2015, with a background in retail banking.
"""


def test_reported_case_reduces_to_exactly_one_disclaimer_and_zero_llm_author_blocks():
    # 3 "About the Author"-family headings + 2 Disclaimer-family headings in
    # the input, matching exactly what was reported.
    author_heading_re = re.compile(r"(?im)^#{1,3}\s*about\s+(?:the\s+author|talal)")
    disclaimer_heading_re = re.compile(r"(?im)^#{1,3}\s*(?:compliance\s+)?disclaimer\b")
    assert len(author_heading_re.findall(REAL_SHAPED_DRAFT)) == 3
    assert len(disclaimer_heading_re.findall(REAL_SHAPED_DRAFT)) == 2

    out = agent_04._dedupe_reserved_end_sections(REAL_SHAPED_DRAFT)

    assert len(author_heading_re.findall(out)) == 0, "every LLM-written About-the-Author block must be gone (the real bio is appended separately)"
    assert len(disclaimer_heading_re.findall(out)) == 1, "exactly one Disclaimer block must survive"


def test_the_disclaimer_kept_is_the_legitimate_last_one_not_a_spontaneous_earlier_one():
    out = agent_04._dedupe_reserved_end_sections(REAL_SHAPED_DRAFT)
    # the FIRST ("Compliance Disclaimer", spontaneous, from expert_section)
    # must be gone; the SECOND ("Disclaimer", legitimate, from closing(),
    # containing the real affiliate disclosure) must survive.
    assert "does not constitute advice" not in out, "the spontaneous, earlier disclaimer must be removed"
    assert "Affiliate Disclosure" in out, "the legitimate, later disclaimer (closing()'s) must survive"


def test_legitimate_surrounding_content_is_never_touched():
    out = agent_04._dedupe_reserved_end_sections(REAL_SHAPED_DRAFT)
    assert "Expert Recommendation" in out
    assert "consult a licensed insurance agent familiar with newcomer profiles" in out
    assert "Conclusion" in out
    assert "Securing coverage as a newcomer is achievable" in out


def test_full_pipeline_case_all_variants_gone_including_hyphenated_founder_editor_heading():
    # the exact third variant reported ("About Talal Eddaouahiri — Founder &
    # Editor") must also be caught, not just the literal "About the Author"
    # wording.
    out = agent_04._dedupe_reserved_end_sections(REAL_SHAPED_DRAFT)
    assert "Founder & Editor" not in out
    assert "Moroccan immigrant who settled in the US in 2015" not in out, (
        "even the honest-sounding LLM-invented variant must be stripped here -- "
        "the ONE bio the reader sees is the fixed, human-approved _AUTHOR_BIO_MD, "
        "appended separately, never an LLM-generated one"
    )


# ---------------------------------------------------------------- no false positives

def test_a_single_legitimate_disclaimer_is_left_untouched():
    text = "## Some Section\n\nContent.\n\n## Disclaimer\n\nThe only disclaimer, must survive untouched.\n"
    out = agent_04._dedupe_reserved_end_sections(text)
    assert out.count("## Disclaimer") == 1
    assert "must survive untouched" in out


def test_a_body_with_no_reserved_sections_is_returned_unchanged():
    text = "## Intro\n\nSome text.\n\n## Eligibility\n\nMore text.\n"
    assert agent_04._dedupe_reserved_end_sections(text) == text


def test_non_reserved_headings_containing_similar_words_are_not_matched():
    # "Disclosure Requirements" or "Author Guidelines" must NOT be mistaken
    # for the reserved Disclaimer/About-the-Author sections.
    text = "## Disclosure Requirements\n\nReal content about disclosure rules.\n\n## Author Guidelines\n\nUnrelated content.\n"
    out = agent_04._dedupe_reserved_end_sections(text)
    assert out == text


# ---------------------------------------------------------------- the fixed, human-approved bio text

def test_author_bio_constant_matches_the_exact_user_approved_text():
    expected = (
        "## About the Author\n\n"
        "**Talal Eddaouahiri** is the founder of [MoneyAbroadGuide.com](https://moneyabroadguide.com), "
        "an independent financial information platform for immigrants and newcomers in the United States "
        "and Canada. Originally from Morocco, he settled in the U.S. in 2015 and built his own credit "
        "history and banking relationships from scratch in both countries. His background is in retail "
        "banking and customer relations, and he draws on that firsthand experience to write independent, "
        "source-based guides — citing regulators including the FCAC, FINTRAC, OSFI, CRA, IRS, and CDIC — "
        "to help newcomers navigate financial systems with confidence."
    )
    assert agent_04._AUTHOR_BIO_MD == expected


def test_author_bio_never_contains_licensed_or_eeat_jargon():
    bio = agent_04._AUTHOR_BIO_MD
    assert "licensed" not in bio.lower()
    assert "eeat" not in bio.lower()


def test_author_bio_contains_all_six_regulators_in_order():
    bio = agent_04._AUTHOR_BIO_MD
    regulators = ["FCAC", "FINTRAC", "OSFI", "CRA", "IRS", "CDIC"]
    positions = [bio.index(r) for r in regulators]
    assert positions == sorted(positions), "regulators must appear in the exact user-specified order"


# ---------------------------------------------------------------- source guards: no more LLM-generated bio, no self-claimed "licensed"

def test_closing_prompt_no_longer_asks_for_an_about_the_author_section():
    closing_call_match = re.search(
        r"closing = await _call_claude\(api_key,(.*?)SYSTEM_PROMPT, max_tokens=900\)", SRC, re.DOTALL)
    assert closing_call_match is not None, "closing() call must still exist in its expected shape"
    assert "Write 2 sections" in closing_call_match.group(1)
    assert "About the Author" not in closing_call_match.group(1)


def test_system_prompt_no_longer_self_claims_licensed():
    # scoped to the SYSTEM_PROMPT string itself -- NOT the surrounding code
    # comments, which deliberately quote the old, now-fixed phrase to explain
    # what changed and why (e.g. this very docstring).
    system_prompt_match = re.search(r'SYSTEM_PROMPT = """(.*?)"""', SRC, re.DOTALL)
    assert system_prompt_match is not None
    prompt_body = system_prompt_match.group(1)
    assert "a licensed financial information platform" not in prompt_body
    assert "an independent financial information platform" in prompt_body


def test_system_prompt_no_longer_instructs_every_call_about_disclaimer_or_author_box():
    system_prompt_match = re.search(r'SYSTEM_PROMPT = """(.*?)"""', SRC, re.DOTALL)
    assert system_prompt_match is not None
    prompt_body = system_prompt_match.group(1)
    assert "author box" not in prompt_body.lower()
    assert "compliance disclaimer" not in prompt_body.lower()


def test_dedupe_and_bio_wired_into_the_body_assembly():
    assert "_dedupe_reserved_end_sections(body)" in SRC
    assert "_AUTHOR_BIO_MD" in SRC
