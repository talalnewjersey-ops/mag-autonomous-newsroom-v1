#!/usr/bin/env python3
"""
NEXUS-14 V4 - Agent 17: Semantic Content Cannibalization Engine
MoneyAbroadGuide.com | Prevents duplicate / cannibalizing content before production.

V4 CHANGES (M4 — Cannibalization Engine)
  * Observe-only mode is OFF by default. Agent 17 is now a BLOCKING gate.
      - AGENT17_OBSERVE_ONLY defaults to "false". Set to "true" ONLY in staging.
  * Semantic similarity via embeddings (services.embeddings_service), replacing
    the old title-only difflib heuristic.
  * Five weighted signals: title, slug, keyword, search-intent, semantic.
  * Decisions: ALLOW | CANONICAL | MERGE | HUMAN_REVIEW | BLOCK.
  * Canonical / merge recommendations include the conflicting post id + URL.
  * Backward compatible CLI: --topic --keywords --output.
  * Output unchanged in location: output/agent_17/cannibalization_report.json.

Runs BEFORE Agent 04. Exit code is non-zero when the decision blocks publication
(BLOCK / MERGE / CANONICAL / HUMAN_REVIEW) unless observe-only mode is enabled.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import requests
from requests.auth import HTTPBasicAuth

from services.embeddings_service import get_embeddings_service
from services.content_similarity import (
    keyword_overlap,
    title_similarity,
    slug_similarity,
    intent_overlap,
    composite_overlap,
    token_set,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("agent_17")

WP_URL = os.getenv("WORDPRESS_URL", "")
WP_USER = os.getenv("WORDPRESS_USERNAME", "")
WP_PASS = os.getenv("WORDPRESS_APP_PASSWORD", "")

# ---- Tunable thresholds (config/cannibalization.yaml overrides these) --------
SIGNAL_WEIGHTS = {
    "semantic": 0.40,
    "title": 0.20,
    "keyword": 0.20,
    "slug": 0.10,
    "intent": 0.10,
}
# Composite-overlap decision bands.
BAND_ALLOW = 0.55          # < this -> ALLOW
BAND_HUMAN = 0.72          # [ALLOW, this) -> HUMAN_REVIEW
BAND_MERGE = 0.85          # [HUMAN, this) -> MERGE / CANONICAL
# >= BAND_MERGE -> BLOCK (near-duplicate)

DECISION_ALLOW = "ALLOW"
DECISION_CANONICAL = "CANONICAL"
DECISION_MERGE = "MERGE"
DECISION_HUMAN = "HUMAN_REVIEW"
DECISION_BLOCK = "BLOCK"

# Decisions that stop the pipeline (non-zero exit).
BLOCKING_DECISIONS = {DECISION_BLOCK, DECISION_MERGE, DECISION_CANONICAL, DECISION_HUMAN}


def _load_thresholds() -> None:
    """Optionally override thresholds from config/cannibalization.yaml if present."""
    cfg = Path("config/cannibalization.yaml")
    if not cfg.exists():
        return
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
    except Exception as e:  # pragma: no cover
        logger.warning("Could not parse cannibalization.yaml: %s", e)
        return
    global BAND_ALLOW, BAND_HUMAN, BAND_MERGE
    bands = data.get("bands", {})
    BAND_ALLOW = bands.get("allow", BAND_ALLOW)
    BAND_HUMAN = bands.get("human_review", BAND_HUMAN)
    BAND_MERGE = bands.get("merge", BAND_MERGE)
    if "weights" in data:
        SIGNAL_WEIGHTS.update(data["weights"])


def fetch_wordpress_articles(status: str = "publish,draft", per_page: int = 100) -> List[dict]:
    """Pull existing posts (id, slug, title, link) for the comparison corpus."""
    if not (WP_URL and WP_USER and WP_PASS):
        logger.warning("WordPress credentials missing; corpus is empty.")
        return []
    auth = HTTPBasicAuth(WP_USER, WP_PASS)
    posts: List[dict] = []
    page = 1
    while True:
        try:
            resp = requests.get(
                f"{WP_URL}/wp-json/wp/v2/posts",
                auth=auth,
                params={"status": status, "per_page": per_page, "page": page,
                        "_fields": "id,slug,title,link,excerpt"},
                timeout=30,
            )
        except Exception as e:  # pragma: no cover - network dependent
            logger.warning("WP fetch failed: %s", e)
            break
        if resp.status_code == 400:
            break
        if not resp.ok:
            logger.warning("WP fetch HTTP %s", resp.status_code)
            break
        batch = resp.json()
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    return posts


def _post_text(post: dict) -> str:
    title = (post.get("title") or {}).get("rendered", "") if isinstance(post.get("title"), dict) else post.get("title", "")
    excerpt = (post.get("excerpt") or {}).get("rendered", "") if isinstance(post.get("excerpt"), dict) else ""
    return f"{title} {excerpt}".strip()


def _post_title(post: dict) -> str:
    t = post.get("title")
    return t.get("rendered", "") if isinstance(t, dict) else (t or "")


def score_conflict(new_topic: str, new_keywords: List[str], new_slug: str,
                   post: dict, emb) -> Dict:
    """Compute all five signals + composite for one existing post."""
    existing_title = _post_title(post)
    existing_slug = post.get("slug", "")
    existing_text = _post_text(post)

    new_vec = emb.embed_text(f"{new_topic} {' '.join(new_keywords)}")
    old_vec = emb.embed_text(existing_text or existing_title)
    semantic = emb.cosine_similarity(new_vec, old_vec)
    # cosine can be negative with signed hashing; clamp to [0,1].
    semantic = max(0.0, semantic)

    signals = {
        "semantic": semantic,
        "title": title_similarity(new_topic, existing_title),
        "keyword": keyword_overlap(new_keywords or [new_topic],
                                   list(token_set(existing_title))),
        "slug": slug_similarity(new_slug, existing_slug),
        "intent": intent_overlap(new_topic, existing_title),
    }
    composite = composite_overlap(signals, SIGNAL_WEIGHTS)
    return {
        "post_id": post.get("id"),
        "slug": existing_slug,
        "title": existing_title,
        "url": post.get("link", ""),
        "signals": {k: round(v, 4) for k, v in signals.items()},
        "composite": round(composite, 4),
    }


def decide(composite: float) -> str:
    if composite < BAND_ALLOW:
        return DECISION_ALLOW
    if composite < BAND_HUMAN:
        return DECISION_HUMAN
    if composite < BAND_MERGE:
        return DECISION_MERGE
    return DECISION_BLOCK


def run_cannibalization_check(new_topic: str, new_keywords: List[str],
                              new_slug: str = "",
                              output_path: str = "output/agent_17/cannibalization_report.json") -> Dict:
    _load_thresholds()
    emb = get_embeddings_service()
    corpus = fetch_wordpress_articles()

    conflicts = [score_conflict(new_topic, new_keywords, new_slug, p, emb) for p in corpus]
    conflicts.sort(key=lambda c: c["composite"], reverse=True)
    top = conflicts[0] if conflicts else None
    max_score = top["composite"] if top else 0.0
    decision = decide(max_score)

    # Map MERGE -> CANONICAL recommendation when intent matches strongly.
    recommended_action = None
    canonical_target = None
    if decision in (DECISION_MERGE, DECISION_BLOCK) and top:
        canonical_target = {"post_id": top["post_id"], "url": top["url"], "slug": top["slug"]}
        if top["signals"]["intent"] >= 1.0 and decision == DECISION_MERGE:
            decision = DECISION_CANONICAL
            recommended_action = f"Set canonical to existing post {top['post_id']} ({top['url']})"
        elif decision == DECISION_MERGE:
            recommended_action = f"Merge new content into existing post {top['post_id']} ({top['url']})"
        else:
            recommended_action = f"BLOCK: near-duplicate of post {top['post_id']} ({top['url']})"
    elif decision == DECISION_HUMAN and top:
        recommended_action = (
            f"Human review required: overlaps post {top['post_id']} "
            f"(composite={max_score})"
        )

    blocking = decision in BLOCKING_DECISIONS

    report = {
        "agent": "agent_17_cannibalization",
        "version": "4.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "new_topic": new_topic,
        "new_keywords": new_keywords,
        "new_slug": new_slug,
        "corpus_size": len(corpus),
        "decision": decision,
        "blocking": blocking,
        "max_composite": round(max_score, 4),
        "bands": {"allow": BAND_ALLOW, "human_review": BAND_HUMAN, "merge": BAND_MERGE},
        "weights": SIGNAL_WEIGHTS,
        "canonical_target": canonical_target,
        "recommended_action": recommended_action,
        "top_conflicts": conflicts[:10],
    }

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(
        "Agent 17 decision=%s blocking=%s max_composite=%s corpus=%d -> %s",
        decision, blocking, round(max_score, 4), len(corpus), out,
    )
    return report


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Agent 17 - Semantic Cannibalization Engine (V4)")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--keywords", default="")
    parser.add_argument("--slug", default="")
    parser.add_argument("--output", default="output/agent_17/cannibalization_report.json")
    args = parser.parse_args()
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    result = run_cannibalization_check(args.topic, keywords, args.slug, args.output)

    # V4: blocking by default. Observe-only mode must be explicitly enabled.
    observe_only = os.getenv("AGENT17_OBSERVE_ONLY", "false").strip().lower() in ("1", "true", "yes")
    if observe_only:
        logger.warning("AGENT17_OBSERVE_ONLY enabled: not blocking despite decision=%s", result["decision"])
        sys.exit(0)
    sys.exit(1 if result["blocking"] else 0)


if __name__ == "__main__":
    main()
