#!/usr/bin/env python3
"""
Offline tests for the M9 internal-consistency gate
(services/content_consistency.py). Deterministic: no network, no LLM, no
external truth-checking and no fabricated data. Verifies each detector, score
bounds, purity, the section mapping, and the writer-loop combiner.
"""
from __future__ import annotations

from services.content_consistency import (
    assess_consistency,
    consistency_sections,
    combine_checks,
    find_numeric_clashes,
    find_unsupported_absolutes,
    find_dangling_references,
    find_temporal_issues,
    MIN_CONSISTENCY_SCORE,
)


def _clean_article() -> str:
    return (
        "# Newcomer Guide\n\n"
        "## Fees\n\nAccording to official .gov sources, the application fee is "
        "$500 for most newcomers. As of 2025 this is current.\n\n"
        "## Banking\n\nThe monthly fee is $12 at many banks.\n\n"
        "## Conclusion\n\nReview each step on a checklist.\n"
    )


def test_clean_article_passes():
    report = assess_consistency(_clean_article())
    assert report["passed"] is True
    assert report["score"] >= MIN_CONSISTENCY_SCORE
    assert report["regenerate_sections"] == []


def test_numeric_clash_detected():
    text = "The application fee is $500 here. Later the application fee is $750."
    clashes = find_numeric_clashes(text)
    assert clashes
    assert any(c["label"].startswith("application fee") for c in clashes)


def test_no_numeric_clash_when_consistent():
    text = "The application fee is $500 here. The application fee is $500 later."
    assert find_numeric_clashes(text) == []


def test_unsupported_absolute_flagged():
    text = "This is always free for everyone. No citation appears anywhere here."
    findings = find_unsupported_absolutes(text)
    assert findings


def test_absolute_with_citation_is_ok():
    text = "According to official .gov sources, this is always free as of 2025."
    # "always" sits next to citation markers, so it should not be flagged.
    assert find_unsupported_absolutes(text) == []


def test_dangling_reference_detected():
    text = "# T\n\n## A\n\nbody\n\nSee Section 9 for details."
    findings = find_dangling_references(text)
    assert findings
    assert findings[0]["section_count"] == 1


def test_valid_section_reference_not_flagged():
    text = "# T\n\n## One\n\n## Two\n\nSee Section 1 for details."
    assert find_dangling_references(text) == []


def test_temporal_issue_detected():
    future = find_temporal_issues("These limits apply as of 2099.")
    past = find_temporal_issues("These limits apply as of 1850.")
    assert future and future[0]["year"] == 2099
    assert past and past[0]["year"] == 1850


def test_plausible_year_not_flagged():
    assert find_temporal_issues("These limits apply as of 2025.") == []


def test_score_bounded_and_penalised():
    bad = (
        "The fee is $500. The fee is $999. This is always guaranteed for everyone. "
        "See Section 14. As of 2099 nothing changes."
    )
    report = assess_consistency(bad)
    assert 0 <= report["score"] <= 100
    assert report["passed"] is False
    assert report["regenerate_sections"]


def test_empty_text_is_safe():
    report = assess_consistency("")
    assert report["score"] == 100
    assert report["passed"] is True
    assert report["regenerate_sections"] == []


def test_assess_consistency_is_pure():
    md = _clean_article()
    before = md
    assess_consistency(md)
    assert md == before


def test_consistency_sections_adapter():
    bad = "The fee is $500. The fee is $999."
    secs = consistency_sections(bad)
    assert isinstance(secs, list)
    assert "body" in secs


def test_combine_checks_unions_sections():
    def a(_md):
        return ["body"]

    def b(_md):
        return ["faq", "body"]

    combined = combine_checks(a, b)
    result = combined("anything")
    assert result == ["body", "faq"]  # order-preserving, de-duplicated


def test_combine_checks_swallows_errors():
    def good(_md):
        return ["introduction"]

    def boom(_md):
        raise ValueError("boom")

    combined = combine_checks(boom, good)
    # a raising check must not break the combiner.
    assert combined("x") == ["introduction"]


def test_combine_with_real_quality_and_consistency():
    from services.content_quality import assess_quality

    def quality_sections(md):
        return assess_quality(md)["regenerate_sections"]

    combined = combine_checks(quality_sections, consistency_sections)
    # A short, self-contradictory article should flag at least one section.
    bad = "# T\n\nThe fee is $500. The fee is $999. Short and weak."
    result = combined(bad)
    assert isinstance(result, list)
    assert result  # at least one section flagged by the union


def test_writer_loop_accepts_combined_check():
    from agents.agent_04_writer_v4 import run_writer_v4_loop

    def _gen(section, directive):
        return "regenerated"

    combined = combine_checks(consistency_sections)
    result = run_writer_v4_loop(
        "# T\n\nThe fee is $500. The fee is $999.",
        corpus=[], section_generator=_gen, seed="s", quality_check=combined,
    )
    assert "markdown" in result and "passed" in result

# end of M9 internal-consistency tests
