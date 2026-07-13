"""Write action: creates a NEW Code Snippets entry via code-snippets/v1/snippets
(POST), hardcoded to scope="site-css" -- this is CSS-only, output inertly in
<head> via wp_head, and cannot execute PHP. The scope is intentionally not
configurable from the caller: this script must never be used to create a
"php"/"global"/"single-use" scoped snippet (those execute arbitrary PHP on
every page load -- far too high blast-radius for a scripted one-off tool).

Reads the CSS from a file (CODE_FILE) to avoid workflow_dispatch input size
limits. Requires CONFIRM=yes as a deliberate safety gate.
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request


def create_snippet(wp_url, user, app_password, name, desc, code, active):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/code-snippets/v1/snippets"
    payload = json.dumps({
        "name": name,
        "desc": desc,
        "code": code,
        "scope": "site-css",  # hardcoded -- CSS only, never executable PHP
        "active": active,
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
    name = os.environ["SNIPPET_NAME"]
    desc = os.environ.get("SNIPPET_DESC", "")
    code_path = os.environ["CODE_FILE"]
    active = os.environ.get("ACTIVE", "true").lower() == "true"
    confirm = os.environ.get("CONFIRM", "").lower() == "yes"

    with open(code_path, encoding="utf-8") as f:
        code = f.read()

    print(f"About to create CSS snippet: name={name!r} active={active} code_length={len(code)}")
    print("--- code preview ---")
    print(code)
    print("--------------------")

    if not confirm:
        print("REFUSING: CONFIRM=yes not set. Aborting without writing.")
        sys.exit(1)

    status, result = create_snippet(wp_url, user, app_pw, name, desc, code, active)
    if status not in (200, 201):
        print(f"CREATE FAILED: HTTP {status}: {result}")
        sys.exit(1)

    print(f"SUCCESS: created snippet id={result.get('id')} scope={result.get('scope')} active={result.get('active')}")


if __name__ == "__main__":
    main()
