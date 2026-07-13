"""Read-only diagnostic: fetches ONE Code Snippets entry by ID and prints its
full code, name, scope, active state -- via code-snippets/v1/snippets/{id}.
Never writes anything.
"""
import base64
import json
import os
import urllib.request


def fetch_snippet(wp_url, user, app_password, snippet_id):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/code-snippets/v1/snippets/{snippet_id}"
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
    snippet_id = os.environ["SNIPPET_ID"]

    s = fetch_snippet(wp_url, user, app_pw, snippet_id)
    print(f"id={s.get('id')}")
    print(f"name={s.get('name')!r}")
    print(f"scope={s.get('scope')}")
    print(f"active={s.get('active')}")
    print(f"priority={s.get('priority')}")
    print(f"desc={s.get('desc')!r}")
    print("===CODE-START===")
    print(s.get("code", ""))
    print("===CODE-END===")


if __name__ == "__main__":
    main()
