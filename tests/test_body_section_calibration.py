"""ATTEMPT-0 body-section calibration (2026-07-11, PR #81): #79/#80 only ever
acted AFTER generation, on a retry. Witness runs 5/6bis/7 showed the retry
mechanism (once fixed by #80) works, but STANDARD and PILLAR tiers routinely
overshoot the ceiling badly enough on attempt 0 that even a working retry
struggles to fully close the gap. This targets the actual source: the per-tier
body-section word target ATTEMPT 0 itself, recalibrated from real witness-run
data so the nominal case has a real chance of passing GATE LENGTH without a
retry at all -- "calibrate at the source, not a more aggressive cut" (the
user's own framing).

Real attempt-0 totals vs. declared target_words, before this fix (see
AUDIT-LOG.md's 2026-07-11 entries for the individual run IDs):
  OPPORTUNITY (target 4000): witness run 6bis=4709 (+17.7%), run 7=4401 (+10.0%) -- avg +13.9%
  STANDARD    (target 4000): witness run 5=5232 (+30.8%), 6bis=5492 (+37.3%), run 7=5572 (+39.3%) -- avg +35.8%
  PILLAR      (target 4200): witness run 6bis=6641 (+58.1%), run 7=6422 (+52.9%) -- avg +55.5%

The new sec_target_base for each tier cuts HALF of the headroom down to the
280w/section floor (not the whole gap) -- deliberately preserving real retry
headroom for GATE LENGTH's retry (#80) rather than exhausting it at attempt 0,
which would turn the retry into a no-op exactly when a tier still overshoots
after calibration (see tests/test_length_retry_convergence.py for what happens
to the retry's own headroom post-calibration).

Offline: no network, no real Anthropic API call -- same mocking approach as
tests/test_length_retry_convergence.py (a deterministic stand-in for
_call_claude that reads the word-count range stated in each prompt and
returns exactly that many words, biased to the range's UPPER bound for body
sections -- the harder, more conservative case to pass from).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import length_gate  # noqa: E402

from test_length_retry_convergence import (  # noqa: E402 -- reuse the exact same harness, don't fork it
    _load_agent04, _patch_network, _run_writer, _body_section_prompts, _parse_sec_target,
)


# ---------------------------------------------------------------- the calibrated constants themselves

def test_calibrated_constants_match_the_documented_real_data_derivation():
    agent_04 = _load_agent04()
    assert agent_04.BODY_SECTION_FLOOR_WORDS == 280
    assert agent_04.OPPORTUNITY_SEC_TARGET_BASE == 348
    assert agent_04.STANDARD_SEC_TARGET_BASE == 390
    assert agent_04.PILLAR_SEC_TARGET_BASE == 440


def test_every_tier_keeps_real_headroom_to_the_floor_after_calibration():
    # the whole point of capping at HALF the headroom: calibration must never
    # fully exhaust the floor headroom, or GATE LENGTH's retry (#80) becomes a
    # no-op for a tier that still overshoots after the calibrated attempt 0.
    agent_04 = _load_agent04()
    floor = agent_04.BODY_SECTION_FLOOR_WORDS
    for base in (agent_04.OPPORTUNITY_SEC_TARGET_BASE, agent_04.STANDARD_SEC_TARGET_BASE, agent_04.PILLAR_SEC_TARGET_BASE):
        assert base > floor, "attempt-0 calibration must never reach the floor itself"


def test_calibration_cut_matches_min_of_data_driven_need_and_half_headroom():
    # the rule is min(needed_cut_from_real_data, half of the pre-#81 headroom to the
    # floor) -- OPPORTUNITY's real-data need (52w) is UNDER half its headroom (60w),
    # so it gets the smaller, data-driven cut uncapped; STANDARD/PILLAR's real-data
    # need (258w/383w) EXCEEDS half their headroom (110w/160w), so THEY hit the cap.
    agent_04 = _load_agent04()
    floor = agent_04.BODY_SECTION_FLOOR_WORDS
    pre_pr81_bases = {"OPPORTUNITY": 400, "STANDARD": 500, "PILLAR": 600}
    needed_cut_from_data = {"OPPORTUNITY": 52, "STANDARD": 258, "PILLAR": 383}  # see module docstring
    new_bases = {
        "OPPORTUNITY": agent_04.OPPORTUNITY_SEC_TARGET_BASE,
        "STANDARD": agent_04.STANDARD_SEC_TARGET_BASE,
        "PILLAR": agent_04.PILLAR_SEC_TARGET_BASE,
    }
    for tier, old_base in pre_pr81_bases.items():
        half_headroom = (old_base - floor) // 2
        applied_cut = old_base - new_bases[tier]
        assert applied_cut == min(needed_cut_from_data[tier], half_headroom), tier
    # and confirm which regime each tier actually falls into, so this test can't
    # silently stop exercising the "capped" branch if the data changes later.
    assert needed_cut_from_data["OPPORTUNITY"] < (pre_pr81_bases["OPPORTUNITY"] - floor) // 2  # uncapped
    assert needed_cut_from_data["STANDARD"] > (pre_pr81_bases["STANDARD"] - floor) // 2  # capped
    assert needed_cut_from_data["PILLAR"] > (pre_pr81_bases["PILLAR"] - floor) // 2  # capped


# ---------------------------------------------------------------- wiring: the calibrated base is what attempt 0 actually asks for

def test_attempt0_prompts_use_the_new_calibrated_base_not_the_old_one():
    agent_04 = _load_agent04()
    _patch_network(agent_04)
    for tier_name, expected_base in [
        ("OPPORTUNITY", 348), ("STANDARD", 390), ("PILLAR", 440),
    ]:
        tier = agent_04._get_tier_config(tier_name)
        _article, prompts = _run_writer(agent_04, tier, retry_feedback="")
        body_prompts = _body_section_prompts(prompts)
        assert body_prompts, tier_name
        assert _parse_sec_target(body_prompts[0]) == expected_base, tier_name


# ---------------------------------------------------------------- the actual goal: nominal case passes without a retry

def test_opportunity_tier_nominal_attempt0_passes_gate_length_without_a_retry():
    """The one tier where calibration was predicted to fully close the gap
    (avg overshoot +13.9%, well inside what half the floor headroom can absorb).
    This is the primary goal PR #81 was built for: "le cas nominal doit passer
    SANS retry"."""
    agent_04 = _load_agent04()
    _patch_network(agent_04)
    tier = agent_04._get_tier_config("OPPORTUNITY")
    article, _prompts = _run_writer(agent_04, tier, retry_feedback="", body_section_bias="upper")
    word_count = len(article.split())
    report = length_gate.evaluate(word_count, "OPPORTUNITY")
    assert not report["over_ceiling"], (
        f"expected the calibrated OPPORTUNITY attempt 0 to pass GATE LENGTH without a retry, "
        f"got {word_count}w (ceiling {report['ceiling_words']}w)"
    )


def test_standard_and_pillar_tiers_are_measurably_improved_but_may_still_need_a_retry():
    """STANDARD and PILLAR's real overshoot (+35.8%, +55.5%) is too large for
    HALF the floor headroom to fully absorb at attempt 0 -- calibration
    narrows the gap (proven here by comparing the SAME mock scenario at the
    old vs. new base) without a guarantee of zero-retry convergence for these
    two tiers. Honest documentation of a real, known limitation -- see
    tests/test_length_retry_convergence.py for how much headroom the retry
    still has left to close the remainder."""
    for tier_name, old_base_attr_default in [("STANDARD", 500), ("PILLAR", 600)]:
        agent_04 = _load_agent04()
        _patch_network(agent_04)
        tier = agent_04._get_tier_config(tier_name)

        # actual (new, calibrated) base
        article_new, _ = _run_writer(agent_04, tier, retry_feedback="", body_section_bias="upper")
        word_count_new = len(article_new.split())

        # same exact mock scenario, but forced back to the pre-#81 base, for a fair comparison
        agent_04_old = _load_agent04()
        _patch_network(agent_04_old)
        attr = f"{tier_name}_SEC_TARGET_BASE"
        setattr(agent_04_old, attr, old_base_attr_default)
        article_old, _ = _run_writer(agent_04_old, tier, retry_feedback="", body_section_bias="upper")
        word_count_old = len(article_old.split())

        assert word_count_new < word_count_old, (
            f"{tier_name}: calibration should measurably reduce the attempt-0 total "
            f"({word_count_old}w -> {word_count_new}w expected to go down)"
        )
