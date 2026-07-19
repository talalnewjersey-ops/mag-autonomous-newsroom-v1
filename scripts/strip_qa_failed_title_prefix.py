"""Hotfix (2026-07-19): the previous one-off fix (fix_and_publish_post.py)
published post 48870 without noticing '[QA-FAILED] ' was baked into the
title text itself (not just a taxonomy tag, as the pipeline log implied).
This strips that literal prefix from the live title. Refuses to run unless
the title starts with the exact prefix, so it can never touch an unrelated
post's title.
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request

PREFIX = "[QA-FAILED] "


def get_post(wp_url, user, app_password, post_id):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}?context=edit"
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def update_title(wp_url, user, app_password, post_id, title):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}"
    payload = json.dumps({"title": title}).encode("utf-8")
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
    title = before.get("title", {}).get("raw", "")
    print(f"BEFORE: id={post_id} status={before.get('status')} title={title!r}")

    if not title.startswith(PREFIX):
        print(f"REFUSING: title does not start with {PREFIX!r}. Aborting -- nothing to strip.")
        sys.exit(1)

    new_title = title[len(PREFIX):]
    status_code, result = update_title(wp_url, user, app_pw, post_id, new_title)
    if status_code not in (200, 201):
        print(f"UPDATE FAILED: HTTP {status_code}: {result}")
        sys.exit(1)

    print(f"AFTER: id={result.get('id')} status={result.get('status')} title={result.get('title', {}).get('rendered')!r}")
    print(f"SUCCESS: post {post_id} title prefix stripped -> {result.get('link')}")


if __name__ == "__main__":
    main()
