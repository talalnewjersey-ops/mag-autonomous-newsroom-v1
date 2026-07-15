"""Write action: updates an EXISTING Code Snippets entry's PHP code (scope
must be 'global', i.e. a PHP snippet -- not site-css). Higher blast radius
than update_wp_css_snippet.py since this is arbitrary PHP executed sitewide
on every page load. Safety gates:
  - refuses unless scope == 'global'
  - refuses unless the snippet's CURRENT code length matches EXPECTED_CURRENT_LENGTH
    (protects against clobbering a concurrent edit made since the caller last read it)
  - requires CONFIRM=yes
Reads new code from CODE_FILE.
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
    expected_current_length = int(os.environ["EXPECTED_CURRENT_LENGTH"])
    confirm = os.environ.get("CONFIRM", "").lower() == "yes"

    before = get_snippet(wp_url, user, app_pw, snippet_id)
    if before.get("scope") != "global":
        print(f"REFUSING: snippet {snippet_id} has scope={before.get('scope')!r}, not 'global'. Aborting.")
        sys.exit(1)

    current_len = len(before.get("code", "") or "")
    print(f"BEFORE: id={snippet_id} scope={before.get('scope')} active={before.get('active')} "
          f"code_length={current_len}")

    if current_len != expected_current_length:
        print(f"REFUSING: current code_length={current_len} does not match "
              f"EXPECTED_CURRENT_LENGTH={expected_current_length} -- snippet may have changed "
              f"since it was last read. Aborting without writing.")
        sys.exit(1)

    with open(code_path, encoding="utf-8") as f:
        code = f.read()

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
