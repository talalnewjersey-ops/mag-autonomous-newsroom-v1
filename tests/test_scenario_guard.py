"""Illustrative Scenarios anti-fabrication guard (2026-07-10, lever "a" of the
48624 EEAT diagnosis). Sprint 8 (2026-07-05) removed the old free-form case-
study section because it fabricated named personas and unsourced figures --
that decision is NOT reversed here. This module lets agent_04 reintroduce a
STRICT, different format ("Illustrative Scenarios", validated live on article
48384) with the Sprint 8 constraint enforced IN CODE, not just prompt wording.

THE LOAD-BEARING TEST in this file is test_the_exact_reported_violation_shape_
is_rejected below: it MUST fail (i.e. the guard must reject) a scenario shaped
exactly like the incident this whole guard exists to prevent -- an invented
first name plus a precise unsourced dollar amount ("Sarah saved $3,240").
If that test ever passes with is_clean=True, the Sprint 8 decision has been
silently weakened and this test is designed to catch that immediately.

Offline, no network, no API key.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents._scenario_guard import (
    COMMON_FIRST_NAMES,
    SCENARIO_DISCLAIMER,
    SCENARIO_HEADING,
    build_scenario_block,
    find_invented_names,
    find_uncovered_numeric_claims,
    strip_leading_duplicate_heading,
    validate_scenario_block,
)

V = "us_auto"
# Real us_auto STABLE fact (agents/_vertical_facts.py): Texas minimum liability.
TX_URL = "https://www.tdi.texas.gov/pubs/consumer/cb020.html"


# ---------------- find_invented_names ----------------

def test_common_first_name_is_detected():
    assert find_invented_names("Sarah moved to Texas last year.") == ["Sarah"]


def test_diverse_first_names_are_detected():
    # the real incident this guards against used "Priya"/"Carlos" (AUDIT-LOG.md,
    # article 47510's anonymization work) -- an anglo-only list would miss it.
    assert "Priya" in find_invented_names("Priya applied for a student visa.")
    assert "Carlos" in find_invented_names("Carlos opened a bank account.")


def test_role_based_description_has_no_names():
    text = ("The student arrived on an F-1 visa and applied for a state driver's "
            "license after their SEVIS record was activated.")
    assert find_invented_names(text) == []


def test_institution_and_place_names_are_not_false_positives():
    # capitalized but NOT first names -- Texas, GEICO, Ontario are legitimate.
    text = "GEICO accepted an applicant from Texas with an ITIN in Ontario-adjacent cases."
    assert find_invented_names(text) == []


# ---------------- find_uncovered_numeric_claims ----------------

def test_uncovered_dollar_amount_is_flagged():
    claims = find_uncovered_numeric_claims("The applicant saved $3,240 on their premium.", V)
    assert len(claims) == 1


def test_number_matching_a_real_engraved_fact_is_not_flagged():
    text = f"Texas requires $30,000 of bodily-injury coverage per person ([TDI]({TX_URL}))."
    assert find_uncovered_numeric_claims(text, V) == []


def test_qualitative_description_has_no_numeric_claims():
    text = "The applicant received a lower quote after providing a translated driving record."
    assert find_uncovered_numeric_claims(text, V) == []


# ---------------- validate_scenario_block ----------------

def test_clean_role_based_qualitative_scenario_passes():
    text = (
        "### Illustrative Scenario 1: International Student, Engineering Program (Texas)\n\n"
        "The student arrived on an F-1 visa with no US driving history. After providing a "
        f"translated foreign license and proof of enrollment, they were quoted a rate the "
        f"insurer described as typical for first-time applicants ([TDI]({TX_URL}))."
    )
    is_clean, reasons = validate_scenario_block(text, V)
    assert is_clean is True
    assert reasons == []


def test_real_48384_shaped_scenario_passes():
    # mirrors the actual validated text fetched from article 48384 (WP REST API):
    # role-based personas, no names, no invented figures, real regulator reference.
    text = (
        "### Illustrative Scenario 1: International Student, Computer Science Program (Ontario)\n\n"
        "A newly arrived international student used their study permit and home-country passport "
        "as primary identification to open a savings account within their first week -- no "
        "Canadian credit history was required. The entirely digital onboarding process took under "
        "25 minutes, with no branch visit needed.\n\n"
        "### Illustrative Scenario 2: Graduate Student, MBA Program (Quebec)\n\n"
        "A graduate student initially opened an account through a traditional bank's student "
        "banking program, then compared fees using a tool on the Financial Consumer Agency of "
        "Canada's website before consolidating savings into a separate account."
    )
    is_clean, reasons = validate_scenario_block(text, "canada_newcomer")
    assert is_clean is True
    assert reasons == []


def test_scenario_with_only_a_name_violation_fails():
    text = "### Illustrative Scenario 1: Newcomer\n\nCarlos applied for a state driver's license."
    is_clean, reasons = validate_scenario_block(text, V)
    assert is_clean is False
    assert any("name" in r for r in reasons)


def test_scenario_with_only_an_unsourced_number_violation_fails():
    text = "### Illustrative Scenario 1: The Applicant\n\nThe applicant's premium dropped to $840 a year."
    is_clean, reasons = validate_scenario_block(text, V)
    assert is_clean is False
    assert any("numeric" in r for r in reasons)


# ---------------- THE LOAD-BEARING TEST: Sprint 8 decision locked in code ----------------

def test_the_exact_reported_violation_shape_is_rejected():
    # The exact pattern the user named when maintaining the Sprint 8 decision:
    # an invented first name AND a precise, unsourced dollar figure. This test
    # is the code-level guarantee that this specific failure mode can never
    # silently ship again -- if this assertion ever breaks, the anti-
    # fabrication guard has regressed.
    violation = "### Illustrative Scenario 1: Newcomer\n\nSarah saved $3,240 on her first policy."
    is_clean, reasons = validate_scenario_block(violation, V)
    assert is_clean is False, "Sprint 8 anti-fabrication guard REGRESSED: this must be rejected"
    assert len(reasons) == 2  # BOTH violations caught, not just one
    joined = " ".join(reasons)
    assert "Sarah" in joined
    assert "numeric" in joined


def test_build_scenario_block_never_publishes_the_violating_shape():
    violation = "### Illustrative Scenario 1: Newcomer\n\nSarah saved $3,240 on her first policy."
    block, is_clean, reasons = build_scenario_block(violation, V)
    assert block == ""
    assert is_clean is False
    assert "Sarah" not in block  # trivially true for "" but documents the invariant explicitly


# ---------------- build_scenario_block: full assembly ----------------

def test_build_scenario_block_assembles_heading_and_disclaimer_on_success():
    text = "### Illustrative Scenario 1: The Applicant\n\nThe applicant provided a translated driving record."
    block, is_clean, reasons = build_scenario_block(text, V)
    assert is_clean is True
    assert block.startswith(SCENARIO_HEADING)
    assert SCENARIO_DISCLAIMER in block
    assert text in block


def test_build_scenario_block_empty_input_produces_empty_output():
    block, is_clean, reasons = build_scenario_block("", V)
    assert block == ""
    assert is_clean is True  # nothing to validate, nothing published -- not a failure


# ---------------- strip_leading_duplicate_heading (2026-07-11 real-run fix) ----------------
# Real bug found on draft 48632 (production_v2.yml run 29134020416): the LLM's
# raw output echoed its OWN "## Illustrative Scenarios" H2 -- on top of the
# SAME heading build_scenario_block adds deterministically -- producing a
# visible duplicate H2 in the published article:
#   ## Illustrative Scenarios
#
#   *The following are illustrative scenarios, not real testimonials...*
#
#   ## Illustrative Scenarios          <-- the bug
#
#   ### Illustrative Scenario: F-1 International Student, ...

def test_strip_leading_duplicate_heading_removes_it():
    raw = "## Illustrative Scenarios\n\n### Illustrative Scenario: The Applicant\n\nBody text here."
    stripped = strip_leading_duplicate_heading(raw)
    assert stripped == "### Illustrative Scenario: The Applicant\n\nBody text here."
    assert stripped.count("## Illustrative Scenarios") == 0


def test_strip_leading_duplicate_heading_is_a_noop_when_absent():
    raw = "### Illustrative Scenario: The Applicant\n\nBody text here."
    assert strip_leading_duplicate_heading(raw) == raw


def test_strip_leading_duplicate_heading_only_touches_the_leading_line():
    # a legitimate "### " (H3, not H2) at the very start must survive untouched.
    raw = "### Illustrative Scenario: The Applicant\n\nSee ## for details (not a real heading)."
    assert strip_leading_duplicate_heading(raw) == raw


def test_build_scenario_block_deduplicates_the_real_48632_shaped_output():
    # exact shape observed in production: LLM echoes the H2, THEN the real
    # H3 + body. build_scenario_block must publish it ONCE, not twice.
    raw_llm_output = (
        "## Illustrative Scenarios\n\n"
        "### Illustrative Scenario: F-1 International Student, Graduate Program (New York)\n\n"
        "A graduate student arrives on an F-1 visa and seeks auto insurance without a US "
        "driving record, qualifying only for higher-risk pricing tiers initially."
    )
    block, is_clean, reasons = build_scenario_block(raw_llm_output, "us_auto")
    assert is_clean is True
    assert block.count("## Illustrative Scenarios") == 1, (
        f"duplicate H2 heading regressed -- real bug from draft 48632: {block!r}"
    )
    assert "### Illustrative Scenario: F-1 International Student" in block
    assert SCENARIO_DISCLAIMER in block


def test_disclaimer_explicitly_denies_being_a_real_testimonial():
    # constraint (4) from the user: never presented as a real testimonial.
    assert "not real testimonials" in SCENARIO_DISCLAIMER
    assert "illustrative" in SCENARIO_DISCLAIMER.lower()


def test_heading_is_explicitly_labeled_illustrative():
    # constraint (1) from the user: explicitly titled/introduced as illustrative.
    assert "Illustrative" in SCENARIO_HEADING


# ---------------- source guards on agent_04's wiring ----------------

AGENT_04_SRC = open(os.path.join(ROOT, "agents/agent_04_article_writer.py"), encoding="utf-8").read()


def test_agent_04_calls_build_scenario_block_not_a_raw_assignment():
    assert "case_studies, _scenario_ok, _scenario_issues = build_scenario_block(" in AGENT_04_SRC


def test_agent_04_prompt_explicitly_forbids_names_and_unsourced_numbers():
    # source-guard: the prompt instruction text itself must still carry the
    # constraints (defense layer 1), even though the code check (layer 2,
    # tested above) is what's actually enforced. Substrings kept within a
    # single f-string line (not straddling a line break) so they survive
    # incidental prompt rewrapping.
    assert "no first names/invented" in AGENT_04_SRC
    assert "identities (role/status only)" in AGENT_04_SRC
    assert "no $/%/number unless already" in AGENT_04_SRC
    assert "established elsewhere in this article" in AGENT_04_SRC
    assert "never a real testimonial" in AGENT_04_SRC


def test_agent_04_logs_a_warning_on_rejection_never_silently_drops():
    assert "Illustrative Scenarios REJECTED (anti-fabrication guard)" in AGENT_04_SRC


def test_scenario_call_is_short_deliberately_capped():
    # 2026-07-10 real-run finding on draft 48624: a verbose 2-scenario call
    # (max_tokens=700) pushed an OPPORTUNITY-tier article (already 4304w,
    # +7.6% over its own 4000w target) past the +-10% word-count tolerance --
    # costing 15 SEO points (word_count_ok) + 40 content_check points, a NET
    # SCORE REGRESSION despite the EEAT gain. First fix: ONE scenario,
    # 40-70w, max_tokens=200 -- STILL not enough (see next test's docstring):
    # a real-run on draft 48632 showed the fixed costs (H2 3w + disclaimer
    # 14w + H3 ~10w = ~27w non-negotiable) plus even an in-target 63w body
    # totalled 93w, pushing a 4344w base article (normal generation
    # variance) 34w over 4400. Tightened further: body target 25-40w,
    # max_tokens=150. NOT fixed by widening agent_12's shared +-10%
    # tolerance (that governs every article, not just ones with a scenario).
    m = re.search(r"Write ONE short sub-section for:.*?max_tokens=(\d+)\)", AGENT_04_SRC, re.DOTALL)
    assert m, "the Illustrative Scenarios _call_claude invocation was not found"
    assert int(m.group(1)) <= 200, (
        f"scenario max_tokens={m.group(1)} is too generous -- real-run tests showed 700 and even "
        f"200-with-a-40-70w-target regress the score by pushing an OPPORTUNITY-tier article over "
        f"its own +-10% word-count tolerance (SEO word_count_ok + content_check both fail)"
    )
    assert "ONE short sub-section" in AGENT_04_SRC
    assert "25-40 words" in AGENT_04_SRC


def test_scenario_prompt_asks_the_llm_not_to_duplicate_the_heading():
    # layer-1 defense (prompt wording) alongside layer-2 (code-level dedup,
    # tested in test_strip_leading_duplicate_heading_* above) -- the prompt
    # no longer even mentions the literal "## Illustrative Scenarios" text
    # (the old wording "Write '## Illustrative Scenarios' for: ..." directly
    # invited the LLM to echo it), and explicitly says not to add another
    # heading before the "### " one.
    assert "Write '## Illustrative Scenarios' for:" not in AGENT_04_SRC
    assert "no other heading before it" in AGENT_04_SRC


def test_min_case_studies_still_zero_sprint_8_floor_unchanged():
    # the NEW format is opt-in/best-effort (validated or dropped), never a
    # hard requirement -- the tier floors stay exactly as Sprint 8 set them.
    assert re.search(r"PILLAR_MIN_CASE_STUDIES\s*=\s*0", AGENT_04_SRC)
    assert re.search(r"STANDARD_MIN_CASE_STUDIES\s*=\s*0", AGENT_04_SRC)
    assert re.search(r"OPPORTUNITY_MIN_CASE_STUDIES\s*=\s*0", AGENT_04_SRC)
