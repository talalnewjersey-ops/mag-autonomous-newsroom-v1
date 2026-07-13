"""Read-only diagnostic: lists published WordPress posts via the REST API --
id/slug/title/link/categories/tags -- for building internal-link inventories
(e.g. the Start Here page rebuild, 2026-07-13). Never writes anything.
"""
import base64
import json
import os
import urllib.request


def fetch_all_posts(wp_url, user, app_password, status, per_page=100):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    posts = []
    page_num = 1
    while True:
        url = (f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts?status={status}"
               f"&per_page={per_page}&page={page_num}"
               f"&_fields=id,title,slug,status,link,date")
        req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                batch = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"ERROR fetching page {page_num} (status={status}): {e}")
            break
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < per_page:
            break
        page_num += 1
    return posts


def _title_text(entry):
    title = entry.get("title", "")
    return title.get("rendered", "") if isinstance(title, dict) else title


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
    statuses = os.environ.get("STATUSES", "publish,draft")

    for status in statuses.split(","):
        status = status.strip()
        posts = fetch_all_posts(wp_url, user, app_pw, status)
        posts.sort(key=lambda p: _title_text(p).lower())
        print(f"\n===== {len(posts)} POST(S) status={status} =====\n")
        for p in posts:
            print(f"id={p.get('id')} | status={p.get('status')} | slug={p.get('slug')} | "
                  f"date={p.get('date')} | link={p.get('link')} | title={_title_text(p)}")


if __name__ == "__main__":
    main()
