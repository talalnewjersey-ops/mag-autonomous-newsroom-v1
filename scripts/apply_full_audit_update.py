"""One-off: apply a full editorial audit update (title, slug, content, Yoast
SEO meta) to ONE WordPress post, from a checked-in spec file. Part of the
published-content audit workstream -- NEVER publishes, NEVER touches any
other post/page/plugin/theme/snippet/setting.

Fix-file shape (JSON): {"post_id": int, "title": str, "slug": str,
"content_file": str (path to the new content HTML, read at run time so this
JSON stays small and diffable), "yoast_title": str, "yoast_metadesc": str,
"yoast_focuskw": str}

Safety, absolute:
  - Refuses unless the CURRENT live status is exactly 'draft'. Never writes
    to a published, pending, or private post with this script.
  - After writing, explicitly re-sets status to 'draft' in the SAME request
    (belt-and-suspenders -- a field omitted from a POST body is left
    unchanged by the WP REST API, so status is never implicitly at risk,
    but this makes the "never publishes" guarantee visible in the payload
    itself, not just an absence).
  - Prints BEFORE and AFTER title/slug/status/content-length for an
    auditable record; writes a full before/after snapshot to disk.
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


def update_post(wp_url, user, app_password, post_id, payload):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
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

    before = get_post(wp_url, user, app_pw, post_id)
    before_status = before.get("status")
    print(f"BEFORE: id={post_id} status={before_status!r} title={before.get('title', {}).get('raw', '')!r} "
          f"slug={before.get('slug', '')!r} content_length={len(before.get('content', {}).get('raw', ''))}")

    with open(f"post_{post_id}_before_full_audit.json", "w", encoding="utf-8") as f:
        json.dump(before, f, indent=2, ensure_ascii=False)

    if before_status != "draft":
        print(f"REFUSING: post {post_id} status is {before_status!r}, not 'draft'. "
              f"This script only ever writes to a draft. Aborting -- no change made.")
        sys.exit(1)

    with open(spec["content_file"], "r", encoding="utf-8") as f:
        new_content = f.read()

    payload = {
        "title": spec["title"],
        "slug": spec["slug"],
        "content": new_content,
        "status": "draft",  # explicit, belt-and-suspenders -- never publishes
        "meta": {
            "_yoast_wpseo_title": spec["yoast_title"],
            "_yoast_wpseo_metadesc": spec["yoast_metadesc"],
            "_yoast_wpseo_focuskw": spec["yoast_focuskw"],
        },
    }

    status_code, result = update_post(wp_url, user, app_pw, post_id, payload)
    if status_code not in (200, 201):
        print(f"UPDATE FAILED: HTTP {status_code}: {result}")
        sys.exit(1)

    print(f"AFTER: id={result.get('id')} status={result.get('status')!r} "
          f"title={result.get('title', {}).get('raw', '')!r} slug={result.get('slug', '')!r} "
          f"content_length={len(result.get('content', {}).get('raw', ''))}")

    if result.get("status") != "draft":
        print(f"CRITICAL: post-write status is {result.get('status')!r}, NOT 'draft' -- "
              f"this should never happen. Investigate immediately.")
        sys.exit(1)

    print("SUCCESS: draft updated, status confirmed still 'draft'. NOT published.")

    with open(f"post_{post_id}_after_full_audit.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
