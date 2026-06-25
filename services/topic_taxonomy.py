"""
NEXUS-14 V4 - services/topic_taxonomy.py (M7 - Topic Selection, structural)

Expert, knowledge-based taxonomy of HIGH-VALUE topics for newcomers to the
USA and Canada. This module encodes EDITORIAL knowledge, not live data: each
topic carries static, defensible scores for how essential it is to a newcomer
(newcomer_value) and how strong its commercial intent is (commercial_intent),
plus how durable / evergreen it is (evergreen). These are deliberately NOT
invented "search volume" or "trend" numbers -- those require a real data
source and are handled as documented integration points in topic_prioritizer.

WHY KNOWLEDGE-BASED, NOT DATA-BASED
The environment has no authorised live source for search volume, trends,
clicks/impressions, or affiliate-partner demand. Fabricating such numbers
would violate the project rule "do not simulate / do not fabricate results".
So this taxonomy ranks topics by editorial reasoning that can be reviewed and
audited, and leaves real-signal slots for prioritizer to fill when a source
is connected.

SCALE
All scores are floats in [0.0, 1.0]. 1.0 = maximal.
  newcomer_value    - how critical the topic is in a newcomer first months
  commercial_intent - how strongly the topic maps to monetisable products
  evergreen         - how stable the topic is over time (low churn = durable)

REGION
Each topic is tagged for "US", "CA", or "BOTH" so the prioritizer can target
the right audience.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class Topic:
    """A single newcomer topic with static, editorially-justified scores."""
    slug: str
    title: str
    region: str  # "US" | "CA" | "BOTH"
    newcomer_value: float
    commercial_intent: float
    evergreen: float
    keywords: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for name in ("newcomer_value", "commercial_intent", "evergreen"):
            v = getattr(self, name)
            if not (0.0 <= float(v) <= 1.0):
                raise ValueError(f"{name} for {self.slug!r} must be in [0,1]; got {v!r}")
        if self.region not in ("US", "CA", "BOTH"):
            raise ValueError(f"region for {self.slug!r} must be US/CA/BOTH; got {self.region!r}")


# ---------------------------------------------------------------------------
# AUTHORITATIVE TAXONOMY
# High-value newcomer topics for US & Canada. Scores reflect editorial
# judgement about first-months criticality and commercial intent, NOT live
# search data. Edit here to add/retune topics; prioritizer consumes this list.
# ---------------------------------------------------------------------------
NEWCOMER_TOPICS: List[Topic] = [
    Topic("open-bank-account-newcomer", "How to open a bank account as a newcomer",
          "BOTH", 0.98, 0.85, 0.95,
          ["newcomer bank account", "open checking account immigrant", "no SSN bank account"]),
    Topic("build-credit-score-newcomer", "How to build credit history from zero",
          "BOTH", 0.95, 0.90, 0.95,
          ["build credit newcomer", "first credit card immigrant", "credit score from scratch"]),
    Topic("get-ssn", "How to get a Social Security Number (SSN)",
          "US", 0.96, 0.40, 0.90,
          ["how to get SSN", "social security number newcomer", "SSN for immigrants"]),
    Topic("get-sin", "How to get a Social Insurance Number (SIN)",
          "CA", 0.96, 0.40, 0.90,
          ["how to get SIN", "social insurance number newcomer", "SIN application"]),
    Topic("international-money-transfer", "Cheapest ways to send money internationally",
          "BOTH", 0.88, 0.95, 0.90,
          ["send money abroad", "cheap international transfer", "best remittance newcomer"]),
    Topic("newcomer-credit-cards", "Best credit cards for newcomers",
          "BOTH", 0.82, 0.97, 0.85,
          ["best credit card newcomer", "no credit history card", "secured credit card"]),
    Topic("health-insurance-newcomer", "Health insurance for new arrivals",
          "BOTH", 0.90, 0.88, 0.88,
          ["newcomer health insurance", "health coverage immigrant", "private health insurance"]),
    Topic("file-taxes-first-year", "Filing taxes in your first year",
          "BOTH", 0.85, 0.60, 0.92,
          ["newcomer tax return", "first year taxes immigrant", "tax filing new resident"]),
    Topic("driver-license-newcomer", "How to get a driver license as a newcomer",
          "BOTH", 0.80, 0.45, 0.90,
          ["driver license newcomer", "exchange foreign license", "DMV new resident"]),
    Topic("rent-first-apartment", "Renting your first apartment with no local history",
          "BOTH", 0.83, 0.55, 0.85,
          ["rent apartment no credit", "newcomer rental guide", "first apartment immigrant"]),
    Topic("phone-plan-newcomer", "Best phone plans for new arrivals",
          "BOTH", 0.70, 0.80, 0.80,
          ["newcomer phone plan", "no credit phone plan", "prepaid SIM newcomer"]),
    Topic("car-insurance-newcomer", "Car insurance for newcomers",
          "BOTH", 0.74, 0.85, 0.85,
          ["car insurance newcomer", "auto insurance no history", "cheap car insurance immigrant"]),
]


def all_topics() -> List[Topic]:
    """Return the full authoritative topic list (a fresh list copy)."""
    return list(NEWCOMER_TOPICS)


def topics_for_region(region: str) -> List[Topic]:
    """Return topics relevant to a region; region "US"/"CA" includes BOTH."""
    if region not in ("US", "CA", "BOTH"):
        raise ValueError(f"region must be US/CA/BOTH; got {region!r}")
    if region == "BOTH":
        return all_topics()
    return [t for t in NEWCOMER_TOPICS if t.region in (region, "BOTH")]


def topic_by_slug(slug: str) -> Topic:
    """Look up a single topic by slug; raises KeyError if absent."""
    for t in NEWCOMER_TOPICS:
        if t.slug == slug:
            return t
    raise KeyError(slug)


def slugs() -> List[str]:
    """Return all topic slugs (stable order)."""
    return [t.slug for t in NEWCOMER_TOPICS]
