"""Read-only diagnostic: lists Code Snippets plugin entries via its own REST
API namespace (code-snippets/v1/snippets) -- id/name/scope/active/priority.
Never writes anything. Used to understand existing sitewide CSS snippets
(e.g. "MAG Performance & Accessibility Fixes") before adding a new one.
"""
import base64
import json
import os
import urllib.request


def fetch_snippets(wp_url, user, app_password):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/code-snippets/v1/snippets?per_page=100"
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]

    snippets = fetch_snippets(wp_url, user, app_pw)
    print(f"===== {len(snippets)} SNIPPET(S) FOUND =====")
    for s in snippets:
        print(f"id={s.get('id')} | name={s.get('name')!r} | scope={s.get('scope')} | "
              f"active={s.get('active')} | priority={s.get('priority')}")
    print()
    print("===== FULL RAW JSON =====")
    print(json.dumps(snippets, indent=2))


if __name__ == "__main__":
    main()
