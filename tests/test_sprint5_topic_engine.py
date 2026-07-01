"""Sprint 5 — curated topic engine (agent_01) tests. No network, no API key.

Guarantees:
- registry integrity (28 topics, exactly 1 published seed)
- lexicographic priority monetization > traffic > variety, NO compensation
- never selects a published/in_progress topic (anti-repetition)
- near-duplicate guard rejects re-wordings but keeps genuinely distinct topics
- commit-back marks a picked topic in_progress so it is not re-selected
- output schema stays compatible with Agents 02-18
- manual --topic override bypasses the registry entirely
"""
import asyncio
import json
import shutil
from pathlib import Path

import pytest

from agents.agent_01_seo_research import SEOResearchAgent

REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_REGISTRY = REPO_ROOT / "data" / "topic_registry.json"
PUBLISHED_SEED_ID = "ca-building-credit-from-zero"


def _agent(registry_path):
    a = SEOResearchAgent(config={})
    a.registry_path = str(registry_path)
    return a


def _write(tmp_path, registry: dict) -> Path:
    p = tmp_path / "reg.json"
    p.write_text(json.dumps(registry), encoding="utf-8")
    return p


# ---------- registry integrity ----------

def test_registry_file_valid_28_topics_one_published():
    d = json.loads(REAL_REGISTRY.read_text(encoding="utf-8"))
    topics = d["topics"]
    assert len(topics) == 28, "curated table must hold 28 topics"
    published = [t for t in topics if t["status"] == "published"]
    assert len(published) == 1, "exactly one seed topic must be pre-marked published"
    assert published[0]["id"] == PUBLISHED_SEED_ID
    # every candidate carries the two scoring axes 1-5
    for t in topics:
        assert 1 <= t["monetization_score"] <= 5
        assert 1 <= t["traffic_score"] <= 5


# ---------- anti-repetition ----------

def test_published_seed_is_never_selected():
    agent = _agent(REAL_REGISTRY)
    chosen = agent._select_from_registry(99)  # ask for everything
    ids = {c["id"] for c in chosen}
    assert PUBLISHED_SEED_ID not in ids, "published topic must never be re-selected"
    assert len(chosen) == 27, "27 candidates remain after the 1 published seed"


def test_mark_selected_persists_and_excludes_next_run(tmp_path):
    reg = tmp_path / "reg.json"
    shutil.copy(REAL_REGISTRY, reg)
    agent = _agent(reg)

    first = agent._select_from_registry(1)
    first_id = first[0]["id"]
    agent._mark_selected([first_id])

    # persisted as in_progress
    saved = json.loads(reg.read_text(encoding="utf-8"))
    entry = next(t for t in saved["topics"] if t["id"] == first_id)
    assert entry["status"] == "in_progress"
    assert "selected_at" in entry

    # a fresh selection (new run) must NOT return the same topic
    second = agent._select_from_registry(1)
    assert second[0]["id"] != first_id


# ---------- lexicographic priority (monetization > traffic > variety) ----------

def test_first_pick_is_highest_monetization_then_traffic():
    agent = _agent(REAL_REGISTRY)
    first = agent._select_from_registry(1)[0]
    assert first["monetization_score"] == 5, "monetization must dominate the first pick"
    assert first["traffic_score"] == 5, "among M5, highest traffic wins"


def test_monetization_has_no_compensation(tmp_path):
    # M5/T1 must beat M3/T5 — traffic can never buy back monetization.
    reg = _write(tmp_path, {"topics": [
        {"id": "low-money-high-traffic", "title": "High Traffic Cheap", "market": "USA",
         "category": "x", "monetization_score": 3, "traffic_score": 5, "status": "candidate"},
        {"id": "high-money-low-traffic", "title": "High Money Rare", "market": "USA",
         "category": "y", "monetization_score": 5, "traffic_score": 1, "status": "candidate"},
    ]})
    agent = _agent(reg)
    first = agent._select_from_registry(1)[0]
    assert first["id"] == "high-money-low-traffic"


def test_variety_breaks_ties_three_distinct_categories():
    # Selecting 3 topics should surface >=3 distinct categories (blueprint matrix),
    # achieved purely as a tie-breaker without violating monetization order.
    agent = _agent(REAL_REGISTRY)
    chosen = agent._select_from_registry(3)
    cats = {c["category"] for c in chosen}
    assert len(cats) >= 3, f"expected >=3 distinct categories, got {cats}"
    # and monetization is non-increasing across the ordered picks
    scores = [c["monetization_score"] for c in chosen]
    assert scores == sorted(scores, reverse=True)


# ---------- near-duplicate guard ----------

def test_near_duplicate_rejected_but_distinct_kept():
    agent = _agent(REAL_REGISTRY)
    pub = "Building Credit in Canada From Zero"
    # exact re-wording -> duplicate
    assert agent._is_near_duplicate("building credit in canada from zero!!!", [pub]) is True
    # genuinely different topic sharing a few words -> NOT a duplicate
    assert agent._is_near_duplicate("Building US Credit From Zero With an ITIN", [pub]) is False
    # and the ITIN topic is actually selectable from the real registry
    ids = {c["id"] for c in agent._select_from_registry(99)}
    assert "us-building-credit-itin" in ids


# ---------- output schema ----------

def test_selected_topic_matches_downstream_schema():
    agent = _agent(REAL_REGISTRY)
    entry = agent._select_from_registry(1)[0]
    topic = agent._registry_to_topic(entry)
    for field in ("keyword", "title", "market", "priority_score", "content_suitable", "validated"):
        assert field in topic
    assert topic["source"] == "topic_registry"
    assert topic["monetization_score"] == entry["monetization_score"]
    assert topic["priority_score"] == entry["monetization_score"] * 10 + entry["traffic_score"]


# ---------- manual override still works and never mutates the registry ----------

def test_topic_override_bypasses_and_preserves_registry(tmp_path):
    reg = tmp_path / "reg.json"
    shutil.copy(REAL_REGISTRY, reg)
    before = reg.read_text(encoding="utf-8")
    agent = _agent(reg)
    out = asyncio.run(agent.run(
        max_topics=1,
        output_path=str(tmp_path / "topics.json"),
        topic_override="Custom Manual Topic",
    ))
    assert out["research_mode"] == "manual_override"
    assert out["topics"][0]["keyword"] == "Custom Manual Topic"
    assert reg.read_text(encoding="utf-8") == before, "override must not touch the registry"


def test_dry_run_selects_without_mutating(tmp_path):
    reg = tmp_path / "reg.json"
    shutil.copy(REAL_REGISTRY, reg)
    before = reg.read_text(encoding="utf-8")
    agent = _agent(reg)
    out = asyncio.run(agent.run(
        max_topics=1,
        output_path=str(tmp_path / "topics.json"),
        dry_run=True,
    ))
    assert out["research_mode"] == "topic_registry"
    assert reg.read_text(encoding="utf-8") == before, "dry-run must not mutate the registry"
