"""RETRY SAFETY (2026-07-06): the retry mechanism must NEVER be allowed to ship
an article that is structurally worse than the one it replaced -- a real
control run showed a retry that fixed G-Substance's sourcing complaint but
silently dropped the entire FAQ section (13 H2s -> 8, has_faq True -> False).
That retry's draft would otherwise have sailed through every downstream gate
(none of them check "did we lose a whole section versus before").

Two modes, called from production_v2.yml around the retry loop:
  --snapshot: BEFORE a retry regenerates, record the REJECTED draft's own
    structure (h2_count, has_faq, word_count) to a small JSON file.
  --compare: AFTER a retry produces a new draft that otherwise passed every
    content gate, compare its structure against the snapshot. Exit 1 (with a
    clear reason) if the retry is WORSE -- more H2s / FAQ regained / more
    words is always fine; FEWER H2s, a FAQ that existed before and is now
    gone, or a word count more than 20% below the original snapshot is not.
"""
import argparse
import json
import re
import sys


def _metrics(text):
    return {
        "h2_count": len(re.findall(r"^##\s+", text, re.MULTILINE)),
        "has_faq": bool(re.search(r"^###\s+.+\?", text, re.MULTILINE)),
        "word_count": len(text.split()),
    }


def is_worse(before, after, max_word_drop_ratio=0.20):
    """Returns (worse: bool, reasons: list[str])."""
    reasons = []
    if after["h2_count"] < before["h2_count"]:
        reasons.append(f"h2_count dropped {before['h2_count']} -> {after['h2_count']}")
    if before["has_faq"] and not after["has_faq"]:
        reasons.append("FAQ section present before the retry, missing after")
    if before["word_count"] > 0:
        drop_ratio = (before["word_count"] - after["word_count"]) / before["word_count"]
        if drop_ratio > max_word_drop_ratio:
            reasons.append(
                f"word_count dropped {before['word_count']} -> {after['word_count']} "
                f"({drop_ratio:.0%} > {max_word_drop_ratio:.0%} tolerance)"
            )
    return bool(reasons), reasons


def main():
    ap = argparse.ArgumentParser(description="Retry structural-completeness safety gate")
    ap.add_argument("--input", required=True, help="Current article draft (markdown)")
    ap.add_argument("--snapshot", help="Write mode: save this draft's structure to this JSON path")
    ap.add_argument("--compare", help="Compare mode: compare this draft's structure against the JSON at this path")
    args = ap.parse_args()

    with open(args.input, encoding="utf-8") as f:
        text = f.read()
    current = _metrics(text)

    if args.snapshot:
        with open(args.snapshot, "w", encoding="utf-8") as f:
            json.dump(current, f)
        print(f"Structure snapshot saved: {current}")
        sys.exit(0)

    if args.compare:
        try:
            with open(args.compare, encoding="utf-8") as f:
                before = json.load(f)
        except Exception as e:
            print(f"No usable pre-retry snapshot ({e}) -- skipping completeness check, allowing through")
            sys.exit(0)
        worse, reasons = is_worse(before, current)
        if worse:
            print(f"RETRY REGRESSION: retry draft is structurally WORSE than the original rejected "
                  f"draft -- {'; '.join(reasons)}. The retry must never ship something worse than the "
                  f"original -- treating this as a failure.")
            sys.exit(1)
        print(f"Retry structure OK (before={before}, after={current})")
        sys.exit(0)

    ap.error("one of --snapshot or --compare is required")


if __name__ == "__main__":
    main()
