"""DESTRUCTIVE (but reversible by default): deletes ONE WordPress post via the
REST API. Moves the post to trash by default (recoverable from wp-admin for
the usual WP trash retention window); pass FORCE=true to bypass trash and
delete permanently.

Requires the caller to also pass CONFIRM_POST_ID equal to POST_ID, as a
fat-finger guard -- a workflow_dispatch typo (wrong id typed once) must not
silently delete the wrong post.

Used to clean up orphaned witness/control-run drafts that block their own
topic from ever being regenerated (agent_11's exact-normalized-title dedup
guard matches ANY existing post regardless of status -- see
agent_11_wordpress_integration.py::_duplicate_of).
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request


def delete_post(wp_url, user, app_password, post_id, force=False):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}"
    if force:
        url += "?force=true"
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"}, method="DELETE")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
    post_id = os.environ["POST_ID"].strip()
    confirm_post_id = os.environ.get("CONFIRM_POST_ID", "").strip()
    force = os.environ.get("FORCE", "false").strip().lower() == "true"

    if not post_id or confirm_post_id != post_id:
        print(f"ABORT: CONFIRM_POST_ID ('{confirm_post_id}') does not match POST_ID ('{post_id}')")
        sys.exit(1)

    try:
        result = delete_post(wp_url, user, app_pw, post_id, force=force)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code} deleting post {post_id}: {body}")
        sys.exit(1)

    print(f"post_id={post_id} force={force}")
    print(f"result status: {result.get('status')}")
    print(f"result id: {result.get('id')}")
    print(f"trashed (recoverable): {not force}")


if __name__ == "__main__":
    main()
