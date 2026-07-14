"""Write action: creates a NEW Code Snippets entry with scope="global" (PHP),
arbitrary PHP body supplied by the caller. Unlike create_wp_php_css_snippet.py
(which constrains generation to a fixed static-echo template), this script
accepts real logic -- use ONLY after explicit user approval for the specific
functionality being added, and review the code before running with
CONFIRM=yes (the script prints it first regardless).
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
        "scope": "global",
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
        body = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, {"raw": body[:500]}


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

    print(f"About to create PHP snippet (scope=global): name={name!r} active={active}")
    print("--- code ---")
    print(code)
    print("------------")

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
