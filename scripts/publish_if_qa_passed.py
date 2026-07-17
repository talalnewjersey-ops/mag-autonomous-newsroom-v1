#!/usr/bin/env python3
"""Flip a WordPress draft to live `publish` status -- the ONLY code path in
this repo that ever does so (2026-07-17, real auto-publish decision).

Strictly gated, in this order -- ALL must hold or the post stays a draft:
  1. draft_only must be the literal string "false" (same fail-safe contract
     as scripts/production_batch_loop.sh's own resolve_draft_only()).
  2. agent_12's qa_report.json must be from the REAL DI-stack path, not the
     heuristic fallback (agent_12 sets "mode": "heuristic" only on that
     fallback -- its overall_score is a different, much weaker scale,
     capped at 75, that would never legitimately clear the gate below, but
     this is checked explicitly anyway as defense-in-depth, same philosophy
     as agent_12's own hallucination_penalty comment).
  3. status must be "PASS".
  4. overall_score must be >= PUBLICATION_QUALITY_GATE.

PUBLICATION_QUALITY_GATE is IMPORTED from agent_12, never copied as a second
literal -- a copied "95" is exactly how GATE QA's own threshold silently
drifted from the documented 95 down to 85 for an unknown stretch of time
before AUDIT-LOG.md caught it (see agent_12's module docstring). One source
of truth, enforced by tests/test_publish_flip_invariant.py.

Best-effort / non-blocking, same convention as scripts/mark_qa_failed.py: a
WordPress API hiccup here must never fail the batch loop or the article's
PRODUCED count -- the post simply stays a draft and gets picked up on the
next run. This script also refuses to touch a post that is not currently in
"draft" status (defense-in-depth against a double-run or race).
"""
import argparse
import base64
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents.agent_12_quality_assurance import PUBLICATION_QUALITY_GATE  # noqa: E402

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def should_publish(qa_report, draft_only):
    """Pure decision function, no network -- unit-tested directly by
    tests/test_publish_flip_invariant.py. Returns (publish: bool, reason: str).
    The ONLY True outcome: draft_only=="false" AND a real (non-heuristic) PASS
    at or above PUBLICATION_QUALITY_GATE."""
    if draft_only != "false":
        return False, f"draft_only={draft_only!r} (not the literal 'false') -- staying draft"
    if qa_report.get("mode") == "heuristic":
        return False, "qa_report is from the heuristic fallback path (no real gate) -- staying draft"
    if qa_report.get("status") != "PASS":
        return False, f"qa_report status={qa_report.get('status')!r} -- staying draft"
    score = qa_report.get("overall_score", 0)
    if not isinstance(score, (int, float)) or score < PUBLICATION_QUALITY_GATE:
        return False, f"overall_score={score} below PUBLICATION_QUALITY_GATE={PUBLICATION_QUALITY_GATE} -- staying draft"
    return True, f"overall_score={score} >= {PUBLICATION_QUALITY_GATE}, status=PASS, draft_only=false -- publishing"


def _req(method, url, auth, data=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        url, data=body, method=method,
        headers={"Authorization": auth, "User-Agent": _UA, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser(
        description="Flip a WordPress draft to publish, gated on draft_only=false + real QA PASS >= 95")
    ap.add_argument("--qa-report", required=True, help="agent_12 qa_report.json")
    ap.add_argument("--wordpress-report", required=True,
                     help="agent_11 wordpress_validation_report.json (post_id source)")
    ap.add_argument("--draft-only", required=True, help="resolved DRAFT_ONLY bash value ('true' or 'false')")
    args = ap.parse_args()

    try:
        qa_report = json.load(open(args.qa_report, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 -- best-effort, must never break the batch
        print(f"publish_if_qa_passed: no qa_report ({e}) -> skip, staying draft")
        return 0

    publish, reason = should_publish(qa_report, args.draft_only)
    print(f"publish_if_qa_passed: {reason}")
    if not publish:
        return 0

    try:
        wp_report = json.load(open(args.wordpress_report, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"publish_if_qa_passed: no wordpress_report ({e}) -> skip, staying draft")
        return 0
    post_id = wp_report.get("post_id")
    if not post_id:
        print("publish_if_qa_passed: no post_id in wordpress_report -> nothing to publish")
        return 0

    url = os.environ.get("WORDPRESS_URL", "").rstrip("/")
    user = os.environ.get("WORDPRESS_USERNAME", "")
    pw = os.environ.get("WORDPRESS_APP_PASSWORD", "").replace(" ", "")
    if not (url and user and pw):
        print("publish_if_qa_passed: WordPress credentials missing -> skip (non-blocking)")
        return 0

    auth = "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode()
    try:
        before = _req("GET", f"{url}/wp-json/wp/v2/posts/{post_id}?context=edit", auth)
        current_status = before.get("status")
        if current_status != "draft":
            print(f"publish_if_qa_passed: post {post_id} current status={current_status!r} "
                  f"(not 'draft') -> refusing to touch it")
            return 0
        after = _req("POST", f"{url}/wp-json/wp/v2/posts/{post_id}", auth, {"status": "publish"})
        print(f"publish_if_qa_passed: post {post_id} {current_status} -> {after.get('status')} "
              f"(qa_score={qa_report.get('overall_score')}, url={after.get('link', '')})")
        if after.get("status") != "publish":
            print(f"publish_if_qa_passed: WARNING -- WP did not confirm 'publish' status "
                  f"after update (got {after.get('status')!r})")
    except Exception as e:  # noqa: BLE001 -- best-effort, must never break the batch
        print(f"publish_if_qa_passed: WP publish call failed (non-blocking): {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
