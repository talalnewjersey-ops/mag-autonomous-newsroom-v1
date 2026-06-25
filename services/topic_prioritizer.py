"""
NEXUS-14 V4 - services/topic_prioritizer.py (M7 - Topic Selection, scoring)

Deterministic, offline scoring engine that ranks newcomer topics. It combines
STATIC editorial scores from topic_taxonomy (newcomer_value, commercial_intent,
evergreen) with OPTIONAL live signals (search demand, trend, affiliate-partner
demand) that are injected from outside -- never fabricated here.

HONEST DATA BOUNDARY
This project has no authorised live data source for search volume, trends,
clicks/impressions, or affiliate demand. Per the project rule "do not simulate
/ do not fabricate", this module NEVER invents those numbers. Instead it exposes
a LiveSignals slot. When a signal is absent (None), the score falls back to the
static editorial signals only, and the result records which signals were real.
A LiveSignalsProvider Protocol documents the integration point an authorised
data source (e.g. Search Console export, a trends API) would implement later.

WEIGHTING (recommended defaults, retunable)
Rationale: durable real-world usefulness to a newcomer is weighted highest,
because without a live trend feed, evergreen newcomer-critical topics are the
most reliable source of sustained traffic and revenue. Commercial intent comes
next (it is what converts), then evergreen stability. Live signals, when
present, ADD to the score but cannot by themselves dominate a low-value topic.

  newcomer_value     0.34
  commercial_intent  0.26
  evergreen          0.15
  search_demand      0.13  (live, optional)
  trend              0.07  (live, optional)
  affiliate_demand   0.05  (live, optional)

All component scores are in [0,1]; the composite is in [0,1].
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Protocol

from services.topic_taxonomy import Topic, topics_for_region


# ---------------------------------------------------------------------------
# WEIGHTS - single source of truth for the composite. Must sum to 1.0.
# ---------------------------------------------------------------------------
WEIGHTS: Dict[str, float] = {
    "newcomer_value": 0.34,
    "commercial_intent": 0.26,
    "evergreen": 0.15,
    "search_demand": 0.13,
    "trend": 0.07,
    "affiliate_demand": 0.05,
}

assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "WEIGHTS must sum to 1.0"


@dataclass(frozen=True)
class LiveSignals:
    """Optional, externally-supplied real signals for one topic.

    Every field defaults to None meaning "no real data available". Values, when
    supplied, MUST be floats in [0,1] derived from a real source -- never
    fabricated. None is treated as a neutral 0.0 contribution, and the topic
    is ranked on its static editorial merit alone.
    """
    search_demand: Optional[float] = None
    trend: Optional[float] = None
    affiliate_demand: Optional[float] = None


class LiveSignalsProvider(Protocol):
    """Integration point for a future authorised data source.

    An implementation would map a topic slug to real LiveSignals built from an
    authorised export/API (Search Console, a trends service, an affiliate
    network feed). No implementation ships here on purpose: there is no
    authorised live source connected, and inventing one is forbidden.
    """

    def signals_for(self, slug: str) -> LiveSignals:
        ...


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else float(x)


@dataclass(frozen=True)
class ScoredTopic:
    """A topic plus its composite score and provenance of the inputs."""
    slug: str
    title: str
    region: str
    score: float
    used_live_signals: List[str]  # which live signals were real (non-None)


def score_topic(topic: Topic, live: Optional[LiveSignals] = None) -> ScoredTopic:
    """Compute the composite score for a single topic.

    Static signals always contribute. Live signals contribute only when the
    caller supplies real values; absent (None) live signals contribute 0 and
    are NOT counted as used.
    """
    live = live or LiveSignals()
    used: List[str] = []

    def live_val(name: str) -> float:
        v = getattr(live, name)
        if v is None:
            return 0.0
        used.append(name)
        return _clamp01(v)

    score = (
        WEIGHTS["newcomer_value"] * _clamp01(topic.newcomer_value)
        + WEIGHTS["commercial_intent"] * _clamp01(topic.commercial_intent)
        + WEIGHTS["evergreen"] * _clamp01(topic.evergreen)
        + WEIGHTS["search_demand"] * live_val("search_demand")
        + WEIGHTS["trend"] * live_val("trend")
        + WEIGHTS["affiliate_demand"] * live_val("affiliate_demand")
    )
    return ScoredTopic(
        slug=topic.slug,
        title=topic.title,
        region=topic.region,
        score=round(_clamp01(score), 6),
        used_live_signals=used,
    )


def prioritize(
    region: str = "BOTH",
    provider: Optional[LiveSignalsProvider] = None,
    limit: Optional[int] = None,
) -> List[ScoredTopic]:
    """Rank topics for a region, highest score first.

    If a provider is supplied it is queried for real signals per slug; otherwise
    ranking uses static editorial signals only. Ties break by slug for a stable,
    deterministic order. Pass limit to return only the top N.
    """
    scored: List[ScoredTopic] = []
    for t in topics_for_region(region):
        live = provider.signals_for(t.slug) if provider is not None else None
        scored.append(score_topic(t, live))
    scored.sort(key=lambda s: (-s.score, s.slug))
    if limit is not None:
        if limit < 0:
            raise ValueError("limit must be >= 0")
        scored = scored[:limit]
    return scored


def top_topic(region: str = "BOTH",
              provider: Optional[LiveSignalsProvider] = None) -> ScoredTopic:
    """Convenience: the single highest-ranked topic for a region."""
    ranked = prioritize(region, provider=provider, limit=1)
    if not ranked:
        raise LookupError(f"no topics for region {region!r}")
    return ranked[0]
