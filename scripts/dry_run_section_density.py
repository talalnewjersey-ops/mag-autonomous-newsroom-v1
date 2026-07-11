"""Dry validation for the Experience-signal enrichment fix (2026-07-11):
regenerate ONE real body section with the NEW prompt (agent_04's
_EXPERIENCE_SIGNAL_INSTRUCTION) via a SINGLE live Claude API call, and
compare its Experience-pattern match density against the REAL section it
replaces (witness run 9, article 1, body section 2 -- 0 matches / 539 words,
see AUDIT-LOG.md and tests/test_experience_signal_enrichment.py for the
locked baseline). Deliberately NOT a full witness run: one section, one API
call, cheap to re-run before committing to a production run.

Usage: ANTHROPIC_API_KEY=... python3 scripts/dry_run_section_density.py
"""
import asyncio
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents import agent_04_article_writer as agent_04

# The exact real section this replaces (run 9, article 1, OPPORTUNITY tier).
_TITLE = "Best Car Insurance for Foreign Drivers and International Students: Complete Guide for USA Immigrants (2026)"
_KEYWORD = "car insurance for foreign drivers"
_H2 = "What Is Car Insurance For Foreign Drivers And International Students And Why Do Immigrants Need It?"
_BASELINE_MATCHES = 0
_BASELINE_WORDS = 539

_EXPERIENCE_PATTERNS = [
    r'(?:based on|according to|our experience|we found|in practice)',
    r'(?:real-world|case study|example|scenario)',
    r'(?:tested|reviewed|analyzed|compared)',
    r'firsthand experience',
    r'built (?:his|her|their|our) own .{0,60}from scratch',
]


def _count_matches(text):
    return sum(len(re.findall(p, text, re.IGNORECASE)) for p in _EXPERIENCE_PATTERNS)


async def main():
    api_key = os.environ["ANTHROPIC_API_KEY"]
    sec_target = agent_04.OPPORTUNITY_SEC_TARGET_BASE
    prompt = (
        f"Write section ## 2. {_H2} for: {_TITLE} | {_KEYWORD}\n"
        f"{sec_target}-{sec_target + 150}w. Concise. No padding. BODY ONLY: no compliance "
        "disclaimer, no author bio, no brand slogan, no 'not financial advice' notice, no "
        "internal-link CTA in this section — those are written elsewhere exactly once."
        f"{agent_04._EXPERIENCE_SIGNAL_INSTRUCTION}"
    )
    text = await agent_04._call_claude(api_key, prompt, agent_04.SYSTEM_PROMPT, max_tokens=1800)
    words = len(text.split())
    matches = _count_matches(text)
    density = round(matches / words * 1000, 2) if words else 0.0
    baseline_density = round(_BASELINE_MATCHES / _BASELINE_WORDS * 1000, 2)

    print("=" * 70)
    print("GENERATED SECTION TEXT:")
    print("=" * 70)
    print(text)
    print("=" * 70)
    print(f"BEFORE (real run 9, article 1, body section 2): "
          f"{_BASELINE_MATCHES} matches / {_BASELINE_WORDS}w = {baseline_density}/1000w")
    print(f"AFTER  (this dry-run, new prompt):               "
          f"{matches} matches / {words}w = {density}/1000w")
    print(f"Calibration anchor (agents/_eeat_scoring.py): 4.0/1000w = 100/100")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
