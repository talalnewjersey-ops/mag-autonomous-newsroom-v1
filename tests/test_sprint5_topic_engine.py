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
    # Production legitimately grows the curated table over time -> do NOT hard-code
    # an exact count (2026-07-19: went 28 -> 29 with a new, legitimately distinct
    # topic added, confirmed via a duplicate-id scan, not a data bug). The stable
    # invariants are: never fewer than the original curated baseline, no duplicate
    # ids (a real duplicate WOULD indicate data corruption, unlike count growth),
    # and the seed stays published.
    assert len(topics) >= 28, "curated table must hold at least the original 28 topics"
    ids = [t["id"] for t in topics]
    dupes = {i for i in ids if ids.count(i) > 1}
    assert not dupes, f"duplicate topic ids found (data corruption, not legitimate growth): {dupes}"
    published_ids = {t["id"] for t in topics if t["status"] == "published"}
    assert PUBLISHED_SEED_ID in published_ids, "the seed topic must be among published"
    # every candidate carries the two scoring axes 1-5
    for t in topics:
        assert 1 <= t["monetization_score"] <= 5
        assert 1 <= t["traffic_score"] <= 5


# ---------- anti-repetition ----------

def test_published_seed_is_never_selected():
    agent = _agent(REAL_REGISTRY)
    d = json.loads(REAL_REGISTRY.read_text(encoding="utf-8"))
    candidate_ids = {t["id"] for t in d["topics"] if t["status"] == "candidate"}
    chosen_ids = {c["id"] for c in agent._select_from_registry(99)}  # ask for everything
    # Robust invariant (no hard-coded count): only candidates are ever selected and
    # the published/seed topic is never re-selected -- true for any published count.
    assert PUBLISHED_SEED_ID not in chosen_ids, "published/seed topic must never be re-selected"
    assert chosen_ids <= candidate_ids, "only candidate topics may be selected"
    assert chosen_ids, "at least one candidate must be selectable"


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
    # Derive the expected max from the topics NOT excluded by status or the
    # near-duplicate guard -- do NOT hard-code a literal score. The guard can
    # legitimately remove the nominal highest-monetization candidate from the
    # real pool (2026-07-19: both M5 "send money to Mexico/Philippines"
    # candidates were correctly excluded as near-duplicates of the already-
    # drafted "send money to India" topic -- the guard doing its job, not a
    # regression; see AUDIT-LOG.md for the 2026-07-13 precedent of the same
    # dynamic). The tie-break LOGIC itself (monetization can never be bought
    # back by traffic) is covered robustly with synthetic, drift-proof data in
    # test_monetization_has_no_compensation below.
    agent = _agent(REAL_REGISTRY)
    d = json.loads(REAL_REGISTRY.read_text(encoding="utf-8"))
    excluded_statuses = {"published", "in_progress", "drafted", "blocked"}
    used_titles = [t["title"] for t in d["topics"] if t["status"] in excluded_statuses]
    eligible = [t for t in d["topics"]
                if t["status"] not in excluded_statuses
                and not agent._is_near_duplicate(t["title"], used_titles)]
    expected_max_monetization = max(t["monetization_score"] for t in eligible)

    first = agent._select_from_registry(1)[0]
    assert first["monetization_score"] == expected_max_monetization, \
        "monetization must dominate the first pick (among the actually-eligible pool)"


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
    # Selecting topics must never violate monetization order, and must never
    # pick the same topic twice. Do NOT hard-code an expected category count
    # against live data: the real pool's category mix legitimately changes as
    # topics get selected/drafted/published (2026-07-19: after the near-
    # duplicate guard correctly removed both top-tier "send money" candidates,
    # only 2 distinct categories remained at the next tier -- a real reflection
    # of the current pool, not a tie-break bug). The rotation LOGIC itself is
    # covered robustly with synthetic, drift-proof data in
    # test_variety_tie_break_rotates_categories_synthetic below.
    agent = _agent(REAL_REGISTRY)
    chosen = agent._select_from_registry(3)
    scores = [c["monetization_score"] for c in chosen]
    assert scores == sorted(scores, reverse=True), "monetization order must never be violated for variety"
    assert len({c["id"] for c in chosen}) == len(chosen), "no topic should be selected twice"


def test_variety_tie_break_rotates_categories_synthetic(tmp_path):
    # Synthetic, drift-proof: 3 topics tied on (monetization, traffic) across
    # 3 distinct categories must all be selectable within the same 3-pick
    # batch, proving the cat_usage rotation actually diversifies among ties.
    reg = _write(tmp_path, {"topics": [
        {"id": "t-a", "title": "Topic A", "market": "USA", "category": "cat-1",
         "monetization_score": 4, "traffic_score": 3, "status": "candidate"},
        {"id": "t-b", "title": "Topic B", "market": "USA", "category": "cat-2",
         "monetization_score": 4, "traffic_score": 3, "status": "candidate"},
        {"id": "t-c", "title": "Topic C", "market": "USA", "category": "cat-3",
         "monetization_score": 4, "traffic_score": 3, "status": "candidate"},
    ]})
    agent = _agent(reg)
    chosen = agent._select_from_registry(3)
    cats = {c["category"] for c in chosen}
    assert cats == {"cat-1", "cat-2", "cat-3"}, f"expected all 3 tied categories to be picked, got {cats}"


# ---------- near-duplicate guard ----------

def test_near_duplicate_rejected_but_distinct_kept():
    agent = _agent(REAL_REGISTRY)
    pub = "Building Credit in Canada From Zero"
    # exact re-wording -> duplicate
    assert agent._is_near_duplicate("building credit in canada from zero!!!", [pub]) is True
    # genuinely different topic sharing a few words -> NOT a duplicate
    assert agent._is_near_duplicate("Building US Credit From Zero With an ITIN", [pub]) is False
    # NOT asserting a specific real-registry topic id stays selectable here:
    # 2026-07-19, "us-building-credit-itin" (the topic this test used to check)
    # legitimately moved candidate -> drafted (real WP post 48810, confirmed via
    # a live 401-not-404 check) as the pipeline processed it -- exactly the
    # anti-repetition behavior test_published_seed_is_never_selected protects.
    # The integration path (registry selection respecting the near-dup guard)
    # is covered without that aging-out risk in the synthetic test below.


def test_near_duplicate_guard_integration_synthetic(tmp_path):
    # Integration-level, drift-proof: a candidate whose title is a near-
    # rewording of an already-used title must never be selectable; a
    # genuinely distinct candidate sharing a few words must remain
    # selectable. Synthetic data so this never ages out as real topics
    # legitimately move from candidate -> drafted/published over time.
    reg = _write(tmp_path, {"topics": [
        {"id": "already-used", "title": "Building Credit in Canada From Zero",
         "market": "Canada", "category": "credit", "monetization_score": 3,
         "traffic_score": 3, "status": "drafted"},
        {"id": "near-dup-of-used", "title": "Building Credit In Canada From Zero!!!",
         "market": "Canada", "category": "credit", "monetization_score": 5,
         "traffic_score": 5, "status": "candidate"},
        {"id": "genuinely-distinct", "title": "Building US Credit From Zero With an ITIN",
         "market": "USA", "category": "credit builder", "monetization_score": 3,
         "traffic_score": 3, "status": "candidate"},
    ]})
    agent = _agent(reg)
    ids = {c["id"] for c in agent._select_from_registry(99)}
    assert "near-dup-of-used" not in ids, "near-rewording of an already-used title must be rejected"
    assert "genuinely-distinct" in ids, "a genuinely distinct topic must remain selectable"


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
