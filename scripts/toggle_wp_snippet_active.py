"""Write action: sets a Code Snippets entry's 'active' field directly.
Requires CONFIRM=yes. Used to force Code Snippets to recompute its cached
site-css bundle (activate/deactivate toggles appear to be what invalidates
that cache -- a content-only edit while already active did not).
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request


def set_active(wp_url, user, app_password, snippet_id, active):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/code-snippets/v1/snippets/{snippet_id}"
    payload = json.dumps({"active": active}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
    snippet_id = os.environ["SNIPPET_ID"]
    active = os.environ["ACTIVE"].lower() == "true"
    confirm = os.environ.get("CONFIRM", "").lower() == "yes"

    if not confirm:
        print("REFUSING: CONFIRM=yes not set. Aborting.")
        sys.exit(1)

    result = set_active(wp_url, user, app_pw, snippet_id, active)
    print(f"SUCCESS: id={result.get('id')} active={result.get('active')}")


if __name__ == "__main__":
    main()
