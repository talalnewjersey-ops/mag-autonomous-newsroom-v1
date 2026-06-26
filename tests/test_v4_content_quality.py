#!/usr/bin/env python3
"""
Offline tests for the M8 content-quality gate (services/content_quality.py).

All deterministic: no network, no LLM, no fabricated metrics. Verifies the
scorer, per-signal detail, weak-signal detection, the regenerate_sections
mapping, and the non-blocking quality hook in the Writer V4 loop.
"""
from __future__ import annotations

import pytest

from services.content_quality import (
    assess_quality,
    needs_quality_pass,
    score_length,
    score_structure,
    score_newcomer_actionability,
    score_eeat_surface,
    score_faq_coverage,
    score_readability,
    MIN_QUALITY_SCORE,
    SIGNAL_PASS_FLOOR,
    WEIGHTS,
)


# A deliberately STRONG newcomer guide: long, structured, actionable, FAQ, EEAT.
def _strong_article() -> str:
    body = " ".join([
        "A newcomer to the United States must apply for an SSN early.",
        "Building a credit score and credit history takes documented steps.",
        "Open a bank account; you will need a routing number and documents.",
        "Understand tax basics with the IRS and, in Canada, the CRA.",
        "Check eligibility and requirements before you apply for each step.",
        "Review fees and cost, keep a checklist, and watch every deadline.",
    ] * 30)
    return (
        "# Newcomer Money Guide\n\n" + body + "\n\n"
        "## Getting your SSN\n\nAccording to official .gov sources, as of 2025 "
        "you should apply early. " + body + "\n\n"
        "## Building credit\n\nVerify your documentation and consult a source. "
        + body + "\n\n"
        "## Banking basics\n\n" + body + "\n\n"
        "## Conclusion\n\nUpdated guidance: keep your checklist current.\n\n"
        "## FAQ\n\n"
        "### How do I get an SSN as a newcomer?\n\nApply at the office.\n\n"
        "### What documents do I need to open a bank account?\n\nBring ID.\n\n"
        "### How long does building a credit score take?\n\nSeveral months.\n"
    )


# A deliberately WEAK article: short, no structure, no FAQ, no newcomer terms.
def _weak_article() -> str:
    return "# Title\n\nThis is a very short post with little useful content.\n"


def test_strong_article_passes():
    report = assess_quality(_strong_article())
    assert report["passed"] is True
    assert report["score"] >= MIN_QUALITY_SCORE
    assert report["regenerate_sections"] == []
    assert report["weak_signals"] == []


def test_weak_article_fails_and_flags_sections():
    report = assess_quality(_weak_article())
    assert report["passed"] is False
    assert report["score"] < MIN_QUALITY_SCORE
    assert report["weak_signals"]  # at least one signal is weak
    assert report["regenerate_sections"]  # at least one section to regenerate


def test_needs_quality_pass_predicate():
    assert needs_quality_pass(_weak_article()) is True
    assert needs_quality_pass(_strong_article()) is False


def test_report_has_all_signals():
    report = assess_quality(_strong_article())
    assert set(report["signals"].keys()) == set(WEIGHTS.keys())
    for name, info in report["signals"].items():
        assert 0.0 <= info["score"] <= 1.0
        assert "detail" in info


def test_score_is_bounded_0_100():
    for md in ("", _weak_article(), _strong_article()):
        report = assess_quality(md)
        assert 0 <= report["score"] <= 100


def test_empty_article_scores_low():
    report = assess_quality("")
    assert report["passed"] is False
    assert report["score"] < MIN_QUALITY_SCORE


def test_length_signal_monotonic():
    short, _ = score_length("word " * 10)
    long_, _ = score_length("word " * 1000)
    assert long_ >= short
    assert 0.0 <= short <= 1.0 and 0.0 <= long_ <= 1.0


def test_structure_rewards_headings_and_conclusion():
    none, d0 = score_structure("no headings here")
    many, d1 = score_structure(
        "## A\ntext\n## B\ntext\n## C\ntext\n## Conclusion\nwrap up"
    )
    assert many > none
    assert d1["has_conclusion"] is True
    assert d0["has_conclusion"] is False


def test_newcomer_actionability_counts_distinct_terms():
    low, dl = score_newcomer_actionability("hello world")
    high, dh = score_newcomer_actionability(
        "ssn credit score bank account tax eligibility apply requirements "
        "fees checklist deadline newcomer immigrant documents lease deposit"
    )
    assert high > low
    assert len(dh["matched_terms"]) > len(dl["matched_terms"])


def test_eeat_surface_detects_markers():
    low, _ = score_eeat_surface("just plain text")
    high, dh = score_eeat_surface(
        "According to official .gov sources, as of 2025, verify documentation."
    )
    assert high > low
    assert dh["matched_markers"]


def test_faq_coverage_counts_questions():
    none, d0 = score_faq_coverage("# Title\n\nbody text only")
    some, d1 = score_faq_coverage(
        "## FAQ\n\n### Is this a question?\n\nYes.\n\n### And another?\n\nYes.\n"
    )
    assert some > none
    assert d1["faq_questions"] >= 2


def test_readability_penalises_long_sentences():
    short = "Short clear sentence. Another short one. And a third short line."
    longish = (" ".join(["word"] * 60) + ". ") * 4
    s_short, _ = score_readability(short)
    s_long, _ = score_readability(longish)
    assert s_short > s_long


def test_weak_signals_use_pass_floor():
    report = assess_quality(_weak_article())
    for sig in report["weak_signals"]:
        assert report["signals"][sig]["score"] < SIGNAL_PASS_FLOOR


def test_assess_quality_is_pure():
    md = _strong_article()
    before = md
    assess_quality(md)
    assert md == before  # input not mutated


# --- Writer V4 loop integration: the quality hook must be non-blocking --------
def test_writer_loop_quality_hook_optional_and_safe():
    from agents.agent_04_writer_v4 import run_writer_v4_loop

    # A generator that should never be called when nothing is flagged.
    calls = {"n": 0}

    def _gen(section, directive):
        calls["n"] += 1
        return "regenerated"

    md = _strong_article()
    # quality_check that raises must NOT break the loop (defensive guard).
    def _boom(_markdown):
        raise ValueError("boom")

    result = run_writer_v4_loop(md, corpus=[], section_generator=_gen,
                                seed="slug", quality_check=_boom)
    assert "markdown" in result
    assert "passed" in result
    assert isinstance(result["rounds"], int)


def test_writer_loop_default_behaviour_unchanged():
    from agents.agent_04_writer_v4 import run_writer_v4_loop

    def _gen(section, directive):
        return "regenerated"

    md = _strong_article()
    result = run_writer_v4_loop(md, corpus=[], section_generator=_gen, seed="s")
    # With no quality_check and an originality-clean corpus, loop should settle.
    assert "markdown" in result and "passed" in result

# end of M8 content-quality tests
