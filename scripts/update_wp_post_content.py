"""Write action: updates ONE WordPress post's content via the REST API,
explicitly preserving its current status (never force-publishes). Used for
one-off editorial revisions of an already-generated article -- reads the new
content from a local file (not an env var/CLI arg) so large HTML payloads
don't hit workflow_dispatch input size limits.
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
    post_id = os.environ["POST_ID"]
    content_path = os.environ["CONTENT_FILE"]

    with open(content_path, encoding="utf-8") as f:
        new_content = f.read()

    before = get_post(wp_url, user, app_pw, post_id)
    current_status = before.get("status")
    print(f"BEFORE: id={post_id} status={current_status} content_length={len(before.get('content', {}).get('raw', ''))}")

    if current_status not in ("draft", "pending", "private"):
        print(f"REFUSING: post {post_id} is currently '{current_status}', not a safe draft-like status. Aborting to avoid an accidental publish-status change.")
        sys.exit(1)

    status_code, result = update_post_content(wp_url, user, app_pw, post_id, new_content, current_status)
    if status_code not in (200, 201):
        print(f"UPDATE FAILED: HTTP {status_code}: {result}")
        sys.exit(1)

    print(f"AFTER: id={result.get('id')} status={result.get('status')} content_length={len(result.get('content', {}).get('raw', ''))}")
    print(f"SUCCESS: post {post_id} content updated, status preserved as '{result.get('status')}'")


if __name__ == "__main__":
    main()
