"""Couche 3 -- G-Substance gate (BLOCKING).

Runs at Phase 4.45, AFTER the Couche 2 soften and BEFORE every phase that could
reach WordPress (fact-check is Phase 5; the WordPress draft is Phase 11). It
rejects a HOLLOW article -- one that, once soften removed the fabricated figures,
no longer stands on real substance -- so the pipeline never trades "hallucinated"
for "hollow" silently.

FAIL if ANY of the following (OR / strict gate):
  (1) fewer DISTINCT allow-listed source URLs than the tier floor
      (PILLAR 6 / STANDARD 4 / OPPORTUNITY 3);
  (2) strip-ratio (unsourced_found / numeric_claims_total, from soften_report)
      ABOVE --max-strip-ratio (default 0.50) -- the article leaned on fabrication;
  (3) structure broken -- no FAQ section, OR fewer H2 sections than the tier floor.

On FAIL the script exits non-zero; the workflow does `continue`, so agent_11
(Phase 11) never runs: NO WordPress object is created (not even a draft) and, with
no PRODUCED.json, the reconcile rolls the topic back to candidate. A hollow article
can therefore never be published -- the sprint 9/10 invariant, enforced earlier.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents._claims import _URL_IN
from agents._sources import _classify_url

# Tier floors. min_sources mirrors agent_04's per-tier source requirement so the
# floor is tier-aware (never sur-blocks legitimately source-poor OPPORTUNITY work).
TIER = {
    "PILLAR":      {"min_sources": 6, "min_h2": 5},
    "STANDARD":    {"min_sources": 4, "min_h2": 4},
    "GOLD":        {"min_sources": 4, "min_h2": 4},
    "OPPORTUNITY": {"min_sources": 3, "min_h2": 3},
}
_FAQ_RE = re.compile(r"##\s+(?:Frequently Asked Questions|FAQ)", re.IGNORECASE)  # == agent_12
_H2_RE = re.compile(r"(?m)^##\s+\S")  # H2 only ("## x", never "### x")


def evaluate(content, soften_report, article_type, max_strip_ratio=0.50):
    cfg = TIER.get((article_type or "STANDARD").upper(), TIER["STANDARD"])
    distinct_sources = len({u for u in _URL_IN.findall(content) if _classify_url(u) == "official"})
    h2_count = len(_H2_RE.findall(content))
    has_faq = bool(_FAQ_RE.search(content))
    total = int(soften_report.get("numeric_claims_total", 0) or 0)
    unsourced = int(soften_report.get("unsourced_found", 0) or 0)
    strip_ratio = (unsourced / total) if total else 0.0

    reasons = []  # OR gate: any single reason -> FAIL
    if distinct_sources < cfg["min_sources"]:
        reasons.append(f"only {distinct_sources} distinct official sources (need >= {cfg['min_sources']})")
    if strip_ratio > max_strip_ratio:
        reasons.append(f"strip-ratio {strip_ratio:.0%} > {max_strip_ratio:.0%} (leaned on fabrication)")
    if not has_faq:
        reasons.append("no FAQ section")
    if h2_count < cfg["min_h2"]:
        reasons.append(f"only {h2_count} H2 sections (need >= {cfg['min_h2']})")

    return {
        "verdict": "FAIL" if reasons else "PASS",
        "reasons": reasons,
        "tier": (article_type or "STANDARD").upper(),
        "distinct_sources": distinct_sources,
        "strip_ratio": round(strip_ratio, 3),
        "h2_count": h2_count,
        "has_faq": has_faq,
    }


def main():
    ap = argparse.ArgumentParser(description="Couche 3 G-Substance gate (BLOCKING).")
    ap.add_argument("--input", required=True, help="softened article_draft.md")
    ap.add_argument("--soften-report", default=None, help="soften_report.json from Couche 2")
    ap.add_argument("--article-type", default="STANDARD")
    ap.add_argument("--output", default=None, help="path for g_substance_report.json")
    ap.add_argument("--max-strip-ratio", type=float, default=0.50)
    args = ap.parse_args()

    content = Path(args.input).read_text(encoding="utf-8")
    soften_report = {}
    if args.soften_report and Path(args.soften_report).exists():
        try:
            soften_report = json.loads(Path(args.soften_report).read_text(encoding="utf-8"))
        except Exception:
            soften_report = {}  # missing/corrupt report -> strip-ratio criterion is a no-op

    result = evaluate(content, soften_report, args.article_type, args.max_strip_ratio)
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"[COUCHE-3 G-Substance] {result['verdict']} | {result}")
    # BLOCKING: FAIL -> non-zero -> workflow `continue` -> no WordPress, topic stays candidate.
    sys.exit(1 if result["verdict"] == "FAIL" else 0)


if __name__ == "__main__":
    main()
