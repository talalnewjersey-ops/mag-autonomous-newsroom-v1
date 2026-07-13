"""Read-only diagnostic: fetches ALL Code Snippets entries (with full code)
and prints the id/name/scope/active of any whose code contains SEARCH_TERM.
Never writes anything.
"""
import base64
import json
import os
import urllib.request


def fetch_all(wp_url, user, app_password):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    results = []
    page = 1
    while True:
        url = f"{wp_url.rstrip('/')}/wp-json/code-snippets/v1/snippets?per_page=100&page={page}"
        req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            batch = json.loads(resp.read().decode("utf-8"))
        if not batch:
            break
        results.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return results


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
    term = os.environ["SEARCH_TERM"]

    snippets = fetch_all(wp_url, user, app_pw)
    print(f"Searched {len(snippets)} snippets for {term!r}")
    for s in snippets:
        code = s.get("code", "") or ""
        if term in code:
            print(f"MATCH id={s.get('id')} name={s.get('name')!r} scope={s.get('scope')} active={s.get('active')} code_length={len(code)}")


if __name__ == "__main__":
    main()
