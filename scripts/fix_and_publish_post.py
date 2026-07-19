"""One-off write action: fixes the exact 'Ssn' -> 'SSN' title-case defect
that blocked post 48870 at GATE D (agents/_placeholder_scan.py::scan_title),
then publishes it. Refuses to run unless the live post's title/content still
contain the broken substring exactly as expected, and unless the post is
currently draft/pending/private -- so it can never silently touch unrelated
content or an already-published post.
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request

OLD = "Ssn"
NEW = "SSN"


def get_post(wp_url, user, app_password, post_id):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}?context=edit"
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def update_post(wp_url, user, app_password, post_id, title, content, status):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}"
    payload = json.dumps({"title": title, "content": content, "status": status}).encode("utf-8")
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

    before = get_post(wp_url, user, app_pw, post_id)
    status = before.get("status")
    title = before.get("title", {}).get("raw", "")
    content = before.get("content", {}).get("raw", "")
    print(f"BEFORE: id={post_id} status={status} title={title!r}")

    if status not in ("draft", "pending", "private"):
        print(f"REFUSING: post {post_id} is currently '{status}', not a safe draft-like status. Aborting.")
        sys.exit(1)

    title_hits = title.count(OLD)
    content_hits = content.count(OLD)
    if title_hits != 1:
        print(f"REFUSING: expected exactly 1 occurrence of {OLD!r} in title, found {title_hits}. Aborting -- live content doesn't match the expected defect.")
        sys.exit(1)
    if content_hits != 1:
        print(f"REFUSING: expected exactly 1 occurrence of {OLD!r} in content, found {content_hits}. Aborting -- live content doesn't match the expected defect.")
        sys.exit(1)

    new_title = title.replace(OLD, NEW)
    new_content = content.replace(OLD, NEW)
    print(f"Fixing: {OLD!r} -> {NEW!r} (1 hit in title, 1 hit in content)")

    status_code, result = update_post(wp_url, user, app_pw, post_id, new_title, new_content, "publish")
    if status_code not in (200, 201):
        print(f"UPDATE FAILED: HTTP {status_code}: {result}")
        sys.exit(1)

    print(f"AFTER: id={result.get('id')} status={result.get('status')} title={result.get('title', {}).get('rendered')!r}")
    print(f"SUCCESS: post {post_id} title/content fixed and published -> {result.get('link')}")


if __name__ == "__main__":
    main()
