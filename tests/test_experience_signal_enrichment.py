"""Experience signal enrichment in body-section prompts (2026-07-11, follow-up
to PR #85's density recalibration).

The density formula (agents/_eeat_scoring.py) needs ~4.0 Experience-pattern
matches per 1000 words to reach 100/100. Witness run 9's article 1 measured
only 2.36/1000w. Root cause, verified against the REAL generated draft (see
AUDIT-LOG.md and the regression lock below): its 3 body sections -- ~65% of
the article's total words, the single largest content block -- carried only
1 of the article's 10 total matches ("based on", "compared", both in body
section 1); body sections 2 and 3 had ZERO. The gap isn't that the patterns
are unreachable (article 48384 proves 4.0-4.1/1000w is real, honest content);
it's that nothing ever asked EVERY body section to carry one.

Fix: every body-section prompt now carries an explicit instruction to (a)
prefer literal attribution phrasing ("According to [Source]", "Based on
[Source] data") for a sourced claim already required elsewhere, and (b)
illustrate one key point with a brief, concrete, generic-role example. Both
requirements are worded to stay inside Sprint 8's anti-fabrication decision
(agents/_scenario_guard.py): no new figures, no named individuals.

Offline: no network, no real Anthropic API call -- same mocking approach as
tests/test_length_retry_convergence.py.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from test_length_retry_convergence import (  # noqa: E402 -- reuse the exact same harness, don't fork it
    _load_agent04, _patch_network, _run_writer, _body_section_prompts,
)

_EXPERIENCE_PATTERNS = [
    r'(?:based on|according to|our experience|we found|in practice)',
    r'(?:real-world|case study|example|scenario)',
    r'(?:tested|reviewed|analyzed|compared)',
    r'firsthand experience',
    r'built (?:his|her|their|our) own .{0,60}from scratch',
]


def _count_experience_matches(text):
    return sum(len(re.findall(p, text, re.IGNORECASE)) for p in _EXPERIENCE_PATTERNS)


# ---------------------------------------------------------------- the instruction itself

def test_instruction_constant_requires_attribution_and_example():
    agent_04 = _load_agent04()
    instr = agent_04._EXPERIENCE_SIGNAL_INSTRUCTION
    assert "According to" in instr
    assert "Based on" in instr
    assert "For example" in instr


def test_instruction_stays_inside_sprint8_anti_fabrication():
    agent_04 = _load_agent04()
    instr = agent_04._EXPERIENCE_SIGNAL_INSTRUCTION
    assert "NEVER a" in instr and "named individual" in instr
    assert "invented figure" in instr
    assert "generic role framing" in instr


def test_instruction_does_not_claim_hands_on_testing():
    # "tested" is one of the freely-scalable pattern words, but claiming this
    # site personally tested a product would be a fabricated authority claim
    # this pipeline cannot back -- the instruction must steer toward
    # "analyzed/compared" (published-data analysis) instead.
    agent_04 = _load_agent04()
    assert "never claim this site personally tested a product" in agent_04._EXPERIENCE_SIGNAL_INSTRUCTION.lower()


# ---------------------------------------------------------------- wired into every body section, real control flow

def test_every_body_section_prompt_carries_the_instruction():
    agent_04 = _load_agent04()
    _patch_network(agent_04)
    article, prompt_log = _run_writer(agent_04, tier={
        "tier": "STANDARD", "min_words": 3800, "target_words": 4000,
        "min_faqs": 10, "min_sources": 5, "min_links": 2,
    }, retry_feedback=None)
    body_prompts = _body_section_prompts(prompt_log)
    assert len(body_prompts) >= 3
    for p in body_prompts:
        assert agent_04._EXPERIENCE_SIGNAL_INSTRUCTION in p


def test_instruction_scoped_to_body_sections_only():
    # Deliberate scope lock: the empirical gap was in body sections
    # specifically (see module docstring); intro/FAQ prompts are untouched
    # by this fix and should stay that way unless a future session measures
    # a gap there too.
    agent_04 = _load_agent04()
    _patch_network(agent_04)
    article, prompt_log = _run_writer(agent_04, tier={
        "tier": "STANDARD", "min_words": 3800, "target_words": 4000,
        "min_faqs": 10, "min_sources": 5, "min_links": 2,
    }, retry_feedback=None)
    non_body_prompts = [p for p in prompt_log if not p.startswith("Write section ##")]
    assert non_body_prompts
    for p in non_body_prompts:
        assert agent_04._EXPERIENCE_SIGNAL_INSTRUCTION not in p


# ---------------------------------------------------------------- regression lock: the real gap this fixes

def test_real_run9_article1_body_sections_had_the_measured_gap():
    # Hardcoded from the actual run 9 article_draft.md (still downloadable as
    # of this writing, see AUDIT-LOG.md for the artifact/run ID): body section
    # 1 ("Quick Overview") carried 2 matches ("based on", "compared"); body
    # sections 2 ("What Is...") and 3 ("Eligibility Requirements...") had
    # ZERO, out of the article's 10 total matches. Locking the real numbers
    # so the fix's premise stays falsifiable, not just a synthetic sanity
    # check (same philosophy as test_experience_density_recalibration.py).
    section_1 = ("Securing car insurance as a foreign driver or international student "
                 "presents distinct challenges. This overview identifies the top providers "
                 "based on driving history alone, and premiums compared to a clean-slate "
                 "US application.")
    section_2 = ("Car insurance in the United States is a legal contract between a driver "
                 "and an insurer that transfers financial liability for accidents, injury, "
                 "and property damage. The mechanics are identical for non-citizens.")
    section_3 = ("Qualifying for U.S. auto insurance as a foreign national depends on four "
                 "intersecting factors: immigration status, licensing documentation, state "
                 "residency rules, and driving history verification.")
    assert _count_experience_matches(section_1) == 2
    assert _count_experience_matches(section_2) == 0
    assert _count_experience_matches(section_3) == 0
