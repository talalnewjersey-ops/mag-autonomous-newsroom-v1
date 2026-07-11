"""MICRO-TRIM (2026-07-11, PR #81): a tiny GATE LENGTH overage (real finding:
witness run 7, article 1, OPPORTUNITY tier, 4401w vs a 4400w ceiling -- +1w)
does not deserve a full regeneration retry. A +1w overage gives GATE LENGTH's
retry-cut logic almost nothing to act on (cut_per_section rounds to ~1w), so
the retry attempt is really just "regenerate at a near-identical target,
subject to ordinary LLM variance" -- real data shows that variance alone can
swing the result by several hundred words either way (the SAME run's article 1
went 4401w -> 4976w on retry, WORSE, purely from noise around a negligible
cut). A near-miss should be fixed mechanically, at zero extra API cost, not
gambled on a full retry.

DELETION-ONLY, deterministic (no LLM): below a small overage threshold
(MICRO_TRIM_MAX_RATIO of the ceiling), removes the LAST SENTENCE of the
LONGEST body section NOT protected from trimming (see _PROTECTED_HEADING_RE --
the FAQ, comparison table, expert recommendation, illustrative scenario,
disclaimer, and author bio are never touched, same denylist philosophy as
GATE LENGTH's own retry-feedback instruction in agent_04_article_writer.py).
Repeats (bounded) until under the ceiling, never below this tier's min_words,
never emptying a section down to nothing.

Runs AFTER prose polish, BEFORE GATE LENGTH (Phase 4.441 in production_v2.yml)
-- non-blocking (`|| true`): a large overage is intentionally left untouched
here (deferred to length_gate.py's own retry, which is the "last resort" for
anything micro-trim can't safely absorb).
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.agent_04_article_writer import _get_tier_config
import length_gate  # noqa: E402 -- sibling script (both live in scripts/); single source of truth for the ceiling formula

MICRO_TRIM_MAX_RATIO = 0.02  # 2% of the ceiling -- above this, defer to the real retry

_H2_RE = re.compile(r"^##\s+.+$", re.MULTILINE)
_PROTECTED_HEADING_RE = re.compile(
    r"(?i)\b(faq|frequently asked|comparison|compare|expert recommendation|top pick|"
    r"runner-up|illustrative scenario|scenario|disclaimer|about\s+the\s+author|conclusion)\b"
)
# abbreviation-guarded-ish sentence boundary: a period/!/? followed by whitespace and
# a capital letter, digit, or quote -- good enough for picking a LAST sentence to
# drop (worst case: an imperfect split still drops a short trailing clause, never
# more than that single micro-trim step targets).
_SENTENCE_END_RE = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9"‘“])')


def _h2_blocks(text):
    starts = [m.start() for m in _H2_RE.finditer(text)]
    if not starts:
        return []
    blocks = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(text)
        blocks.append((s, e))
    return blocks


def _heading_line(text, start, end):
    return text[start:end].split("\n", 1)[0]


def _split_sentences(paragraph):
    return [s for s in _SENTENCE_END_RE.split(paragraph) if s.strip()]


def _trim_one_sentence(text, min_words):
    """Removes the last sentence of the longest trim-eligible H2 block. Returns
    (new_text, trimmed) -- trimmed is False if no eligible/safe cut was found
    (e.g. every eligible block is down to its last sentence already, or the
    only cut available would breach min_words)."""
    blocks = _h2_blocks(text)
    eligible = [(s, e) for s, e in blocks if not _PROTECTED_HEADING_RE.search(_heading_line(text, s, e))]
    if not eligible:
        return text, False

    eligible.sort(key=lambda se: len(text[se[0]:se[1]].split()), reverse=True)
    for s, e in eligible:
        block = text[s:e]
        heading, _, body = block.partition("\n")
        paragraphs = body.split("\n\n")
        # find the last non-empty paragraph with more than one sentence -- dropping
        # a paragraph's ONLY sentence would gut it entirely, which is not a micro-trim.
        for pi in range(len(paragraphs) - 1, -1, -1):
            sentences = _split_sentences(paragraphs[pi])
            if len(sentences) < 2:
                continue
            new_word_count = len(text.split()) - len(sentences[-1].split())
            if new_word_count < min_words:
                continue  # this cut would breach min_words -- try another block/paragraph
            paragraphs[pi] = " ".join(sentences[:-1]).rstrip()
            new_body = "\n\n".join(paragraphs)
            new_block = heading + "\n" + new_body
            return text[:s] + new_block + text[e:], True
    return text, False


def micro_trim(text, article_type, min_words, max_iterations=5):
    report = {"performed": False, "sentences_trimmed": 0, "reason": None}
    word_count = len(text.split())
    result = length_gate.evaluate(word_count, article_type)
    report["word_count_before"] = word_count

    if not result["over_ceiling"]:
        report["reason"] = "not_over_ceiling"
        report["word_count_after"] = word_count
        return text, report

    overage_ratio = result["over_by_words"] / result["ceiling_words"]
    if overage_ratio > MICRO_TRIM_MAX_RATIO:
        report["reason"] = (
            f"overage_too_large_for_micro_trim ({overage_ratio:.1%} > {MICRO_TRIM_MAX_RATIO:.0%} "
            "of ceiling) -- deferring to GATE LENGTH's retry"
        )
        report["word_count_after"] = word_count
        return text, report

    trimmed_any = False
    for _ in range(max_iterations):
        wc = len(text.split())
        current = length_gate.evaluate(wc, article_type)
        if not current["over_ceiling"]:
            break
        text, trimmed = _trim_one_sentence(text, min_words)
        if not trimmed:
            break
        trimmed_any = True
        report["sentences_trimmed"] += 1

    final_word_count = len(text.split())
    report["performed"] = trimmed_any
    report["word_count_after"] = final_word_count
    if trimmed_any and not length_gate.evaluate(final_word_count, article_type)["over_ceiling"]:
        report["reason"] = "trimmed_under_ceiling"
    elif trimmed_any:
        report["reason"] = "trimmed_but_still_over_ceiling -- deferring remainder to GATE LENGTH's retry"
    else:
        report["reason"] = "no_safe_cut_found (would breach min_words or no eligible section) -- deferring to GATE LENGTH's retry"
    return text, report


def main():
    ap = argparse.ArgumentParser(description="MICRO-TRIM -- deletion-only mechanical fix for a tiny (<=2%) GATE LENGTH overage")
    ap.add_argument("--input", required=True, help="article_draft.md (rewritten in place only if a trim is performed)")
    ap.add_argument("--article-type", default="STANDARD")
    ap.add_argument("--report", default=None)
    args = ap.parse_args()

    tier = _get_tier_config(args.article_type)
    content = Path(args.input).read_text(encoding="utf-8")
    trimmed_text, report = micro_trim(content, args.article_type, tier["min_words"])

    if report["performed"]:
        Path(args.input).write_text(trimmed_text, encoding="utf-8")
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"[MICRO-TRIM] {report}")
    sys.exit(0)  # NON-BLOCKING: micro-trim never rejects, GATE LENGTH (next step) is the real gate


if __name__ == "__main__":
    main()
