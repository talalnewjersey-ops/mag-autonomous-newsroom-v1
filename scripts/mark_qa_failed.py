#!/usr/bin/env python3
"""Mark a QA/editor-failed WordPress DRAFT as [QA-FAILED].

Sprint 9 publish-invariant: an article that failed the QA (agent_12) or editor
(agent_13) gate has ALREADY had a draft created by agent_11. We do NOT trash it
(we want to inspect failures while calibrating) and we do NOT leave it a "naked"
draft (indistinguishable from a real one, risking publication). Instead we mark
it explicitly: title prefixed "[QA-FAILED] " + a "qa-failed" tag.

This never promotes anything to published (the registry invariant is enforced
separately by PRODUCED.json). It is best-effort and NON-BLOCKING: any failure is
logged and the script exits 0 so it never breaks the batch loop.
"""
import argparse
import base64
import json
import os
import sys
import urllib.request

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
_PREFIX = "[QA-FAILED] "


def qa_failed_title(title: str) -> str:
    """Prefix a title with the QA-FAILED marker, idempotently (never double-prefix)."""
    title = title or "Untitled"
    return title if title.startswith(_PREFIX) else _PREFIX + title


def _req(method, url, auth, data=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        url, data=body, method=method,
        headers={"Authorization": auth, "User-Agent": _UA, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def main() -> int:
    ap = argparse.ArgumentParser(description="Mark a QA-failed WordPress draft [QA-FAILED]")
    ap.add_argument("--wordpress-report", required=True)
    ap.add_argument("--gate", default="QA")
    args = ap.parse_args()

    url = os.environ.get("WORDPRESS_URL", "").rstrip("/")
    user = os.environ.get("WORDPRESS_USERNAME", "")
    pw = os.environ.get("WORDPRESS_APP_PASSWORD", "").replace(" ", "")
    if not (url and user and pw):
        print("mark_qa_failed: WordPress credentials missing -> skip (non-blocking)")
        return 0
    try:
        rep = json.load(open(args.wordpress_report, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"mark_qa_failed: no wordpress_report ({e}) -> skip")
        return 0
    post_id = rep.get("post_id")
    if not post_id:
        print("mark_qa_failed: no post_id in report -> nothing to mark")
        return 0

    auth = "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode()
    try:
        post = _req("GET", f"{url}/wp-json/wp/v2/posts/{post_id}?context=edit", auth)
        current_title = (post.get("title", {}) or {}).get("raw", "") or rep.get("title", "")
        # get-or-create the qa-failed tag
        tag_id = None
        try:
            tags = _req("GET", f"{url}/wp-json/wp/v2/tags?slug=qa-failed", auth)
            tag_id = tags[0]["id"] if tags else _req(
                "POST", f"{url}/wp-json/wp/v2/tags", auth,
                {"name": "qa-failed", "slug": "qa-failed"}).get("id")
        except Exception as e:  # noqa: BLE001
            print(f"mark_qa_failed: tag get/create failed ({e}) -> title-only")
        payload = {"title": qa_failed_title(current_title), "status": "draft"}
        if tag_id:
            payload["tags"] = sorted(set((post.get("tags") or []) + [tag_id]))
        _req("POST", f"{url}/wp-json/wp/v2/posts/{post_id}", auth, payload)
        print(f"mark_qa_failed: post {post_id} marked [QA-FAILED] (gate={args.gate}, tag={tag_id})")
    except Exception as e:  # noqa: BLE001 -- best-effort, must never break the batch
        print(f"mark_qa_failed: WP update failed (non-blocking): {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
