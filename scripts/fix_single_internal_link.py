"""One-off, narrowly-scoped write action: replaces a single internal link's
href in ONE WordPress post's content, leaving everything else (anchor text,
surrounding HTML, all other links, title, slug, meta, status) untouched.

Built for the specific case of an internal link that currently points at a
URL which itself 301-redirects, updating it to point directly at the
redirect's final destination -- without touching the Redirection plugin
rule, which may still be serving other traffic.

Safety:
  - Explicitly re-sends the CURRENT status unchanged (works for
    published/draft/pending/private alike -- this is a content-only patch,
    never a status change).
  - Refuses unless the old href string appears in the content EXACTLY the
    expected number of times (default 1) -- avoids silently touching an
    unintended occurrence or silently doing nothing.
  - Only replaces the href attribute value itself, never anchor text.
  - Writes a full before/after snapshot to disk for an auditable record.

Fix-file shape (JSON): {"post_id": int, "old_href": str, "new_href": str,
"expected_occurrences": int (optional, default 1)}
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


def update_post_content(wp_url, user, app_password, post_id, new_content, keep_status):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}"
    payload = json.dumps({"content": new_content, "status": keep_status}).encode("utf-8")
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
    fix_path = os.environ["FIX_FILE"]

    with open(fix_path, "r", encoding="utf-8") as f:
        spec = json.load(f)

    post_id = spec["post_id"]
    old_href = spec["old_href"]
    new_href = spec["new_href"]
    expected = spec.get("expected_occurrences", 1)

    before = get_post(wp_url, user, app_pw, post_id)
    current_status = before.get("status")
    content = before.get("content", {}).get("raw", "")
    print(f"BEFORE: id={post_id} status={current_status!r} content_length={len(content)}")

    with open(f"post_{post_id}_before_link_fix.json", "w", encoding="utf-8") as f:
        json.dump(before, f, indent=2, ensure_ascii=False)

    old_attr = f'href="{old_href}"'
    new_attr = f'href="{new_href}"'
    count = content.count(old_attr)

    if count != expected:
        print(f"REFUSING: found {count} occurrence(s) of {old_attr!r}, expected exactly {expected}. "
              f"Aborting -- no change made.")
        sys.exit(1)

    new_content = content.replace(old_attr, new_attr)

    status_code, result = update_post_content(wp_url, user, app_pw, post_id, new_content, current_status)
    if status_code not in (200, 201):
        print(f"UPDATE FAILED: HTTP {status_code}: {result}")
        sys.exit(1)

    after_status = result.get("status")
    print(f"AFTER: id={result.get('id')} status={after_status!r} content_length={len(result.get('content', {}).get('raw', ''))}")

    if after_status != current_status:
        print(f"CRITICAL: status changed from {current_status!r} to {after_status!r} -- this should never happen. Investigate immediately.")
        sys.exit(1)

    print(f"SUCCESS: replaced {count} occurrence(s) of the link. Status preserved as {after_status!r}.")

    with open(f"post_{post_id}_after_link_fix.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
