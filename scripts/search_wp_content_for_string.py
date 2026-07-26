"""Read-only diagnostic: searches the raw content of every post (any
status the caller lists) for a literal substring, and prints which posts
contain it. Never writes to WordPress.

Built 2026-07-26 to confirm no other post's href already points at a
draft's about-to-change slug before renaming it -- a plain string search
in the actual stored content, not an inference from titles/slugs alone.
"""
import base64
import json
import os
import urllib.request


def _auth_header(user, app_password):
    return "Basic " + base64.b64encode(f"{user}:{app_password}".encode()).decode()


def fetch_all(wp_url, user, app_password, status, per_page=50):
    auth = _auth_header(user, app_password)
    posts = []
    page = 1
    while True:
        url = (f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts?status={status}&per_page={per_page}"
               f"&page={page}&context=edit&_fields=id,slug,link,status,content")
        req = urllib.request.Request(url, headers={"Authorization": auth})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                batch = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"ERROR fetching {status} page {page}: {e}")
            break
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    return posts


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
    needle = os.environ["SEARCH_STRING"]
    statuses = [s.strip() for s in os.environ.get("STATUSES", "publish,draft").split(",") if s.strip()]

    total = 0
    hits = 0
    for status in statuses:
        posts = fetch_all(wp_url, user, app_pw, status)
        total += len(posts)
        for p in posts:
            content = p.get("content", {}).get("raw", "") or p.get("content", {}).get("rendered", "")
            if needle in content:
                hits += 1
                print(f"MATCH: id={p['id']} status={p['status']} slug={p['slug']} link={p['link']}")

    print(f"Searched {total} post(s) across statuses={statuses} for {needle!r}.")
    print(f"Total matches: {hits}")


if __name__ == "__main__":
    main()
