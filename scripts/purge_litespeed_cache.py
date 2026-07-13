"""Write action: temporarily activates the existing 'MAG Purge All' Code
Snippet (id configurable, PHP scope -- registers a REST route that calls
LiteSpeed's purge-all functions), calls that route once, then deactivates
the snippet again. Minimizes the window where extra PHP code is live to
just the duration of this script. Requires CONFIRM=yes.
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request


def _auth_header(user, app_password):
    return "Basic " + base64.b64encode(f"{user}:{app_password}".encode()).decode()


def set_active(wp_url, user, app_password, snippet_id, active):
    url = f"{wp_url.rstrip('/')}/wp-json/code-snippets/v1/snippets/{snippet_id}"
    payload = json.dumps({"active": active}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Authorization": _auth_header(user, app_password), "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def call_purge(wp_url, user, app_password, route):
    url = f"{wp_url.rstrip('/')}/wp-json/{route}"
    req = urllib.request.Request(
        url, data=b"{}", method="POST",
        headers={"Authorization": _auth_header(user, app_password), "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, {"raw": body[:500]}


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
    snippet_id = os.environ["SNIPPET_ID"]
    purge_route = os.environ.get("PURGE_ROUTE", "mag/v1/purge-all")
    confirm = os.environ.get("CONFIRM", "").lower() == "yes"

    if not confirm:
        print("REFUSING: CONFIRM=yes not set. Aborting without activating anything.")
        sys.exit(1)

    print(f"Activating snippet {snippet_id}...")
    result = set_active(wp_url, user, app_pw, snippet_id, True)
    print(f"  active={result.get('active')}")

    time.sleep(2)  # give WP a moment to register the new rest route

    print(f"Calling purge route /{purge_route}...")
    status, body = call_purge(wp_url, user, app_pw, purge_route)
    print(f"  HTTP {status}: {body}")

    print(f"Deactivating snippet {snippet_id}...")
    result = set_active(wp_url, user, app_pw, snippet_id, False)
    print(f"  active={result.get('active')}")

    if status not in (200, 201):
        print("PURGE CALL FAILED (snippet deactivated regardless -- see status above)")
        sys.exit(1)

    print("SUCCESS: cache purge triggered, snippet deactivated again")


if __name__ == "__main__":
    main()
