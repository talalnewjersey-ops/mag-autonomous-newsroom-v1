"""Applies a SINGLE, exact-string content fix to ONE WordPress post via the
REST API. Part of the published-content audit workstream (separate from the
article-generation pipeline).

Safety, per the user's explicit rules for this workstream:
  - Operates on exactly ONE post per invocation, never a batch.
  - The exact text to remove is read from a checked-in JSON "fix file"
    (audit/pending_fixes/<name>.json: {"post_id": ..., "old_text": ...}),
    not a shell/YAML env var -- avoids escaping risk with HTML-heavy text,
    and leaves the exact removed text versioned/auditable in git history.
  - Requires the OLD substring to be found EXACTLY ONCE in the post's
    current raw content -- refuses to write if it's missing or ambiguous
    (0 or >1 occurrences), so a stale/already-changed article can never be
    silently mismatched.
  - Never touches title, status, slug, or any other field -- only content.
  - Caller is expected to have already written a pre-edit backup (see
    scripts/fetch_one_post.py) before this runs.
"""
import base64
import json
import os
import urllib.request


def fetch_post(wp_url, user, app_password, post_id):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}?context=edit"
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def update_post_content(wp_url, user, app_password, post_id, new_content):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}"
    payload = json.dumps({"content": new_content}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST", headers={
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
    fix_path = os.environ["FIX_FILE"]

    with open(fix_path, "r", encoding="utf-8") as f:
        fix = json.load(f)
    post_id = fix["post_id"]
    old_text = fix["old_text"]

    post = fetch_post(wp_url, user, app_pw, post_id)
    content = post["content"]["raw"]

    count = content.count(old_text)
    if count != 1:
        print(f"REFUSING TO WRITE: expected exactly 1 occurrence of OLD_TEXT, found {count}.")
        print("No change made. Fix OLD_TEXT to match the current live content exactly.")
        raise SystemExit(1)

    new_content = content.replace(old_text, "")
    result = update_post_content(wp_url, user, app_pw, post_id, new_content)

    print(f"Updated post {post_id}.")
    print("New content length:", len(result.get("content", {}).get("rendered", "")))

    with open(f"post_{post_id}_after_fix.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
