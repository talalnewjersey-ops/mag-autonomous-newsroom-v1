"""Read-only diagnostic: fetches ONE Code Snippets entry by ID and writes its
full code (name, scope, active state, code) to a JSON file, for artifact
upload -- avoids GitHub Actions per-line log truncation on large snippets
that print_wp_code_snippet.py hits. Never writes to WordPress.
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

    out_path = f"snippet_{snippet_id}_full.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2, ensure_ascii=False)

    print(f"Saved {out_path}")
    print(f"id={s.get('id')} name={s.get('name')!r} active={s.get('active')} scope={s.get('scope')}")
    print(f"code length: {len(s.get('code', ''))}")


if __name__ == "__main__":
    main()
