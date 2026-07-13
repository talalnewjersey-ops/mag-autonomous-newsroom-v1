"""Write action: updates an EXISTING Code Snippets entry's code (and
optionally name/desc/active), scope is left untouched by this script (it
only ever operates on snippets that are already scope=site-css -- CSS-only).
Reads new code from CODE_FILE. Requires CONFIRM=yes.
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request


def get_snippet(wp_url, user, app_password, snippet_id):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/code-snippets/v1/snippets/{snippet_id}"
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def update_snippet(wp_url, user, app_password, snippet_id, code):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/code-snippets/v1/snippets/{snippet_id}"
    payload = json.dumps({"code": code}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
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
    code_path = os.environ["CODE_FILE"]
    confirm = os.environ.get("CONFIRM", "").lower() == "yes"

    before = get_snippet(wp_url, user, app_pw, snippet_id)
    if before.get("scope") != "site-css":
        print(f"REFUSING: snippet {snippet_id} has scope={before.get('scope')!r}, not 'site-css'. "
              f"This script only updates CSS-only snippets. Aborting.")
        sys.exit(1)

    with open(code_path, encoding="utf-8") as f:
        code = f.read()

    print(f"BEFORE: id={snippet_id} scope={before.get('scope')} active={before.get('active')} "
          f"code_length={len(before.get('code', '') or '')}")

    if not confirm:
        print("REFUSING: CONFIRM=yes not set. Aborting without writing.")
        sys.exit(1)

    status, result = update_snippet(wp_url, user, app_pw, snippet_id, code)
    if status not in (200, 201):
        print(f"UPDATE FAILED: HTTP {status}: {result}")
        sys.exit(1)

    print(f"AFTER: id={result.get('id')} scope={result.get('scope')} active={result.get('active')} "
          f"code_length={len(result.get('code', '') or '')}")
    print("SUCCESS")


if __name__ == "__main__":
    main()
