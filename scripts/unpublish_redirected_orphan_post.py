"""One-off fix (2026-08-07, content-cannibalization audit): sets a PUBLISHED
post's status to 'draft' when its own permalink slug is shadowed by an
ACTIVE, enabled Redirection-plugin 301 rule -- the exact "publish + live
redirect on the same URL" orphan state found on post 48733 (slug
best-newcomer-bank-accounts-in-canada-complete-guide-for-canada-immigrants-2026,
shadowed by redirect id=108 -> /best-banks-newcomers-canada-2026/). The
redirect already does the real consolidation work; a status of 'publish'
on the shadowed post is misleading (it reads as live in wp-admin and in any
DB-level report, e.g. Search Console attribution, while being genuinely
unreachable to a visitor) and the correct state is 'draft', same as any
other pipeline-produced but not-yet-canonical article.

Two independent safety checks, both required, no exceptions:
  1. Fat-finger guard: POST_ID and CONFIRM_POST_ID must match exactly (same
     convention as delete-wp-post.yml).
  2. Self-verified justification: refuses to run unless it independently
     confirms, via the Redirection plugin's own REST API, that an ENABLED
     redirect rule's source URL matches this post's OWN slug -- never trusts
     the caller's claim that a redirect exists. This is what makes the
     script safe to reuse for a future case of this exact anomaly, not just
     a hardcoded one-off for 48733.

Sets status only -- content, title, slug, categories all untouched (same
scope discipline as apply_single_post_fix.py's set_title/set_slug/
set_categories paths, which this deliberately does NOT extend, per that
script's own "never touches status" boundary).
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request


def get_post(wp_url, user, app_password, post_id):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}?context=edit"
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_all_redirects(wp_url, user, app_password, per_page=200):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    items, page_num = [], 0
    while True:
        url = (f"{wp_url.rstrip('/')}/wp-json/redirection/v1/redirect"
               f"?per_page={per_page}&page={page_num}")
        req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        batch = data.get("items", [])
        if not batch:
            break
        items.extend(batch)
        if len(batch) < per_page:
            break
        page_num += 1
    return items


def set_status_draft(wp_url, user, app_password, post_id):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}"
    payload = json.dumps({"status": "draft"}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
    post_id = os.environ["POST_ID"]
    confirm_post_id = os.environ["CONFIRM_POST_ID"]

    if post_id != confirm_post_id:
        print(f"REFUSING: POST_ID ({post_id!r}) and CONFIRM_POST_ID ({confirm_post_id!r}) do not match.")
        sys.exit(1)

    before = get_post(wp_url, user, app_pw, post_id)
    slug = before.get("slug", "")
    status = before.get("status")
    print(f"BEFORE: id={post_id} status={status} slug={slug!r} title={before.get('title', {}).get('raw', '')!r}")

    with open(f"post_{post_id}_before_unpublish.json", "w", encoding="utf-8") as f:
        json.dump(before, f, indent=2, ensure_ascii=False)

    if status != "publish":
        print(f"REFUSING: post {post_id} status is {status!r}, not 'publish' -- nothing to fix here.")
        sys.exit(1)

    redirects = fetch_all_redirects(wp_url, user, app_pw)
    shadowing = [
        r for r in redirects
        if r.get("enabled") and r.get("url", "").strip("/").lower() == slug.strip("/").lower()
    ]
    if not shadowing:
        print(f"REFUSING: no ENABLED Redirection rule found with source url matching slug "
              f"'/{slug}/' -- this post is not actually shadowed by a redirect. Aborting.")
        sys.exit(1)

    rule = shadowing[0]
    target = rule.get("action_data", {}).get("url", "")
    print(f"CONFIRMED shadowing redirect: id={rule.get('id')} '/{slug}/' -> {target!r} "
          f"(code={rule.get('action_code')})")

    status_code, result = set_status_draft(wp_url, user, app_pw, post_id)
    if status_code not in (200, 201):
        print(f"UPDATE FAILED: HTTP {status_code}: {result}")
        sys.exit(1)

    print(f"AFTER: id={result.get('id')} status={result.get('status')}")
    print(f"SUCCESS: post {post_id} set to draft (redirect id={rule.get('id')} still points to {target!r}, unchanged)")

    with open(f"post_{post_id}_after_unpublish.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
