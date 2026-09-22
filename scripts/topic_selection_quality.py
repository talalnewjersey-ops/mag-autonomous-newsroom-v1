#!/usr/bin/env python3
"""
Topic Selection Quality & Production Throttle
NEXUS-14 Pipeline — Priority 5

PURPOSE
-------
Enforce the production policy:
  * Up to SIX articles per day is a hard CEILING — never a quota.
  * No filler: a slot is only filled if a topic genuinely passes ALL
    validation gates. Unused slots stay empty rather than being padded.
  * No gate bypass and no lowering of EEAT / originality / SEO thresholds.
  * Prefer high-value topics in the priority clusters (search traffic,
    topical authority, affiliate opportunity, long-term Google visibility).

This module is DETERMINISTIC and ADVISORY for *ordering*, but AUTHORITATIVE
for *eligibility*: a topic that fails any required gate is never selected,
regardless of its score. It selects from already-validated candidates; it
does NOT itself relax or re-run quality gates.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# Hard production ceiling. A maximum, never a target to "fill".
MAX_ARTICLES_PER_DAY = 6
MAX_PILLAR_PER_DAY = 2

# Priority clusters (kept at the top of selection ordering). Order matters:
# earlier clusters are weighted higher for tie-breaking.
PRIORITY_CLUSTERS = [
    "car_insurance",
    "banking",
    "credit_cards",
    "credit_building",
    "money_transfers",
    "taxes",
    "health_insurance",
    "first_90_days",
    "driver_license",
]

# Gates that MUST pass for a topic to be eligible. These mirror the pipeline's
# blocking gates; this module never overrides them.
REQUIRED_GATES = [
    "eeat_pass",            # EEAT >= 90
    "seo_pass",             # SEO >= 90
    "originality_pass",     # Gate 20 (when in block mode) / Agent 17 advisory
    "cannibalization_pass", # Agent 17 deterministic
    "country_category_pass",# Gate 19
    "fact_check_pass",
    "word_count_pass",
    "affiliate_compliance_pass",
]


@dataclass
class TopicCandidate:
    """A pre-validated topic candidate proposed by upstream agents."""
    topic: str
    cluster: str
    article_type: str = "STANDARD"  # PILLAR / STANDARD / OPPORTUNITY
    # Component scores (0-100) from the balanced scoring model.
    user_value: float = 0.0          # 40%
    commercial_intent: float = 0.0   # 25%
    search_demand: float = 0.0       # 15%
    affiliate_opportunity: float = 0.0  # 10%
    strategic_authority: float = 0.0    # 10%
    # Gate results: gate name -> bool.
    gates: Dict[str, bool] = field(default_factory=dict)

    def balanced_score(self) -> float:
        return (
            0.40 * self.user_value
            + 0.25 * self.commercial_intent
            + 0.15 * self.search_demand
            + 0.10 * self.affiliate_opportunity
            + 0.10 * self.strategic_authority
        )

    def is_eligible(self) -> bool:
        """Eligible only if EVERY required gate explicitly passed."""
        return all(self.gates.get(g, False) for g in REQUIRED_GATES)

    def failed_gates(self) -> List[str]:
        return [g for g in REQUIRED_GATES if not self.gates.get(g, False)]

    def cluster_rank(self) -> int:
        c = (self.cluster or "").strip().lower().replace(" ", "_").replace("-", "_")
        return PRIORITY_CLUSTERS.index(c) if c in PRIORITY_CLUSTERS else len(PRIORITY_CLUSTERS)


def select(
    candidates: List[TopicCandidate],
    max_per_day: int = MAX_ARTICLES_PER_DAY,
    max_pillar: int = MAX_PILLAR_PER_DAY,
) -> Dict:
    """Select up to max_per_day eligible topics.

    Ordering: priority cluster first, then balanced score desc, then topic
    name for stable determinism. ONLY eligible (all-gates-pass) topics are
    selectable. If fewer than max_per_day are eligible, fewer are selected —
    slots are NEVER padded with filler.
    """
    eligible = [c for c in candidates if c.is_eligible()]
    rejected = [
        {"topic": c.topic, "cluster": c.cluster, "failed_gates": c.failed_gates()}
        for c in candidates if not c.is_eligible()
    ]

    # Deterministic ordering.
    eligible.sort(key=lambda c: (c.cluster_rank(), -c.balanced_score(), c.topic))

    selected: List[TopicCandidate] = []
    pillar_count = 0
    for c in eligible:
        if len(selected) >= max_per_day:
            break
        if c.article_type.upper() == "PILLAR":
            if pillar_count >= max_pillar:
                continue
            pillar_count += 1
        selected.append(c)

    return {
        "policy": {
            "max_articles_per_day": max_per_day,
            "max_pillar_per_day": max_pillar,
            "ceiling_not_quota": True,
            "no_filler": True,
            "no_gate_bypass": True,
        },
        "counts": {
            "candidates": len(candidates),
            "eligible": len(eligible),
            "selected": len(selected),
            "rejected": len(rejected),
            "unused_slots": max(0, max_per_day - len(selected)),
        },
        "selected": [
            {
                "topic": c.topic,
                "cluster": c.cluster,
                "article_type": c.article_type,
                "balanced_score": round(c.balanced_score(), 2),
                "cluster_rank": c.cluster_rank(),
            }
            for c in selected
        ],
        "rejected": rejected,
    }


def _load(path: str) -> List[TopicCandidate]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    out = []
    for d in data:
        out.append(TopicCandidate(
            topic=d["topic"],
            cluster=d.get("cluster", ""),
            article_type=d.get("article_type", "STANDARD"),
            user_value=float(d.get("user_value", 0)),
            commercial_intent=float(d.get("commercial_intent", 0)),
            search_demand=float(d.get("search_demand", 0)),
            affiliate_opportunity=float(d.get("affiliate_opportunity", 0)),
            strategic_authority=float(d.get("strategic_authority", 0)),
            gates=d.get("gates", {}),
        ))
    return out


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Topic selection with quality ceiling")
    p.add_argument("--candidates", required=True, help="JSON list of validated candidates")
    p.add_argument("--max-per-day", type=int, default=MAX_ARTICLES_PER_DAY)
    p.add_argument("--max-pillar", type=int, default=MAX_PILLAR_PER_DAY)
    p.add_argument("--output", help="Path to write JSON result (default stdout)")
    args = p.parse_args(argv)

    result = select(_load(args.candidates), args.max_per_day, args.max_pillar)
    out = json.dumps(result, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
