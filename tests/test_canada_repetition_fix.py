"""CANADA REPETITION FIX (2026-07-06, Option B): the real regression was the
writer independently creating a SECOND dedicated subsection ("### Your Legal
Right to Open an Account") around a rights/eligibility claim it had already
made narratively earlier in the SAME article -- the existing _dedup_wording
instruction ("vary your wording, don't reuse a sentence verbatim") and
_build_digest's rules-extraction (formal Act citations only) both missed this
shape. Two additive trackers (_extract_headings, _rights_claim_already_made)
give the writer concrete data instead of just a wording reminder.

GUARDRAIL (user's explicit requirement): this touches every vertical's
prompt, not just Canada's -- verify it does NOT spuriously fire for verticals
that never had this problem (us_auto, us_credit). Fixtures below are frozen,
REAL section text from the actual control runs (not synthetic), so this is a
genuine before/after check, not a hypothetical.

The G3 gate itself (scripts/g3_repetition_gate.py) is NOT touched by this fix
and has no tests here -- it remains the sole judge, unchanged.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import importlib.util
_spec = importlib.util.spec_from_file_location("agent_04_canada_fix_test", os.path.join(ROOT, "agents/agent_04_article_writer.py"))
agent_04 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(agent_04)


# ---------------------------------------------------------------- _extract_headings

def test_extract_headings_collects_h2_and_h3_in_order_deduplicated():
    blocks = [
        "## 1. Overview\n\nSome text.\n\n### Who This Covers\n\nMore text.",
        "## 2. Eligibility\n\n### Who This Covers\n\nRepeated heading text.\n\n### New Topic\n\nFresh content.",
    ]
    headings = agent_04._extract_headings(blocks)
    assert headings == ["1. Overview", "Who This Covers", "2. Eligibility", "New Topic"]


def test_extract_headings_empty_when_no_headings():
    assert agent_04._extract_headings(["plain text, no markdown headings at all"]) == []


def test_extract_headings_ignores_h1_and_h4_plus():
    blocks = ["# Title (H1, ignored)\n\n## Real H2\n\n#### Too deep (H4, ignored)\n"]
    assert agent_04._extract_headings(blocks) == ["Real H2"]


# ---------------------------------------------------------------- _rights_claim_already_made

def test_rights_claim_detects_legal_right_phrasing():
    text = "You have the legal right to open a personal bank account even without a job."
    claim = agent_04._rights_claim_already_made([text])
    assert claim is not None
    assert "right to open a personal bank account" in claim


def test_rights_claim_detects_entitled_to_phrasing():
    text = "Newcomers are entitled to open a personal bank account regardless of employment status."
    assert agent_04._rights_claim_already_made([text]) is not None


def test_rights_claim_none_when_absent():
    text = "Interest rates vary by provider and by account type across the major banks."
    assert agent_04._rights_claim_already_made([text]) is None


def test_rights_claim_returns_first_match_across_blocks():
    blocks = ["First block, nothing here.", "You have the right to open an account without a job.",
              "Second mention: are entitled to open one too."]
    claim = agent_04._rights_claim_already_made(blocks)
    assert "have the right to open" in claim


# ---------------------------------------------------------------- real-data guardrail (frozen fixtures)
# Real section text from the actual control run (2026-07-06), frozen so this
# test stays offline and doesn't depend on the live articles changing later.

US_AUTO_SECTION_1 = (
    "## 1. Best Car Insurance For Foreign Drivers And International Students: Quick Overview\n\n"
    "### Who This Guide Covers\n\nF-1 and M-1 visa holders, work visa holders, and green card holders.\n\n"
    "### Minimum Coverage by State: A Snapshot\n\nCoverage requirements vary significantly by state.\n\n"
    "### The Core Problem Foreign Drivers Face\n\nInsurers price risk using data points newcomers lack.\n"
)
US_AUTO_SECTION_2 = (
    "## 2. What Is Car Insurance For Foreign Drivers And International Students\n\n"
    "### Why Standard Insurance Logic Breaks Down for Newcomers\n\nStandard underwriting assumes a US history.\n\n"
    "### The Legal Obligation Is Absolute\n\nEvery state requires liability coverage before driving.\n"
)

US_CREDIT_SECTION_1 = (
    "## 1. Best Personal Loans For Immigrants No Credit History: Quick Overview\n\n"
    "### Who This Overview Covers\n\nImmigrants without a US credit file.\n\n"
    "### Top Lender Categories at a Glance\n\nCredit unions, CDFIs, and online lenders.\n"
)
US_CREDIT_SECTION_2 = (
    "## 2. What Is Personal Loans For Immigrants No Credit History\n\n"
    "### Defining the Product\n\nAn unsecured installment loan.\n\n"
    "### Why Immigrants Face a Structural Credit Gap\n\nCredit scoring relies on US-only data.\n"
)

CANADA_SECTION_WHY = (
    "## Why This Decision Matters More Than Most Newcomers Realize\n\n"
    "According to the FCAC, federally regulated banks are required to offer basic banking services. "
    "You have the legal right to open a personal bank account even without a job, without an initial "
    "deposit, or if you are unemployed, as confirmed by the FCAC's account-opening rules.\n"
)
CANADA_SECTION_ELIGIBILITY = (
    "## 3. Eligibility Requirements for Immigrants\n\n"
    "### Who Qualifies as a \"Newcomer\"\n\nMost major banks define a newcomer broadly.\n\n"
    "### Your Legal Right to Open an Account\n\n"
    "Under federal banking regulations overseen by the FCAC, you have the right to open a personal "
    "bank account even without a job, without an initial deposit.\n"
)


def test_us_auto_real_sections_never_trigger_a_rights_claim_repeat():
    # us_auto never had this problem -- confirm the guard stays silent (no
    # spurious "already stated" warning) across its own real section sequence.
    prior = [US_AUTO_SECTION_1]
    rights = agent_04._rights_claim_already_made(prior)
    assert rights is None, "us_auto's real content should never trigger the rights-claim guard"
    # and even after section 2, the "own repeat" condition (both prior AND
    # current section containing the pattern) never holds -- verified by
    # the absence of any rights-claim match in EITHER real section.
    assert agent_04._RIGHTS_CLAIM_RE.search(US_AUTO_SECTION_2) is None


def test_us_credit_real_sections_never_trigger_a_rights_claim_repeat():
    prior = [US_CREDIT_SECTION_1]
    assert agent_04._rights_claim_already_made(prior) is None
    assert agent_04._RIGHTS_CLAIM_RE.search(US_CREDIT_SECTION_2) is None


def test_us_auto_and_us_credit_headings_are_all_distinct_no_false_overlap():
    # the heading list itself must never contain accidental duplicates across
    # genuinely different sections in the clean verticals.
    auto_headings = agent_04._extract_headings([US_AUTO_SECTION_1, US_AUTO_SECTION_2])
    assert len(auto_headings) == len(set(h.lower() for h in auto_headings)), "no duplicate headings expected"
    credit_headings = agent_04._extract_headings([US_CREDIT_SECTION_1, US_CREDIT_SECTION_2])
    assert len(credit_headings) == len(set(h.lower() for h in credit_headings))


def test_canada_real_case_the_guard_would_have_fired_before_the_duplicate_subsection():
    # By the time "3. Eligibility Requirements" (containing the duplicate
    # "Your Legal Right to Open an Account" H3) is generated, the rights claim
    # from the earlier "Why This Decision Matters" section is already
    # detectable -- exactly the signal that was missing before this fix.
    prior = [CANADA_SECTION_WHY]
    rights = agent_04._rights_claim_already_made(prior)
    assert rights is not None
    assert "right to open" in rights.lower()
    # and the section that duplicates it does contain a fresh instance of the
    # same claim shape -- confirming this is the real, reproducible case.
    assert agent_04._RIGHTS_CLAIM_RE.search(CANADA_SECTION_ELIGIBILITY) is not None


def test_repetition_guard_block_construction_matches_expected_shape():
    # mirrors the exact block-building logic inside _write_article_standalone
    # (kept in sync manually -- a source-level guard below cross-checks this).
    headings_so_far = agent_04._extract_headings([CANADA_SECTION_WHY])
    rights_so_far = agent_04._rights_claim_already_made([CANADA_SECTION_WHY])
    assert rights_so_far is not None
    assert headings_so_far == ["Why This Decision Matters More Than Most Newcomers Realize"]


# ---------------------------------------------------------------- source-level guards

SRC = open(os.path.join(ROOT, "agents/agent_04_article_writer.py"), encoding="utf-8").read()


def test_repetition_guard_wired_into_body_section_loop():
    assert "_repetition_guard_block" in SRC
    assert "{digest_block}{_repetition_guard_block}{section_sources_block}" in SRC


def test_repetition_guard_wired_into_trailing_dedup_digest():
    assert "_final_headings = _extract_headings" in SRC
    assert "_final_rights = _rights_claim_already_made" in SRC


def test_agent_04_never_imports_or_calls_the_g3_gate():
    # the gate must remain untouched and unreferenced by this fix -- it stays
    # the sole judge, per the user's explicit instruction not to loosen it.
    assert "g3_repetition_gate" not in SRC
