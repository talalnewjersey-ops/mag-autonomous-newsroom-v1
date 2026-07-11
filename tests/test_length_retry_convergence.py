"""GATE LENGTH RETRY convergence (2026-07-11, PR #80): the gap #79's own tests
missed was testing the retry in ISOLATION (string-presence assertions on the
prompt template) without ever wiring it through the real generation function.
Witness run 6 bis proved that gap was real: GATE LENGTH correctly detected and
blocked 3/3 oversized drafts, but the "shortening retry" made 2 of the 3
articles LONGER, not shorter -- because retry_feedback never reached the intro
or the body-section loop (the largest word-count contributor), which
regenerated at the exact same fixed per-tier target on both attempts.

This suite exercises agents.agent_04_article_writer._write_article_standalone
END TO END (network/API mocked, control flow real) to prove:
  1. On a length-gate retry, EVERY generation call -- intro included, not just
     comparison/expert/FAQ/closing -- receives the retry feedback.
  2. The body-section word target is reduced PROPORTIONALLY to the measured
     overage (scripts/length_gate.py + scripts/gate_feedback.py's REAL parsing
     logic, not a hand-rolled shadow copy).
  3. For a realistic +30% (over target) overage, the reduced target actually
     converges under the ceiling within the SINGLE retry production_v2.yml
     allows (there is no second retry -- "for RETRY_ATTEMPT in 0 1", see
     tests/test_retry_feedback.py::test_workflow_retry_is_bounded_not_infinite).
  4. For a tier whose section budget is already close to the safety floor
     (OPPORTUNITY), the SAME +30% overage may NOT converge in that one retry --
     documented here, not swept under the rug -- and that is by design: the
     floor exists so a retry trims prose rather than gutting a section into
     thin, incomplete content. A non-convergent retry fails GATE LENGTH a
     second time and the article is dropped cleanly (ARTICLES_FAILED+1,
     continue 2 -- unchanged, already covered by
     tests/test_retry_safety.py::test_workflow_regression_is_treated_as_full_failure_not_a_fallback).

Offline: no network, no real Anthropic API call. _call_claude and every
network-touching helper (internal links, official sources, methodology links)
are replaced with deterministic stand-ins; scripts/length_gate.py and
scripts/gate_feedback.py run FOR REAL (same code the workflow calls).
"""
import asyncio
import importlib.util
import json
import os
import re
import sys
import tempfile
import unittest.mock as mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import length_gate  # noqa: E402
import gate_feedback  # noqa: E402


def _load_agent04():
    # Fresh module instance per import (matches tests/test_agent04_http_error_body_logged.py)
    # so monkeypatches here never leak into another test file's module object.
    spec = importlib.util.spec_from_file_location("agent_04_convergence_test",
                                                    os.path.join(ROOT, "agents/agent_04_article_writer.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_WORD_RANGE_RE = re.compile(r"(\d+)-(\d+)\s*w(?:ords)?\b")
_FAQ_COUNT_RE = re.compile(r"(\d+) questions \(minimum (\d+)\)")


def _make_fake_call_claude(prompt_log, body_section_bias="upper"):
    """Deterministic stand-in for a rule-following LLM: reads the word-count
    range actually stated in EACH prompt and returns exactly that many words --
    so a smaller instructed range on retry mechanically produces smaller
    output, same as it would from a compliant real model. body_section_bias=
    "upper" reproduces a verbose-but-compliant writer (matches the real
    witness-run data: articles landed at or above their stated ranges, never
    below) -- the more conservative/pessimistic assumption for a convergence
    test, since it is the harder case to converge from.
    """
    async def fake_call_claude(api_key, prompt, system=None, max_tokens=5000, model=None):
        prompt_log.append(prompt)
        if prompt.startswith("Write FAQ section"):
            m = _FAQ_COUNT_RE.search(prompt)
            target_faqs = int(m.group(1)) if m else 12
            return "\n\n".join(
                f"### Question {i + 1}?\n\n" + " ".join(["answer"] * 80)
                for i in range(target_faqs)
            )
        if prompt.startswith("Write 2 sections for"):
            return ("## Conclusion\n\n" + " ".join(["word"] * 250)
                     + "\n\n## Disclaimer\n\n" + " ".join(["word"] * 175))
        if prompt.startswith("Write ONE short sub-section"):
            return "### Illustrative Scenario: Test Case, Example Context\n\nA generic role holder does one generic qualifying thing."
        m = _WORD_RANGE_RE.search(prompt)
        if not m:
            return " ".join(["word"] * 100)
        lo, hi = int(m.group(1)), int(m.group(2))
        n = hi if (body_section_bias == "upper" and prompt.startswith("Write section ##")) else (lo + hi) // 2
        return " ".join(["word"] * n)
    return fake_call_claude


def _patch_network(agent_04):
    agent_04.fetch_real_posts = lambda: []
    agent_04.fetch_methodology_links = lambda: []
    agent_04.resolve_vertical = lambda market, category: "us_default"  # no VERTICAL_FACTS entry -> _build_facts_block("") safely
    agent_04.has_curated_pool = lambda vertical: False
    agent_04.select_official_sources = lambda *a, **k: []
    agent_04.build_scenario_block = lambda raw, vertical: (f"## Illustrative Scenarios\n\n{raw}\n", True, [])


_OUTLINE = {
    "title": "Test Article Title",
    "primary_keyword": "test keyword",
    "market": "USA",
    "category": "credit_cards",
    "target_audience": "newcomers and immigrants in the USA",
    "sections": [{"h2": f"Section {i}"} for i in range(1, 6)],  # 5 generic sections, safe for every tier (max_sections<=5)
    "faq": [],
    "key_takeaways": [],
}


def _make_length_retry_feedback(word_count, article_type):
    """Builds retry_feedback EXACTLY the way production_v2.yml does: run the
    real GATE LENGTH evaluator, write its report to disk, run the real
    gate_feedback.length() parser on it -- not a hand-typed feedback string."""
    report = length_gate.evaluate(word_count, article_type)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(report, f)
        path = f.name
    try:
        feedback = gate_feedback.length(path)
    finally:
        os.unlink(path)
    return report, feedback


def _run_writer(agent_04, tier, retry_feedback, body_section_bias="upper"):
    prompt_log = []
    fake_call_claude = _make_fake_call_claude(prompt_log, body_section_bias=body_section_bias)
    with mock.patch.object(agent_04, "_call_claude", fake_call_claude):
        article = asyncio.run(agent_04._write_article_standalone(
            outline=_OUTLINE, api_key="fake-key",
            min_words=tier["min_words"], target_words=tier["target_words"],
            tier=tier, retry_feedback=retry_feedback))
    return article, prompt_log


def _body_section_prompts(prompt_log):
    return [p for p in prompt_log if p.startswith("Write section ##")]


def _parse_sec_target(prompt):
    m = _WORD_RANGE_RE.search(prompt)
    assert m, f"no word-count range found in prompt: {prompt[:80]}..."
    return int(m.group(1))  # the range's LOWER bound is sec_target itself


# ---------------------------------------------------------------- baseline: no retry_feedback

def test_no_retry_feedback_touches_no_prompt():
    agent_04 = _load_agent04()
    _patch_network(agent_04)
    tier = agent_04._get_tier_config("STANDARD")
    _article, prompts = _run_writer(agent_04, tier, retry_feedback="")
    assert prompts, "expected at least one _call_claude invocation"
    for p in prompts:
        assert "PREVIOUS ATTEMPT REJECTED" not in p


# ---------------------------------------------------------------- the requested end-to-end test

def test_length_gate_retry_reaches_every_generation_call_including_intro():
    agent_04 = _load_agent04()
    _patch_network(agent_04)
    tier = agent_04._get_tier_config("STANDARD")

    # Attempt 0: no feedback yet, honest fresh generation.
    article0, prompts0 = _run_writer(agent_04, tier, retry_feedback="")
    word_count0 = len(article0.split())

    # The mock's natural output overshoots the ceiling (matches the real witness-run
    # pattern) -- build the retry feedback from it using the REAL gate + REAL parser,
    # exactly as production_v2.yml does between attempt 0 and attempt 1.
    report0, retry_feedback = _make_length_retry_feedback(word_count0, "STANDARD")
    assert report0["over_ceiling"], (
        f"test setup assumption broken: mock attempt 0 ({word_count0}w) did not "
        f"exceed the ceiling ({report0['ceiling_words']}w) -- adjust the mock."
    )

    article1, prompts1 = _run_writer(agent_04, tier, retry_feedback=retry_feedback)

    # (1) EVERY call on the retry attempt carries the feedback -- intro included.
    intro_prompts_1 = [p for p in prompts1 if p.startswith("Write introduction")]
    body_prompts_1 = _body_section_prompts(prompts1)
    assert intro_prompts_1 and body_prompts_1
    for p in intro_prompts_1 + body_prompts_1:
        assert "PREVIOUS ATTEMPT REJECTED -- FIX THIS SPECIFICALLY" in p
        assert retry_feedback in p

    # ... and NONE of attempt 0's calls (no feedback existed yet) do.
    for p in prompts0:
        assert "PREVIOUS ATTEMPT REJECTED" not in p

    # (2) the body-section target actually shrank, proportionally to the real overage --
    # not just "some string got longer somewhere".
    sec_target_0 = _parse_sec_target(_body_section_prompts(prompts0)[0])
    sec_target_1 = _parse_sec_target(body_prompts_1[0])
    assert sec_target_1 < sec_target_0

    max_sections = len(body_prompts_1)
    expected_cut = min(sec_target_0 - agent_04.BODY_SECTION_FLOOR_WORDS, -(-report0["over_by_words"] // max_sections))
    assert sec_target_0 - sec_target_1 == expected_cut, (
        "the cut must match the code's own formula exactly, not just be 'smaller'"
    )

    # (3) and the total word count actually went DOWN on retry -- the exact failure
    # mode witness run 6 bis hit (2 of 3 articles got LONGER, not shorter).
    word_count1 = len(article1.split())
    assert word_count1 < word_count0, (
        f"retry made the article LONGER ({word_count0}w -> {word_count1}w) -- "
        "this is precisely the witness-run-6-bis regression this fix targets."
    )


# ---------------------------------------------------------------- convergence, post-#81 calibration
#
# PR #81 recalibrated each tier's ATTEMPT-0 sec_target_base down (see
# agents/agent_04_article_writer.py's BODY_SECTION_FLOOR_WORDS/*_SEC_TARGET_BASE
# comment for the real-data derivation), capped at HALF the headroom down to the
# 280w floor -- deliberately leaving the OTHER half for a retry to still use. That
# means a retry now starts from a LOWER base than before #81, so it has LESS room
# left to cut: the same "+30% over target" stress scenario that used to converge
# for STANDARD (base 500) no longer does at the recalibrated base (390) -- it now
# hits the floor, same as OPPORTUNITY always did. These tests reference the REAL
# module constants (never hardcoded literals) so they can't silently drift out of
# sync with a future recalibration the way the pre-#81 version of this file did.

def test_moderate_overage_standard_tier_converges_in_the_single_retry():
    """A moderate overage that fits within STANDARD's POST-#81 cut capacity
    (max_sections x (sec_target_base - floor)) converges in the one retry
    production_v2.yml allows."""
    agent_04 = _load_agent04()
    _patch_network(agent_04)
    tier = agent_04._get_tier_config("STANDARD")

    max_sections = 4
    sec_target_base = agent_04.STANDARD_SEC_TARGET_BASE
    floor = agent_04.BODY_SECTION_FLOOR_WORDS
    capacity = (sec_target_base - floor) * max_sections
    assert capacity == 440, "this test's overage is chosen relative to this capacity -- update both together"
    overage = 400  # comfortably inside capacity, unlike the old (pre-#81) 800w stress scenario
    simulated_word_count_attempt0 = 4400 + overage  # ceiling + overage
    report, retry_feedback = _make_length_retry_feedback(simulated_word_count_attempt0, "STANDARD")
    assert report["ceiling_words"] == 4400
    assert report["over_by_words"] == overage

    expected_cut = min(sec_target_base - floor, -(-overage // max_sections))
    assert expected_cut < sec_target_base - floor, "test setup should stay UNCLAMPED -- see the floor-clamped test below for that case"
    expected_sec_target = sec_target_base - expected_cut

    article1, prompts1 = _run_writer(agent_04, tier, retry_feedback=retry_feedback, body_section_bias="upper")
    body_prompts_1 = _body_section_prompts(prompts1)
    assert _parse_sec_target(body_prompts_1[0]) == expected_sec_target

    word_count1 = len(article1.split())
    assert word_count1 <= report["ceiling_words"], (
        f"expected the single retry to converge under the {report['ceiling_words']}w ceiling "
        f"for a {overage}w STANDARD overage (within post-#81 cut capacity), got {word_count1}w"
    )


def test_large_overage_is_floor_clamped_on_every_tier_after_calibration():
    """A large overage (the same +30%-over-target magnitude used pre-#81) now
    floor-clamps on EVERY tier, not just OPPORTUNITY -- because #81 intentionally
    spent half of each tier's floor headroom on attempt-0 calibration, leaving
    less for the retry to use. A REAL, documented trade-off, not a regression:
    the floor still exists to stop a retry from gutting a section into thin,
    incomplete content. This does NOT assert full-article convergence (that
    also depends on non-body-section sizes a deterministic mock can't represent
    with real-LLM fidelity) -- only that the code's own formula clamps correctly
    and that the clamped value is what reaches the prompt (wiring proof). If a
    retry's actual result still exceeds the ceiling in production, GATE LENGTH
    fails a second time and the article is dropped cleanly (ARTICLES_FAILED+1,
    continue 2 -- unchanged, see
    tests/test_retry_safety.py::test_workflow_regression_is_treated_as_full_failure_not_a_fallback
    and tests/test_retry_feedback.py::test_workflow_logs_explicitly_on_retry_and_on_exhaustion)."""
    agent_04 = _load_agent04()
    _patch_network(agent_04)
    floor = agent_04.BODY_SECTION_FLOOR_WORDS

    cases = [
        ("OPPORTUNITY", 3, agent_04.OPPORTUNITY_SEC_TARGET_BASE),
        ("STANDARD", 4, agent_04.STANDARD_SEC_TARGET_BASE),
        ("PILLAR", 5, agent_04.PILLAR_SEC_TARGET_BASE),
    ]
    for tier_name, max_sections, sec_target_base in cases:
        tier = agent_04._get_tier_config(tier_name)
        target = tier["target_words"]
        simulated_word_count_attempt0 = round(target * 1.30)  # the same stress magnitude #80's tests used
        report, retry_feedback = _make_length_retry_feedback(simulated_word_count_attempt0, tier_name)

        headroom = sec_target_base - floor
        unclamped_cut = -(-report["over_by_words"] // max_sections)
        assert unclamped_cut > headroom, (
            f"{tier_name}: test setup assumption broken -- this overage should exceed the tier's "
            f"headroom ({headroom}w) so the floor is the binding constraint; adjust the scenario."
        )
        expected_sec_target = sec_target_base - headroom  # == floor, by construction
        assert expected_sec_target == floor

        _article1, prompts1 = _run_writer(agent_04, tier, retry_feedback=retry_feedback, body_section_bias="upper")
        body_prompts_1 = _body_section_prompts(prompts1)
        assert _parse_sec_target(body_prompts_1[0]) == expected_sec_target, tier_name
