"""Write action: updates ONE existing Redirection-plugin redirect's target
URL, via its REST API. Part of the GSC indexation audit workstream
(2026-07-28) -- create_redirects_batch.py can only create new redirects or
skip existing ones, it has no update path, so a redirect that already
exists but points at a stale intermediate hop needs this instead.

Safety, same house convention as apply_single_post_fix.py:
  - Operates on exactly ONE redirect id per invocation.
  - Refuses to write unless the redirect's CURRENT target exactly matches
    `expected_current_target` (read fresh via GET right before writing) --
    protects against updating the wrong rule or a rule that changed since
    it was last inspected.
  - The redirect's source URL, match_type, group_id and enabled state are
    read from the existing record and preserved unchanged; only
    action_data.url (the target) is modified.
"""
import base64
import json
import os
import urllib.error
import urllib.request


def _auth_header(user, app_password):
    return "Basic " + base64.b64encode(f"{user}:{app_password}".encode()).decode()


def get_redirect(wp_url, user, app_password, redirect_id):
    url = f"{wp_url.rstrip('/')}/wp-json/redirection/v1/redirect/{redirect_id}"
    req = urllib.request.Request(url, headers={"Authorization": _auth_header(user, app_password)})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def update_redirect_target(wp_url, user, app_password, redirect_id, current, new_target):
    url = f"{wp_url.rstrip('/')}/wp-json/redirection/v1/redirect/{redirect_id}"
    payload = json.dumps({
        "url": current["url"],
        "match_type": current.get("match_type", "url"),
        "action_type": current.get("action_type", "url"),
        "action_code": current.get("action_code", 301),
        "action_data": {"url": new_target},
        "group_id": current.get("group_id", 1),
        "enabled": current.get("enabled", True),
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST",
        headers={"Authorization": _auth_header(user, app_password), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
    redirect_id = os.environ["REDIRECT_ID"]
    expected_current_target = os.environ["EXPECTED_CURRENT_TARGET"]
    new_target = os.environ["NEW_TARGET"]

    current = get_redirect(wp_url, user, app_pw, redirect_id)
    actual_current_target = current.get("action_data", {}).get("url", "")

    print(f"BEFORE: id={redirect_id} url={current.get('url')!r} -> target={actual_current_target!r}")

    if actual_current_target.strip("/") != expected_current_target.strip("/"):
        print(f"REFUSING TO WRITE: expected current target {expected_current_target!r}, "
              f"found {actual_current_target!r}. No change made.")
        raise SystemExit(1)

    result = update_redirect_target(wp_url, user, app_pw, redirect_id, current, new_target)
    new_url_target = result.get("action_data", {}).get("url", "")
    print(f"AFTER: id={result.get('id')} url={result.get('url')!r} -> target={new_url_target!r}")

    if new_url_target.strip("/") != new_target.strip("/"):
        print("WARNING: resulting target does not match requested new_target -- verify manually.")
        raise SystemExit(1)

    print("SUCCESS: redirect target updated.")


if __name__ == "__main__":
    main()
