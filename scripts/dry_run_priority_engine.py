"""Dry-run demonstration for the Task 4 priority-engine + cannibalization-gate
proposal (2026-07-19). Reads data/topic_registry.json and data/corpus_index.json
(both already checked into this branch), computes what PriorityScore and the
semantic-similarity gate WOULD have said about the most recently
selected/published/drafted/blocked topics. Makes NO network calls, NO WP
writes, NO changes to either input file. Safe to run repeatedly.

Uses tfidf_proxy_similarity() (see agents/_embedding_similarity.py) since no
OPENAI_API_KEY is available in this offline demo -- every proxy-derived line
in the output is labeled DEGRADED/PROXY so it isn't mistaken for a production-
accurate embedding score.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents._priority_score import compute_priority_score, factors_from_registry_entry
from agents._embedding_similarity import tfidf_proxy_similarity, PROXY_THRESHOLD

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_recent_topics(n=15):
    registry = json.loads((REPO_ROOT / "data" / "topic_registry.json").read_text())
    topics = registry.get("topics", [])
    with_activity = [t for t in topics if t.get("status") != "candidate"]

    def sort_key(t):
        return t.get("published_at") or t.get("drafted_at") or t.get("blocked_at") or t.get("selected_at") or ""
    with_activity.sort(key=sort_key, reverse=True)
    return with_activity[:n]


def main():
    corpus = json.loads((REPO_ROOT / "data" / "corpus_index.json").read_text())["posts"]
    corpus_titles = [p["title"] for p in corpus]

    recent = load_recent_topics(15)
    print(f"=== DRY-RUN: last {len(recent)} non-candidate topics from data/topic_registry.json ===")
    print(f"(corpus background: {len(corpus_titles)} published posts, data/corpus_index.json)")
    print(f"(similarity mode: tfidf_proxy_similarity -- DEGRADED, illustrative only, threshold={PROXY_THRESHOLD})")
    print()

    header = f"{'id':<45} {'status':<10} {'PriorityScore':<14} {'max_sim':<9} {'gate_verdict':<20}"
    print(header)
    print("-" * len(header))

    for t in recent:
        factors = factors_from_registry_entry(t)
        result = compute_priority_score(factors)
        title = t.get("title", "")
        # Exclude the topic's OWN eventual post from the comparison corpus --
        # otherwise every already-published/drafted topic trivially "matches"
        # itself at ~1.0, which tests nothing. The real question is: does
        # this topic resemble a DIFFERENT existing post.
        own_post_id = t.get("post_id")
        filtered = [(p["title"], p["post_id"]) for p in corpus if p["post_id"] != own_post_id]
        filtered_titles = [ft for ft, _ in filtered]
        scores = tfidf_proxy_similarity(title, filtered_titles) if filtered_titles else []
        if scores:
            max_sim = max(scores)
            best_idx = scores.index(max_sim)
            best_match_id = filtered[best_idx][1]
        else:
            max_sim, best_match_id = 0.0, None
        verdict = f"WOULD-FLAG vs {best_match_id}" if max_sim >= PROXY_THRESHOLD else "clear (proxy)"
        print(f"{t.get('id',''):<45} {t.get('status',''):<10} {result['score']:<14} {round(max_sim,3):<9} {verdict:<20}")

    print()
    print("=== Full PriorityScore breakdown for the single most recent topic ===")
    if recent:
        t = recent[0]
        factors = factors_from_registry_entry(t)
        result = compute_priority_score(factors)
        print(json.dumps({"topic_id": t.get("id"), **result}, indent=2))

    print()
    print("NOTE: no line above changes anything in data/topic_registry.json or on")
    print("WordPress. This script only reads and prints. See agent_01_seo_research.py's")
    print("PRIORITY_ENGINE_DRY_RUN hook for where this would eventually plug into the")
    print("real selection loop -- also log-only in this proposal, not applied.")


if __name__ == "__main__":
    main()
