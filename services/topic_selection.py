#!/usr/bin/env python3
"""
NEXUS-14 V4: Topic selection bridge (M7 integration).

This module connects the deterministic, knowledge-based topic prioritizer
(services.topic_prioritizer) to the production pipeline. The orchestrator
discovers and validates topics as plain dicts (each carrying at least a
"keyword"). Here we map those validated dicts onto the auditable editorial
scores from the newcomer US/CA taxonomy and reorder them so the highest
value newcomer topics are produced first.

Honest data boundary (unchanged from M7):
  * Ranking uses STATIC editorial scores only. No live search volume,
    trend, click, impression or affiliate metrics are fabricated.
  * Validated topics that are NOT present in the taxonomy are never
    dropped; they keep their original relative order and are placed after
    the taxonomy-matched topics (stable fallback).
  * A LiveSignalsProvider may be passed through to the prioritizer when an
    authorised real data source exists; absent one, it contributes nothing.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.topic_taxonomy import Topic, all_topics
from services.topic_prioritizer import (
    LiveSignalsProvider,
    ScoredTopic,
    score_topic,
)


# Sentinel score for validated topics with no taxonomy match. Strictly
# below the clamped [0, 1] range so unmatched topics always sort last
# while never being removed from the batch.
_UNMATCHED_SCORE: float = -1.0


def _normalize(text: Any) -> str:
    'Lowercase + trim a value for tolerant keyword/slug/title matching.'
    if text is None:
        return ""
    return str(text).strip().lower()


def _build_score_index(
    provider: Optional[LiveSignalsProvider] = None,
) -> Dict[str, float]:
    """Map normalized slug / title / keyword -> static M7 score.

    Every taxonomy Topic is scored once via score_topic(). All of its
    lookup handles (slug, title and each declared keyword) point at that
    single score so the orchestrator can match on whatever string it has.
    On a key collision the higher score wins (deterministic).
    """
    index: Dict[str, float] = {}
    for topic in all_topics():
        live = provider.signals_for(topic.slug) if provider is not None else None
        scored: ScoredTopic = score_topic(topic, live)
        handles = [topic.slug, topic.title, *topic.keywords]
        for handle in handles:
            key = _normalize(handle)
            if not key:
                continue
            if key not in index or scored.score > index[key]:
                index[key] = scored.score
    return index


def _match_score(
    validated: Dict[str, Any],
    index: Dict[str, float],
) -> float:
    """Best static score for a single validated-topic dict.

    Tries the dict keyword, then slug, then title. Returns _UNMATCHED_SCORE
    when none of them is present in the taxonomy index.
    """
    for field in ("keyword", "slug", "title"):
        key = _normalize(validated.get(field))
        if key and key in index:
            return index[key]
    return _UNMATCHED_SCORE


def score_validated_topics(
    topics: List[Dict[str, Any]],
    provider: Optional[LiveSignalsProvider] = None,
) -> List[Dict[str, Any]]:
    """Annotate each validated topic with its static M7 priority score.

    Returns NEW dicts (originals untouched) each carrying:
      * m7_score: float  (taxonomy score, or _UNMATCHED_SCORE)
      * m7_matched: bool (whether it was found in the taxonomy)
    Input order is preserved.
    """
    index = _build_score_index(provider)
    annotated: List[Dict[str, Any]] = []
    for topic in topics:
        score = _match_score(topic, index)
        enriched = dict(topic)
        enriched["m7_score"] = score
        enriched["m7_matched"] = score > _UNMATCHED_SCORE
        annotated.append(enriched)
    return annotated


def prioritize_validated_topics(
    topics: List[Dict[str, Any]],
    provider: Optional[LiveSignalsProvider] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Reorder validated topics by M7 score, highest first (stable).

    * Taxonomy-matched topics come first, ordered by descending static
      score; ties keep their original relative order (stable sort).
    * Unmatched topics keep their original relative order and follow the
      matched ones (never dropped).
    * Pass limit to return only the top N after reordering.
    * Safe on empty input. A non-positive limit yields an empty list.
    """
    annotated = score_validated_topics(topics, provider)
    indexed = list(enumerate(annotated))
    indexed.sort(key=lambda pair: (-pair[1]["m7_score"], pair[0]))
    ordered = [item for _, item in indexed]
    if limit is not None:
        if limit <= 0:
            return []
        return ordered[:limit]
    return ordere
