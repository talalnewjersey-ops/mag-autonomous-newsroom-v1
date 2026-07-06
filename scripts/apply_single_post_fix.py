"""Applies a SINGLE, exact-string content fix to ONE WordPress post via the
REST API. Part of the published-content audit workstream (separate from the
article-generation pipeline).

Safety, per the user's explicit rules for this workstream:
  - Operates on exactly ONE post per invocation, never a batch.
  - The exact text to remove is read from a checked-in JSON "fix file"
    (audit/pending_fixes/<name>.json: {"post_id": ..., "old_text": ...}),
    not a shell/YAML env var -- avoids escaping risk with HTML-heavy text,
    and leaves the exact removed text versioned/auditable in git history.
  - Requires the OLD substring to be found EXACTLY `expected_count` times
    in the post's current raw content (defaults to 1) -- refuses to write
    if the count doesn't match, so a stale/already-changed article can
    never be silently mismatched. A count > 1 is only ever used for a
    single, identical, verbatim artifact repeated within ONE article
    (e.g. a literal "<p>---</p>" markdown-separator leak appearing many
    times) -- never for distinct texts across multiple articles.
  - Two fix-file shapes, mutually exclusive:
      1. {"post_id", "old_text", "expected_count", "new_text"?} -- replace
         an exact, verified-count substring in the post's raw CONTENT with
         `new_text` (defaults to "" -- a pure removal -- when omitted; e.g.
         used to drop an internal Tier/NEXUS marker while KEEPING the
         legitimate "Last Updated: <date>" text around it).
      2. {"post_id", "set_excerpt": "..."} -- set the post's EXCERPT field
         to an explicit, pre-approved value (used when the issue is an
         empty/auto-generated excerpt, not literal residue to remove).
  - Never touches title, status, slug, or any other field.
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


def update_post_field(wp_url, user, app_password, post_id, field, value):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}"
    payload = json.dumps({field: value}).encode("utf-8")
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

    post = fetch_post(wp_url, user, app_pw, post_id)

    if "set_excerpt" in fix:
        result = update_post_field(wp_url, user, app_pw, post_id, "excerpt", fix["set_excerpt"])
        print(f"Updated post {post_id} excerpt.")
        print("New excerpt (rendered):", result.get("excerpt", {}).get("rendered", ""))
    else:
        old_text = fix["old_text"]
        new_text = fix.get("new_text", "")
        expected_count = fix.get("expected_count", 1)
        content = post["content"]["raw"]

        count = content.count(old_text)
        if count != expected_count:
            print(f"REFUSING TO WRITE: expected exactly {expected_count} occurrence(s) of old_text, found {count}.")
            print("No change made. Fix old_text/expected_count to match the current live content exactly.")
            raise SystemExit(1)

        new_content = content.replace(old_text, new_text)
        result = update_post_field(wp_url, user, app_pw, post_id, "content", new_content)
        print(f"Updated post {post_id} content.")
        print("New content length:", len(result.get("content", {}).get("rendered", "")))

    with open(f"post_{post_id}_after_fix.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
