"""Read-only diagnostic: lists every draft post on WordPress via the REST API
(status=publish,draft requires authentication for the draft half -- the
public API forbids status=draft unauthenticated). Never writes anything.

Used to identify residual drafts from prior control runs (e.g. dead-title
collisions like posts 48418/48466) before a manual wp-admin cleanup.
"""
import base64
import json
import os
import urllib.request


def fetch_all_drafts(wp_url, user, app_password, per_page=100):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    drafts = []
    page = 1
    while True:
        url = (f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts?status=draft&per_page={per_page}"
               f"&page={page}&_fields=id,title,slug,date,modified,link")
        req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                batch = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"ERROR fetching page {page}: {e}")
            break
        if not batch:
            break
        drafts.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    return drafts


def _title_text(post):
    title = post.get("title", "")
    return title.get("rendered", "") if isinstance(title, dict) else title


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]

    drafts = fetch_all_drafts(wp_url, user, app_pw)
    drafts.sort(key=lambda d: d.get("date", ""), reverse=True)

    print(f"\n===== {len(drafts)} DRAFT POST(S) FOUND =====\n")
    for d in drafts:
        print(f"id={d.get('id')} | date={d.get('date')} | modified={d.get('modified')} | "
              f"slug={d.get('slug')} | title={_title_text(d)}")


if __name__ == "__main__":
    main()
