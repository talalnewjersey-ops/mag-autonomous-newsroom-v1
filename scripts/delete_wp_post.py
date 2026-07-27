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

--- 2026-07-27 addition: auto-redirect on delete of a PUBLISHED post ---
Root cause fixed here (found during the pre-production 404 audit): this
script previously deleted a post's row with no trace of where its public
URL used to point -- fine for a draft (never had a public URL), but for a
published post it silently created a dead URL with nothing telling
visitors/Google where the content went.

STATUS CHECK: a GET on the post (context=edit) is made right before
deleting, and its live `status` field decides the branch -- not a guess,
not the caller's say-so. `status == "publish"` -> redirect branch below.
Any other status (draft/pending/private/future -- never had a public URL)
-> delete proceeds exactly as before, no redirect created.

REDIRECT TARGET: this script NEVER guesses a topical match on its own.
  - REDIRECT_TO (optional input) is the preferred path -- a HUMAN supplies
    the exact target at the moment they call this script, same as this
    session's own 48787->47159 / 48832->47092 calls. This is the only way
    a content-based redirect target gets chosen.
  - If REDIRECT_TO is omitted, falls back to the post's own PRIMARY
    CATEGORY archive URL (first category ID returned by the REST API).
    This is a safe STRUCTURAL default, not a content guess -- a post's own
    assigned category is by definition topically related to it.
  - If the post has no category at all and no REDIRECT_TO was given, the
    script ABORTS without deleting -- silently redirecting to the
    homepage would be worse than the dead URL it's trying to prevent.
  - If redirect CREATION fails for any reason, the delete is also
    aborted -- never end up in the exact state this fix exists to
    avoid (post gone, no redirect, nobody told).
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request

# Same group every existing manually-created redirect on this site uses
# (confirmed via GET /wp-json/redirection/v1/redirect during the 404
# audit -- group_id=1 on all 125 entries as of 2026-07-27).
REDIRECTION_GROUP_ID = 1


def _auth_header(user, app_password):
    return "Basic " + base64.b64encode(f"{user}:{app_password}".encode()).decode()


def get_post(wp_url, user, app_password, post_id):
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}?context=edit"
    req = urllib.request.Request(url, headers={"Authorization": _auth_header(user, app_password)})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_category_link(wp_url, user, app_password, category_id):
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/categories/{category_id}?_fields=link,slug"
    req = urllib.request.Request(url, headers={"Authorization": _auth_header(user, app_password)})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8")).get("link")


def create_redirect(wp_url, user, app_password, source_path, target_url):
    url = f"{wp_url.rstrip('/')}/wp-json/redirection/v1/redirect"
    payload = json.dumps({
        "url": source_path, "match_type": "url", "action_type": "url",
        "action_code": 301, "action_data": {"url": target_url},
        "group_id": REDIRECTION_GROUP_ID,
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Authorization": _auth_header(user, app_password), "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def delete_post(wp_url, user, app_password, post_id, force=False):
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}"
    if force:
        url += "?force=true"
    req = urllib.request.Request(url, headers={"Authorization": _auth_header(user, app_password)}, method="DELETE")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
    post_id = os.environ["POST_ID"].strip()
    confirm_post_id = os.environ.get("CONFIRM_POST_ID", "").strip()
    force = os.environ.get("FORCE", "false").strip().lower() == "true"
    redirect_to = os.environ.get("REDIRECT_TO", "").strip()

    if not post_id or confirm_post_id != post_id:
        print(f"ABORT: CONFIRM_POST_ID ('{confirm_post_id}') does not match POST_ID ('{post_id}')")
        sys.exit(1)

    before = get_post(wp_url, user, app_pw, post_id)
    status = before.get("status")
    slug = before.get("slug", "")
    source_path = f"/{slug}/"
    print(f"BEFORE: id={post_id} status={status} slug={slug!r} categories={before.get('categories')}")

    if status == "publish":
        target = redirect_to
        target_source = "explicit REDIRECT_TO"
        if not target:
            cats = before.get("categories") or []
            if not cats:
                print("ABORT: post is published, has no category, and no REDIRECT_TO was given -- "
                      "refusing to guess a redirect target. Re-run with REDIRECT_TO set.")
                sys.exit(1)
            target = get_category_link(wp_url, user, app_pw, cats[0])
            target_source = f"category fallback (category_id={cats[0]})"
            if not target:
                print(f"ABORT: could not resolve a link for category_id={cats[0]}. Re-run with REDIRECT_TO set.")
                sys.exit(1)

        print(f"Post is published -- creating 301 redirect {source_path} -> {target} ({target_source})")
        try:
            redirect_result = create_redirect(wp_url, user, app_pw, source_path, target)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            print(f"ABORT: redirect creation failed (HTTP {e.code}): {body}. Post NOT deleted.")
            sys.exit(1)
        print(f"Redirect created: id={redirect_result.get('id')}")
    else:
        print(f"Post status is {status!r} (never publicly reachable) -- skipping redirect, nothing to redirect from.")

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
