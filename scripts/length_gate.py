"""GATE LENGTH (2026-07-11) -- symmetric ceiling counterpart to agent_04's
word-count control, which is floor-only: _write_article_standalone expands
the article when it's under min_words, but nothing anywhere checks an
overshoot at generation time.

Real finding (witness run 5, article 2, us-send-money-to-india, STANDARD
tier): base generation produced 5232 words against a 4000w target -- +30.8%.
agent_12_quality_assurance.py's own tier-relative word-count check caught
it (content_details.score dropped to 60, overall_score=82.5), but GATE QA
and GATE EDITOR sit OUTSIDE production_v2.yml's retry loop (which only
covers G-Substance/G3/GATE A/GATE B) -- a base-generation overshoot had
zero chance to self-correct before the article was declared failed.

This gate runs INSIDE that same retry loop (Phase 4.445, right after Couche
2/prose-polish and before G-Substance), so an overshoot gets the same
retry-with-feedback chance as every other content gate. Same tolerance as
agent_12_quality_assurance.py's _WORD_COUNT_TOLERANCE (0.10) -- one
canonical ceiling, not a second guess.

Tier word budgets are read from agents.agent_04_article_writer._get_tier_config
(single source of truth -- not a third copy of the PILLAR/STANDARD/OPPORTUNITY
numbers).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.agent_04_article_writer import _get_tier_config

WORD_COUNT_TOLERANCE = 0.10  # matches agents/agent_12_quality_assurance.py::_WORD_COUNT_TOLERANCE


def evaluate(word_count: int, article_type: str) -> dict:
    tier = _get_tier_config(article_type)
    target = tier["target_words"]
    ceiling = round(target * (1 + WORD_COUNT_TOLERANCE))
    over_by = max(0, word_count - ceiling)
    return {
        "tier": tier["tier"],
        "target_words": target,
        "ceiling_words": ceiling,
        "word_count": word_count,
        "over_ceiling": word_count > ceiling,
        "over_by_words": over_by,
    }


def main():
    ap = argparse.ArgumentParser(description="GATE LENGTH -- ceiling counterpart to agent_04's floor-only expansion")
    ap.add_argument("--input", required=True)
    ap.add_argument("--article-type", default="STANDARD")
    ap.add_argument("--output", default=None)
    args = ap.parse_args()

    content = Path(args.input).read_text(encoding="utf-8")
    word_count = len(content.split())
    result = evaluate(word_count, args.article_type)

    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")

    if result["over_ceiling"]:
        print(f"GATE LENGTH FAIL: {word_count}w > ceiling {result['ceiling_words']}w "
              f"(tier {result['tier']}, target {result['target_words']}w, +{result['over_by_words']}w over)")
    else:
        print(f"GATE LENGTH PASS: {word_count}w <= ceiling {result['ceiling_words']}w (tier {result['tier']})")
    sys.exit(1 if result["over_ceiling"] else 0)


if __name__ == "__main__":
    main()
