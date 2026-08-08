"""Write action: updates a PUBLISHED post's content. Deliberately separate
from update_wp_post_content.py (which refuses on 'publish' by design) --
this is the explicit, higher-stakes counterpart, only to be used after
explicit user go-ahead for a specific live merge. Safety gates:
  - refuses unless the post's CURRENT status is already 'publish' (confirms
    we're targeting what the caller thinks we're targeting)
  - refuses unless current content length matches EXPECTED_CURRENT_LENGTH
    (protects against clobbering a concurrent edit)
  - never sends a 'status' field -- status is never touched either way
  - requires CONFIRM=yes
Part of the calculator live-merge workstream (2026-08-08), posts 1641/1624.
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


def update_post_content(wp_url, user, app_password, post_id, new_content):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}"
    payload = {"content": new_content}  # deliberately no "status" key
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
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
    content_path = os.environ["CONTENT_FILE"]
    expected_current_length = int(os.environ["EXPECTED_CURRENT_LENGTH"])
    confirm = os.environ.get("CONFIRM", "").lower() == "yes"

    with open(content_path, encoding="utf-8") as f:
        new_content = f.read()

    before = get_post(wp_url, user, app_pw, post_id)
    current_status = before.get("status")
    current_content = before.get("content", {}).get("raw", "") or ""
    print(f"BEFORE: id={post_id} status={current_status} content_length={len(current_content)}")

    if current_status != "publish":
        print(f"REFUSING: post {post_id} is currently '{current_status}', not 'publish'. Aborting.")
        sys.exit(1)

    if len(current_content) != expected_current_length:
        print(f"REFUSING: current content length {len(current_content)} != expected {expected_current_length} "
              f"-- content changed since last read, possible concurrent edit. Aborting.")
        sys.exit(1)

    if not confirm:
        print("REFUSING: CONFIRM=yes not set. This is a deliberate safety gate for a live published-post edit. Aborting without writing.")
        sys.exit(1)

    status_code, result = update_post_content(wp_url, user, app_pw, post_id, new_content)
    if status_code not in (200, 201):
        print(f"UPDATE FAILED: HTTP {status_code}: {result}")
        sys.exit(1)

    after_status = result.get("status")
    after_content = result.get("content", {}).get("raw", "") or ""
    print(f"AFTER: id={result.get('id')} status={after_status} content_length={len(after_content)}")

    if after_status != "publish":
        print("ATTENTION: post status changed unexpectedly -- verify manually.")
        sys.exit(1)

    print(f"SUCCESS: post {post_id} content updated, status remains 'publish'")


if __name__ == "__main__":
    main()
