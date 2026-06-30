#!/usr/bin/env python3
"""Notify nexus-ugc-enterprise when a NEXUS-14 article goes live in WordPress.

The NEXUS-14 newsroom pipeline (``production_v2.yml``) stops at a WordPress
*draft*; a human publishes it later. This decoupled notifier watches WordPress
for posts that have actually reached ``status=publish`` and, for each one not yet
announced, fires a GitHub ``repository_dispatch`` (event_type
``nexus14_article_published``) to the UGC repo so it can produce promotional
short-form content pointing at the real, live canonical URL.

It is **fail-closed**: missing configuration aborts the run; a transport error
on one post does not stop the others but is reported and fails the run.

Idempotency: dispatched post ids are remembered in a small JSON state file
(persisted between runs via the workflow's Actions cache), so re-running never
re-announces the same article. No WordPress-side plugin or post meta is needed.

The pure helpers (``build_payload``, ``select_to_notify``, ``load_notified`` …)
are unit-tested offline; network access lives behind small seams that take an
injected ``requests``-style session, so tests need no network and no secrets.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import requests

UGC_EVENT_TYPE = "nexus14_article_published"
SOURCE_SYSTEM = "nexus-14"
DEFAULT_UGC_REPO = "talalnewjersey-ops/nexus-ugc-enterprise"
DEFAULT_STATE_FILE = ".ugc_notified_ids.json"
# WordPress returns at most 100 posts per page; we dedupe with the state file,
# so a single page of the most-recent published posts is enough.
PER_PAGE = 100


def iso_utc(value: str) -> str:
    """Normalize a WordPress ``date_gmt`` (naive UTC) to ISO-8601 with ``Z``."""
    v = (value or "").strip()
    if not v:
        return v
    return v if v.endswith("Z") else f"{v}Z"


def build_payload(post: Mapping[str, Any]) -> dict[str, Any]:
    """Map a WordPress post object onto the ``nexus14_article_published`` body."""
    post_id = post["id"]
    return {
        "event_type": UGC_EVENT_TYPE,
        "client_payload": {
            "source_system": SOURCE_SYSTEM,
            "article_id": f"wp-{post_id}",
            "canonical_url": (post.get("link") or "").strip(),
            "article_ref": f"/wp-json/wp/v2/posts/{post_id}",
            "published_at": iso_utc(post.get("date_gmt", "")),
        },
    }


def is_publishable(post: Mapping[str, Any], notified: set[str]) -> bool:
    """True if the post is live, has a real URL, and hasn't been announced yet."""
    return (
        post.get("status") == "publish"
        and bool((post.get("link") or "").strip())
        and str(post.get("id")) not in notified
    )


def select_to_notify(
    posts: Iterable[Mapping[str, Any]], notified: set[str]
) -> list[Mapping[str, Any]]:
    """Filter the WordPress posts down to those that still need an announcement."""
    return [p for p in posts if is_publishable(p, notified)]


def load_notified(path: str | Path) -> set[str]:
    """Load the set of already-announced post ids (empty if no/invalid state)."""
    p = Path(path)
    if not p.exists():
        return set()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set()
    if isinstance(data, list):
        return {str(x) for x in data}
    return set()


def save_notified(path: str | Path, notified: set[str]) -> None:
    """Persist the announced-post-id set as a sorted JSON list."""
    Path(path).write_text(
        json.dumps(sorted(notified), indent=2) + "\n", encoding="utf-8"
    )


def fetch_published_posts(
    session: requests.Session, wp_url: str, user: str, app_password: str
) -> list[dict[str, Any]]:
    """Fetch the most-recent published posts from the WordPress REST API."""
    resp = session.get(
        f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts",
        params={
            "status": "publish",
            "per_page": PER_PAGE,
            "orderby": "date",
            "order": "desc",
            "_fields": "id,link,date_gmt,status",
        },
        auth=(user, app_password),
        timeout=30,
    )
    resp.raise_for_status()
    posts = resp.json()
    return posts if isinstance(posts, list) else []


def dispatch_to_ugc(
    session: requests.Session, repo: str, token: str, payload: Mapping[str, Any]
) -> int:
    """POST a repository_dispatch to the UGC repo; returns the HTTP status (204)."""
    resp = session.post(
        f"https://api.github.com/repos/{repo}/dispatches",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "nexus14-ugc-publish-notifier",
        },
        data=json.dumps(payload).encode("utf-8"),
        timeout=30,
    )
    resp.raise_for_status()
    return int(resp.status_code)


def main() -> int:
    wp_url = os.environ.get("WORDPRESS_URL", "")
    user = os.environ.get("WORDPRESS_USERNAME", "")
    app_password = os.environ.get("WORDPRESS_APP_PASSWORD", "")
    token = os.environ.get("UGC_DISPATCH_TOKEN", "")
    repo = os.environ.get("UGC_REPO", DEFAULT_UGC_REPO)
    state_file = os.environ.get("UGC_NOTIFIED_STATE_FILE", DEFAULT_STATE_FILE)

    required = {
        "WORDPRESS_URL": wp_url,
        "WORDPRESS_USERNAME": user,
        "WORDPRESS_APP_PASSWORD": app_password,
        "UGC_DISPATCH_TOKEN": token,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        print(
            f"[notifier] missing env: {', '.join(missing)}; refusing to run (fail-closed)",
            file=sys.stderr,
        )
        return 1

    session = requests.Session()
    notified = load_notified(state_file)
    try:
        posts = fetch_published_posts(session, wp_url, user, app_password)
    except requests.RequestException as exc:
        print(f"[notifier] WordPress fetch failed: {exc}", file=sys.stderr)
        return 1

    todo = select_to_notify(posts, notified)
    print(
        f"[notifier] {len(posts)} published post(s) seen; {len(todo)} new to announce"
    )

    failures = 0
    for post in todo:
        payload = build_payload(post)
        url = payload["client_payload"]["canonical_url"]
        try:
            dispatch_to_ugc(session, repo, token, payload)
        except requests.RequestException as exc:
            failures += 1
            print(f"[notifier] FAILED wp-{post.get('id')}: {exc}", file=sys.stderr)
            continue
        notified.add(str(post["id"]))
        print(f"[notifier] announced wp-{post['id']} -> {url}")

    save_notified(state_file, notified)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
