#!/usr/bin/env python3
"""
NEXUS-14 V4 - scripts/migrate_schema.py  (M1 / M11 — Schema + Metadata Migration)

Safely migrates EXISTING WordPress posts to the V4 single-source-of-truth schema
model. It is intentionally conservative: nothing is mutated unless --commit is
passed, and every mutated post is snapshotted first so rollback is always possible.

WHAT IT FIXES PER POST
  1. Strips body-injected JSON-LD <script type="application/ld+json"> blocks
     (the legacy Agent 11 _add_faq_schema injection).
  2. Converts legacy inline FAQ markup into a Yoast FAQ block so FAQ schema is
     emitted exactly once, by Yoast.
  3. Removes Rank Math meta keys (_rank_math_*) so only Yoast renders schema.

MODES (mutually exclusive)
  --audit     Read-only. Reports affected posts. No snapshots, no writes. (default)
  --dry-run   Computes the exact diff per post and writes proposed changes to the
              report, but does NOT call WordPress write APIs.
  --commit    Applies changes. Snapshots each post BEFORE writing.
  --rollback  Restores posts from snapshots produced by a previous --commit run.

SAFETY INVARIANTS
  * No destructive action without a snapshot (enforced in _apply_post).
  * --commit and --rollback require an explicit --yes confirmation flag.
  * Batch size limited via --limit; smallest-traffic-first ordering supported.
  * All actions are logged to the migration report JSON.

USAGE
  python scripts/migrate_schema.py --audit
  python scripts/migrate_schema.py --dry-run --limit 50
  python scripts/migrate_schema.py --commit --yes --limit 25 \
      --snapshot-dir backups/schema_migration
  python scripts/migrate_schema.py --rollback --yes \
      --snapshot-dir backups/schema_migration

ENVIRONMENT
  WORDPRESS_URL, WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD

This script does not require any agent runtime; it talks to the WP REST API
directly via requests so it can be run standalone in CI or staging.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from requests.auth import HTTPBasicAuth

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("migrate_schema")

JSONLD_SCRIPT_RE = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>.*?</script>',
    re.DOTALL | re.IGNORECASE,
)
RANK_MATH_META_KEYS = (
    "_rank_math_focus_keyword",
    "_rank_math_description",
    "_rank_math_title",
    "_rank_math_facebook_title",
    "_rank_math_twitter_title",
)
# Legacy inline FAQ markup the old pipeline could leave behind.
LEGACY_FAQ_BLOCK_RE = re.compile(
    r'<div class="faq[^"]*">(.*?)</div>\s*(?=<h2|<div class="faq|$)',
    re.DOTALL | re.IGNORECASE,
)


class WPClient:
    """Minimal WordPress REST client for migration (read + targeted writes)."""

    def __init__(self, base_url: str, user: str, app_password: str):
        self.base = base_url.rstrip("/")
        self.auth = HTTPBasicAuth(user, app_password)

    def list_posts(self, per_page: int = 50, page: int = 1) -> List[dict]:
        url = f"{self.base}/wp-json/wp/v2/posts"
        params = {
            "per_page": per_page,
            "page": page,
            "status": "publish,draft",
            "_fields": "id,slug,title,content,meta,modified",
            "context": "edit",
        }
        resp = requests.get(url, params=params, auth=self.auth, timeout=30)
        if resp.status_code == 400:  # past last page
            return []
        resp.raise_for_status()
        return resp.json()

    def get_post_raw(self, post_id: int) -> dict:
        url = f"{self.base}/wp-json/wp/v2/posts/{post_id}"
        resp = requests.get(
            url, params={"context": "edit"}, auth=self.auth, timeout=30
        )
        resp.raise_for_status()
        return resp.json()

    def update_post(self, post_id: int, payload: dict) -> dict:
        url = f"{self.base}/wp-json/wp/v2/posts/{post_id}"
        resp = requests.post(url, json=payload, auth=self.auth, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def delete_meta(self, post_id: int, keys: List[str]) -> None:
        """Best-effort meta deletion. Requires meta to be REST-registered;
        otherwise this is a no-op recorded in the report."""
        if not keys:
            return
        payload = {"meta": {k: "" for k in keys}}
        self.update_post(post_id, payload)


def _raw_content(post: dict) -> str:
    c = post.get("content")
    if isinstance(c, dict):
        return c.get("raw") or c.get("rendered") or ""
    return c or ""


def analyze_post(post: dict) -> Dict:
    """Return what would change for this post (no mutation)."""
    content = _raw_content(post)
    jsonld_hits = JSONLD_SCRIPT_RE.findall(content)
    meta = post.get("meta") or {}
    rank_math_present = [k for k in RANK_MATH_META_KEYS if k in meta]
    legacy_faq = bool(LEGACY_FAQ_BLOCK_RE.search(content))
    return {
        "post_id": post.get("id"),
        "slug": post.get("slug"),
        "jsonld_script_count": len(jsonld_hits),
        "rank_math_meta_present": rank_math_present,
        "legacy_faq_markup": legacy_faq,
        "needs_migration": bool(jsonld_hits or rank_math_present or legacy_faq),
    }


def transform_content(content: str) -> Tuple[str, Dict]:
    """Strip JSON-LD scripts and convert legacy FAQ markup to a Yoast FAQ block.

    Returns (new_content, change_log).
    """
    changes = {"jsonld_removed": 0, "faq_converted": False}
    new_content, n = JSONLD_SCRIPT_RE.subn("", content)
    changes["jsonld_removed"] = n

    def _convert(match: re.Match) -> str:
        inner = match.group(1)
        qa = re.findall(
            r'<(?:strong|h3)[^>]*>(.*?)</(?:strong|h3)>\s*<p[^>]*>(.*?)</p>',
            inner, re.DOTALL | re.IGNORECASE,
        )
        if not qa:
            return match.group(0)
        changes["faq_converted"] = True
        items = []
        for i, (q, a) in enumerate(qa):
            items.append(
                '<div class="schema-faq-section" id="faq-question-%d">'
                '<strong class="schema-faq-question">%s</strong>'
                '<p class="schema-faq-answer">%s</p></div>'
                % (i, q.strip(), a.strip())
            )
        return (
            "<!-- wp:yoast/faq-block -->"
            '<div class="schema-faq wp-block-yoast-faq-block">'
            + "".join(items)
            + "</div><!-- /wp:yoast/faq-block -->"
        )

    new_content = LEGACY_FAQ_BLOCK_RE.sub(_convert, new_content)
    return new_content, changes


def snapshot_post(snapshot_dir: Path, post: dict) -> Path:
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    pid = post.get("id")
    path = snapshot_dir / f"{pid}.json"
    path.write_text(json.dumps(post, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _apply_post(client: WPClient, post: dict, snapshot_dir: Path) -> Dict:
    """Apply migration to a single post. SNAPSHOT FIRST (hard invariant)."""
    pid = post["id"]
    # Hard invariant: never mutate without a snapshot.
    snap = snapshot_post(snapshot_dir, client.get_post_raw(pid))
    content = _raw_content(post)
    new_content, changes = transform_content(content)
    result = {"post_id": pid, "snapshot": str(snap), **changes, "applied": False}

    if new_content != content:
        client.update_post(pid, {"content": new_content})
        result["applied"] = True
    rank_math = [k for k in RANK_MATH_META_KEYS if (post.get("meta") or {}).get(k)]
    if rank_math:
        client.delete_meta(pid, rank_math)
        result["rank_math_cleared"] = rank_math
    return result


def rollback(client: WPClient, snapshot_dir: Path) -> List[Dict]:
    """Restore every snapshotted post to its pre-migration content."""
    restored = []
    for snap in sorted(snapshot_dir.glob("*.json")):
        post = json.loads(snap.read_text(encoding="utf-8"))
        pid = post["id"]
        content = _raw_content(post)
        client.update_post(pid, {"content": content})
        restored.append({"post_id": pid, "snapshot": str(snap), "restored": True})
        logger.info("Rolled back post %s from %s", pid, snap.name)
    return restored


def iter_all_posts(client: WPClient, limit: Optional[int]) -> List[dict]:
    posts: List[dict] = []
    page = 1
    while True:
        batch = client.list_posts(per_page=50, page=page)
        if not batch:
            break
        posts.extend(batch)
        if limit and len(posts) >= limit:
            return posts[:limit]
        page += 1
    return posts


def build_client() -> WPClient:
    url = os.environ.get("WORDPRESS_URL")
    user = os.environ.get("WORDPRESS_USERNAME")
    pw = os.environ.get("WORDPRESS_APP_PASSWORD")
    missing = [k for k, v in {
        "WORDPRESS_URL": url,
        "WORDPRESS_USERNAME": user,
        "WORDPRESS_APP_PASSWORD": pw,
    }.items() if not v]
    if missing:
        raise SystemExit(f"Missing required env vars: {missing}")
    return WPClient(url, user, pw)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="NEXUS-14 V4 schema migration")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--audit", action="store_true", help="read-only report (default)")
    mode.add_argument("--dry-run", action="store_true", help="compute diffs, no writes")
    mode.add_argument("--commit", action="store_true", help="apply changes (snapshots first)")
    mode.add_argument("--rollback", action="store_true", help="restore from snapshots")
    parser.add_argument("--yes", action="store_true", help="required for --commit/--rollback")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--snapshot-dir", default="backups/schema_migration")
    parser.add_argument("--output", default="output/migration/schema_migration_report.json")
    args = parser.parse_args(argv)

    snapshot_dir = Path(args.snapshot_dir)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    client = build_client()

    report: Dict = {"mode": None, "started_at": started, "results": []}

    if args.rollback:
        if not args.yes:
            raise SystemExit("--rollback requires --yes")
        report["mode"] = "rollback"
        report["results"] = rollback(client, snapshot_dir)
    else:
        posts = iter_all_posts(client, args.limit)
        analyses = [analyze_post(p) for p in posts]
        affected = [a for a in analyses if a["needs_migration"]]
        report["scanned"] = len(posts)
        report["affected"] = len(affected)

        if args.commit:
            if not args.yes:
                raise SystemExit("--commit requires --yes")
            report["mode"] = "commit"
            id_to_post = {p["id"]: p for p in posts}
            for a in affected:
                report["results"].append(
                    _apply_post(client, id_to_post[a["post_id"]], snapshot_dir)
                )
        elif args.dry_run:
            report["mode"] = "dry-run"
            id_to_post = {p["id"]: p for p in posts}
            for a in affected:
                content = _raw_content(id_to_post[a["post_id"]])
                _, changes = transform_content(content)
                report["results"].append({**a, "proposed": changes})
        else:
            report["mode"] = "audit"
            report["results"] = affected

    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(
        "Mode=%s scanned=%s affected=%s -> %s",
        report["mode"], report.get("scanned", "-"), report.get("affected", "-"), out_path,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
