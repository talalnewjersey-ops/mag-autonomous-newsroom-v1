"""GATE D connector-scar repair (2026-08-07).

CONTEXT: adjacent_connector_pair is a real, well-tested detector (tests/
test_placeholder_gate.py) catching a real writer defect -- scripts/
soften_claims.py strips an unsourced number/amount and, in its own
DOCUMENTED CASE 4/5a tradeoff (soften_claims.py lines ~455-468), sometimes
deliberately KEEPS the surrounding clause rather than deleting good content,
accepting a "two connector words now sit next to each other" scar (e.g. "at
of the prior year's earnings"). GATE D (scripts/placeholder_gate.py) then
correctly rejects the article -- but has NO retry (its own docstring: "a
placeholder-gate failure goes straight to mark_qa_failed.py ... not back
through agent_04 regeneration", a deliberate choice). Two real drafts this
week (49200, 49240) died this exact way; live `gh run list` on
mag-autonomous-newsroom-v1 shows the last 15 scheduled runs all "failure".

This module adds a narrow, ADDITIVE repair step that runs strictly AFTER a
GATE D failure and BEFORE mark_qa_failed.py: if the gate report's ONLY
findings anywhere are body-level adjacent_connector_pair (nothing else --
no title/alt-text finding, no other body finding type), attempt ONE small,
targeted LLM call per finding to naturally repair just the flagged sentence
(never a full agent_04 regeneration -- respects placeholder_gate.py's own
documented reasoning above), then re-run GATE D once. Any other finding
mix is untouched and falls straight through to the pre-existing
mark_qa_failed.py path.

Offline, no network, no API key -- same convention as
tests/test_placeholder_gate.py and tests/test_agent12_publication_gate_95.py
(the LLM caller and the WordPress content-sync caller are both injected as
plain functions, so every test below supplies a fake).
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.repair_connector_scars import (  # noqa: E402
    is_repairable,
    extract_sentence,
    build_repair_prompt,
    repair_draft,
)


# ============================================================
# Real verbatim scars from this week's failed runs (49200, 49240) --
# see tests/test_placeholder_gate.py's own REAL_* fixture convention.
# ============================================================

REAL_49240_SENTENCE = (
    "Recent Canadian citizens — typically within of status confirmation — may see "
    "sponsorship requirements reduced."
)

REAL_49200_SENTENCE_1 = (
    "Opening an account before a first paycheque triggers RRSP contribution room at "
    "of the prior year's earnings."
)

REAL_49200_SENTENCE_2 = (
    "A newcomer international student earning in their first year of in RRSP room "
    "for the following year should plan contributions early."
)


def _make_gate_report(body_findings=None, title_findings=None, alt_text_findings=None):
    return {
        "gate": "placeholder_gate",
        "body_findings": body_findings or [],
        "title_findings": title_findings or [],
        "alt_text_findings": alt_text_findings or [],
        "finding_count": len(body_findings or []) + len(title_findings or []) + len(alt_text_findings or []),
        "status": "FAIL" if (body_findings or title_findings or alt_text_findings) else "PASS",
    }


# ============================================================
# is_repairable: eligibility gate -- ONLY body-level
# adjacent_connector_pair findings, nothing else.
# ============================================================

def test_repairable_when_only_connector_pair_findings():
    report = _make_gate_report(body_findings=[
        {"type": "adjacent_connector_pair", "match": "at of", "context": REAL_49200_SENTENCE_1, "position": 10},
    ])
    assert is_repairable(report) is True


def test_repairable_true_for_multiple_connector_pair_findings_same_article():
    report = _make_gate_report(body_findings=[
        {"type": "adjacent_connector_pair", "match": "at of", "context": REAL_49200_SENTENCE_1, "position": 10},
        {"type": "adjacent_connector_pair", "match": "of in", "context": REAL_49200_SENTENCE_2, "position": 200},
    ])
    assert is_repairable(report) is True


def test_not_repairable_when_a_different_body_finding_type_is_present():
    # A leaked alt-text / broken-title-case / fused-link scar is a DIFFERENT
    # bug class this script does not attempt to fix.
    report = _make_gate_report(body_findings=[
        {"type": "adjacent_connector_pair", "match": "at of", "context": REAL_49200_SENTENCE_1, "position": 10},
        {"type": "fused_link_sentence", "match": "x.uscis.gov", "context": "...", "position": 300},
    ])
    assert is_repairable(report) is False


def test_not_repairable_when_title_finding_present():
    report = _make_gate_report(
        body_findings=[{"type": "adjacent_connector_pair", "match": "at of", "context": "x", "position": 1}],
        title_findings=[{"type": "broken_title_case_acronym", "match": "Usa", "context": "x", "position": 0}],
    )
    assert is_repairable(report) is False


def test_not_repairable_when_alt_text_finding_present():
    report = _make_gate_report(
        body_findings=[{"type": "adjacent_connector_pair", "match": "at of", "context": "x", "position": 1}],
        alt_text_findings=[{"type": "leaked_internal_label_alt", "match": "Comparison guide: X", "context": "x"}],
    )
    assert is_repairable(report) is False


def test_not_repairable_when_no_findings_at_all():
    report = _make_gate_report()
    assert is_repairable(report) is False


# ============================================================
# extract_sentence: locate the sentence containing a finding's position,
# pure text-slicing, no network.
# ============================================================

def test_extract_sentence_finds_containing_sentence():
    text = "First sentence is fine. " + REAL_49200_SENTENCE_1 + " Third sentence is also fine."
    position = text.index("at of")
    sentence, start, end = extract_sentence(text, position)
    assert sentence.strip() == REAL_49200_SENTENCE_1
    assert text[start:end].strip() == REAL_49200_SENTENCE_1


def test_extract_sentence_handles_first_sentence_in_document():
    text = REAL_49240_SENTENCE + " Second sentence follows."
    position = text.index("within of")
    sentence, start, end = extract_sentence(text, position)
    assert sentence.strip() == REAL_49240_SENTENCE


def test_extract_sentence_handles_last_sentence_in_document():
    text = "First sentence is fine. " + REAL_49200_SENTENCE_2
    position = text.index("of in")
    sentence, start, end = extract_sentence(text, position)
    assert sentence.strip() == REAL_49200_SENTENCE_2


# ============================================================
# build_repair_prompt: must forbid reintroducing a fabricated number
# (same anti-fabrication constraint agent_04 itself is bound by).
# ============================================================

def test_repair_prompt_forbids_reintroducing_a_number():
    prompt = build_repair_prompt(REAL_49200_SENTENCE_1)
    assert REAL_49200_SENTENCE_1 in prompt
    assert "number" in prompt.lower() or "figure" in prompt.lower()
    assert "without" in prompt.lower() or "never" in prompt.lower() or "do not" in prompt.lower()


# ============================================================
# repair_draft: end-to-end pure-text repair (LLM call injected/faked).
# ============================================================

def test_repair_draft_replaces_flagged_sentence_with_llm_output():
    draft = "Intro line.\n\n" + REAL_49200_SENTENCE_1 + "\n\nClosing line."
    report = _make_gate_report(body_findings=[{
        "type": "adjacent_connector_pair", "match": "at of",
        "context": REAL_49200_SENTENCE_1, "position": draft.index("at of"),
    }])

    def fake_llm(prompt):
        return "Opening an account before a first paycheque triggers RRSP contribution room based on prior earnings."

    repaired_text, ok, fixes = repair_draft(draft, report, call_llm=fake_llm)
    assert ok is True
    assert "at of" not in repaired_text
    assert "Intro line." in repaired_text and "Closing line." in repaired_text
    assert "based on prior earnings" in repaired_text
    assert fixes == [{
        "old_sentence": REAL_49200_SENTENCE_1,
        "new_sentence": "Opening an account before a first paycheque triggers RRSP contribution room based on prior earnings.",
    }]


def test_repair_draft_rejects_repair_that_still_has_a_grammar_scar():
    # If the LLM's own "fix" still contains a detectable scar, repair_draft
    # must NOT apply it silently -- fail closed, exactly like every other
    # gate in this pipeline.
    draft = "Intro line.\n\n" + REAL_49200_SENTENCE_1 + "\n\nClosing line."
    report = _make_gate_report(body_findings=[{
        "type": "adjacent_connector_pair", "match": "at of",
        "context": REAL_49200_SENTENCE_1, "position": draft.index("at of"),
    }])

    def bad_llm(prompt):
        return "Opening an account before a first paycheque triggers RRSP contribution room at of last year."

    repaired_text, ok, fixes = repair_draft(draft, report, call_llm=bad_llm)
    assert ok is False
    assert repaired_text == draft  # untouched on failure
    assert fixes == []


def test_repair_draft_rejects_repair_that_reintroduces_a_fabricated_number():
    # The whole point of the original strip was "no unsourced figure" --
    # a repair that puts a bare number back defeats Couche 2/3 entirely.
    draft = "Intro line.\n\n" + REAL_49200_SENTENCE_1 + "\n\nClosing line."
    report = _make_gate_report(body_findings=[{
        "type": "adjacent_connector_pair", "match": "at of",
        "context": REAL_49200_SENTENCE_1, "position": draft.index("at of"),
    }])

    def fabricating_llm(prompt):
        return "Opening an account before a first paycheque triggers RRSP contribution room at 18% of prior earnings."

    repaired_text, ok, fixes = repair_draft(draft, report, call_llm=fabricating_llm)
    assert ok is False
    assert repaired_text == draft
    assert fixes == []


def test_repair_draft_handles_multiple_findings_in_one_article():
    draft = REAL_49200_SENTENCE_1 + "\n\n" + REAL_49200_SENTENCE_2
    report = _make_gate_report(body_findings=[
        {"type": "adjacent_connector_pair", "match": "at of",
         "context": REAL_49200_SENTENCE_1, "position": draft.index("at of")},
        {"type": "adjacent_connector_pair", "match": "of in",
         "context": REAL_49200_SENTENCE_2, "position": draft.index("of in")},
    ])
    fixes = {
        REAL_49200_SENTENCE_1: "Opening an account before a first paycheque triggers RRSP contribution room based on prior earnings.",
        REAL_49200_SENTENCE_2: "A newcomer international student earning income in their first year builds RRSP room for the following year.",
    }

    def fake_llm(prompt):
        for original, fixed in fixes.items():
            if original in prompt:
                return fixed
        raise AssertionError("prompt did not contain either known sentence")

    repaired_text, ok, applied = repair_draft(draft, report, call_llm=fake_llm)
    assert ok is True
    assert "at of" not in repaired_text and "of in RRSP" not in repaired_text
    assert "based on prior earnings" in repaired_text
    assert "builds RRSP room" in repaired_text
    # Regression lock for a real offset bug caught before shipping: applied
    # fixes must be reported in DOCUMENT order (first sentence first), and
    # each old_sentence must be the ORIGINAL (pre-repair) text -- repair_draft
    # applies highest-position-first internally so earlier splices never
    # invalidate not-yet-processed lower positions, but a caller reconstructing
    # "old vs new" from raw finding positions AFTER the fact (against the
    # fully-patched text) would get the wrong slice for every finding except
    # the last one applied, since a lower-position splice shifts every
    # position after it. applied_fixes exists precisely so no caller ever
    # needs to do that reconstruction.
    assert [f["old_sentence"] for f in applied] == [REAL_49200_SENTENCE_1, REAL_49200_SENTENCE_2]
    assert applied[0]["new_sentence"] == fixes[REAL_49200_SENTENCE_1]
    assert applied[1]["new_sentence"] == fixes[REAL_49200_SENTENCE_2]


def test_repair_draft_returns_false_when_not_repairable():
    draft = "Some article text."
    report = _make_gate_report(body_findings=[
        {"type": "fused_link_sentence", "match": "x", "context": "x", "position": 0},
    ])
    repaired_text, ok, fixes = repair_draft(draft, report, call_llm=lambda p: "irrelevant")
    assert ok is False
    assert repaired_text == draft
    assert fixes == []


# ============================================================
# production_batch_loop.sh wiring -- source guard, proves the repair
# step exists between GATE D's first failure and mark_qa_failed.py, and
# that it only ever gets ONE attempt (no loop).
# ============================================================

def test_batch_loop_wires_connector_repair_between_gate_d_and_mark_qa_failed():
    src = (REPO_ROOT / "scripts" / "production_batch_loop.sh").read_text(encoding="utf-8")
    gate_d_pos = src.index("Phase 11.5: Anti-Placeholder Gate [GATE D]")
    repair_pos = src.index("scripts/repair_connector_scars.py")
    qa_pos = src.index("Phase 12-13: QA + Chief Editor")
    assert gate_d_pos < repair_pos < qa_pos
