#!/usr/bin/env python3
"""
NEXUS-14 - Agent 17 Observation Dashboard (Etape 1 - Observation Mode)

PURELY INFORMATIONAL. Read-only post-processing. Never blocks, never writes
to WordPress, never modifies production. Aggregates Agent 17
cannibalization_report.json files produced by runs and emits an observation
dashboard (JSON, optional HTML).

Per-observation record kept for future false-positive analysis:
{
  "run_id": "...",
  "article_title": "...",
  "article_country": "...",
  "decision": "...",
  "would_block": true,
  "max_combined_score": 0.91
}

Step-2 eligibility (DISPLAY ONLY - never auto-activates anything):
  >= 6 real runs
  >= 15 articles observed
  false_positive_rate < 5%
  >= 80% true duplicates
  all would_block cases reviewed
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


def _country_of(report):
    obs = report.get("observation", {}) or {}
    cs = obs.get("country_signals", {}) or {}
    if cs.get("usa") and not cs.get("canada"):
        return "USA"
    if cs.get("canada") and not cs.get("usa"):
        return "CANADA"
    if cs.get("usa") and cs.get("canada"):
        return "BOTH"
    return "UNKNOWN"


def _run_id_of(report):
    return (report.get("__source_file", "") or "").split(os.sep)[0] or report.get("run_id", "unknown")


def build_observations(reports):
    observations = []
    for r in reports:
        obs = r.get("observation", {}) or {}
        observations.append({
            "run_id": r.get("run_id") or _run_id_of(r),
            "article_title": r.get("new_topic", ""),
            "article_country": _country_of(r),
            "decision": r.get("decision", "UNKNOWN"),
            "would_block": bool(obs.get("would_block", r.get("blocking", False))),
            "max_combined_score": float(obs.get("max_combined_score", 0.0) or 0.0),
            "slug_collisions": obs.get("slug_collisions", []),
            "search_intent": obs.get("search_intent", {}),
        })
    return observations


def summarize(observations):
    run_ids = {o["run_id"] for o in observations}
    articles = len(observations)
    would_block = sum(1 for o in observations if o["would_block"])
    slug_collisions = sum(1 for o in observations if o.get("slug_collisions"))
    intent_conflicts = sum(
        1 for o in observations
        if (o.get("search_intent") or {}).get("similarity", 0) >= 0.72
    )
    # "confirmed duplicates" and "false positives" require human verdict; until
    # provided we report would_block as candidates and leave verdicts unknown.
    confirmed_duplicates = sum(
        1 for o in observations if str(o.get("human_verdict", "")).lower() == "duplicate"
    )
    false_positives = sum(
        1 for o in observations
        if o["would_block"] and str(o.get("human_verdict", "")).lower() == "not_duplicate"
    )
    reviewed = sum(1 for o in observations if o.get("human_verdict"))
    fp_rate = (false_positives / would_block) if would_block else 0.0
    true_dup_rate = (confirmed_duplicates / would_block) if would_block else 0.0

    eligibility = {
        "runs_ok": len(run_ids) >= 6,
        "articles_ok": articles >= 15,
        "fp_rate_ok": fp_rate < 0.05,
        "true_dup_ok": true_dup_rate >= 0.80,
        "all_would_block_reviewed": reviewed >= would_block,
    }
    eligible = all(eligibility.values())

    return {
        "runs_observed": len(run_ids),
        "articles_analyzed": articles,
        "would_block_count": would_block,
        "confirmed_duplicates": confirmed_duplicates,
        "false_positives": false_positives,
        "false_positive_rate": round(fp_rate, 4),
        "slug_collisions": slug_collisions,
        "intent_conflicts": intent_conflicts,
        "step2_eligibility_criteria": eligibility,
        "step2_eligible": eligible,
        "note": "DISPLAY ONLY - human decision required. Nothing is activated automatically.",
    }


def main():
    parser = argparse.ArgumentParser(description="Agent 17 Observation Dashboard (read-only)")
    parser.add_argument("--reports", nargs="+",
                        default=["output/**/agent_17/cannibalization_report.json"],
                        help="Glob pattern(s) for cannibalization_report.json files")
    parser.add_argument("--output", default="output/agent17_observation/dashboard.json")
    args = parser.parse_args()

    reports = _load_reports(args.reports)
    observations = build_observations(reports)
    summary = summarize(observations)

    dashboard = {
        "generated_at": datetime.utcnow().isoformat(),
        "mode": "observe_only",
        "summary": summary,
        "observations": observations,
    }

    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(dashboard, f, indent=2)

    print("=" * 60)
    print("AGENT 17 OBSERVATION DASHBOARD (informational)")
    print("=" * 60)
    print(f"Runs observed      : {summary['runs_observed']}")
    print(f"Articles analyzed  : {summary['articles_analyzed']}")
    print(f"would_block        : {summary['would_block_count']}")
    print(f"Confirmed dupes    : {summary['confirmed_duplicates']}")
    print(f"False positives    : {summary['false_positives']} (rate {summary['false_positive_rate']})")
    print(f"Slug collisions    : {summary['slug_collisions']}")
    print(f"Intent conflicts   : {summary['intent_conflicts']}")
    print(f"Step-2 eligible    : {summary['step2_eligible']} (display only)")
    print(f"Dashboard saved    : {args.output}")


if __name__ == "__main__":
    main()
