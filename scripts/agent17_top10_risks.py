#!/usr/bin/env python3
"""
NEXUS-14 - Agent 17 Top 10 Highest-Risk Conflicts (Etape 1 - Observation Mode)

PURELY INFORMATIONAL. Read-only post-processing. Never blocks, never writes to
WordPress, never modifies production. Ranks observed conflicts by risk and
emits a Top-10 report with an EMPTY "human_verdict" column for manual review.

Columns kept:
  combined_score
  search_intent_similarity
  slug_collision
  same_country
  would_block
  human_verdict   (left empty on purpose)
"""

import argparse
import glob
import json
import os
from datetime import datetime


def _load_reports(paths):
    reports = []
    for pattern in paths:
        for fp in glob.glob(pattern, recursive=True):
            if not fp.endswith(".json"):
                continue
            try:
                with open(fp, "r") as f:
                    data = json.load(f)
                data["__source_file"] = fp
                reports.append(data)
            except Exception as e:
                print(f"[WARN] could not parse {fp}: {e}")
    return reports


def _same_country(report, conflict):
    obs = report.get("observation", {}) or {}
    cs = obs.get("country_signals", {}) or {}
    new_country = "USA" if cs.get("usa") else ("CANADA" if cs.get("canada") else "UNKNOWN")
    c_country = conflict.get("country", "UNKNOWN")
    return new_country != "UNKNOWN" and new_country == c_country


def build_rows(reports):
    rows = []
    for r in reports:
        obs = r.get("observation", {}) or {}
        si = obs.get("search_intent", {}) or {}
        topic = r.get("new_topic", "")
        slug_collisions = obs.get("slug_collisions", []) or []
        # Each conflict found becomes a candidate row
        for c in (r.get("conflicts_found", []) or []):
            rows.append({
                "new_topic": topic,
                "conflicting_title": c.get("title", ""),
                "combined_score": float(c.get("combined_score", 0.0) or 0.0),
                "search_intent_similarity": float(si.get("similarity", 0.0) or 0.0),
                "slug_collision": bool(slug_collisions),
                "same_country": _same_country(r, c),
                "would_block": bool(obs.get("would_block", r.get("blocking", False))),
                "human_verdict": "",
            })
        # If no conflicts but would_block measured, still surface the topic
        if not (r.get("conflicts_found") or []):
            rows.append({
                "new_topic": topic,
                "conflicting_title": "",
                "combined_score": float(obs.get("max_combined_score", 0.0) or 0.0),
                "search_intent_similarity": float(si.get("similarity", 0.0) or 0.0),
                "slug_collision": bool(slug_collisions),
                "same_country": False,
                "would_block": bool(obs.get("would_block", r.get("blocking", False))),
                "human_verdict": "",
            })
    return rows


def rank(rows):
    def risk_key(row):
        return (
            row["would_block"],
            row["combined_score"],
            row["search_intent_similarity"],
            row["slug_collision"],
            row["same_country"],
        )
    return sorted(rows, key=risk_key, reverse=True)[:10]


def main():
    parser = argparse.ArgumentParser(description="Agent 17 Top-10 highest-risk conflicts (read-only)")
    parser.add_argument("--reports", nargs="+",
                        default=["output/**/agent_17/cannibalization_report.json"])
    parser.add_argument("--output", default="output/agent17_observation/top10_risks.json")
    args = parser.parse_args()

    reports = _load_reports(args.reports)
    rows = build_rows(reports)
    top10 = rank(rows)

    out = {
        "generated_at": datetime.utcnow().isoformat(),
        "mode": "observe_only",
        "columns": [
            "combined_score", "search_intent_similarity", "slug_collision",
            "same_country", "would_block", "human_verdict",
        ],
        "top_10": top10,
        "note": "human_verdict intentionally empty - manual review required.",
    }

    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(out, f, indent=2)

    print("=" * 60)
    print("AGENT 17 - TOP 10 HIGHEST-RISK CONFLICTS (informational)")
    print("=" * 60)
    print(f"{'#':<3}{'score':<8}{'intent':<8}{'slug':<6}{'ctry':<6}{'block':<6}verdict")
    for i, row in enumerate(top10, 1):
        print(f"{i:<3}{row['combined_score']:<8.3f}{row['search_intent_similarity']:<8.3f}"
              f"{str(row['slug_collision']):<6}{str(row['same_country']):<6}"
              f"{str(row['would_block']):<6}{row['human_verdict'] or '(empty)'}")
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
