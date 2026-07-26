"""Read-only diagnostic: extracts EVERY internal moneyabroadguide.com href
from every published post and page's actual content, and checks each one
against the current live slug set.

Built 2026-07-26, same 404 audit chantier. The Redirection 404 log (see
fetch_redirection_404_log.py) only captures links someone/some bot has
actually clicked -- a broken link buried in a rarely-visited "related
articles" block can sit there for months without ever generating a log
entry. Found by hand on post 46652 (16 of 18 links in its related-articles
list are dead) while investigating the log-based list of 9 -- this script
exists because that finding means the log-based list is an undercount, not
because the log approach was wrong for what it measures.

Never writes to WordPress.
"""
import base64
import json
import os
import re
import urllib.request

_LINK_RE = re.compile(r'href="https?://(?:www\.)?moneyabroadguide\.com(/[^"#?]*)"', re.IGNORECASE)


def _auth_header(user, app_password):
    return "Basic " + base64.b64encode(f"{user}:{app_password}".encode()).decode()


def fetch_all(wp_url, user, app_password, endpoint, per_page=50):
    auth = _auth_header(user, app_password)
    items = []
    page = 1
    while True:
        url = (f"{wp_url.rstrip('/')}/{endpoint}?status=publish&per_page={per_page}"
               f"&page={page}&context=edit&_fields=id,slug,link,content")
        req = urllib.request.Request(url, headers={"Authorization": auth})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                batch = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"ERROR fetching {endpoint} page {page}: {e}")
            break
        if not batch:
            break
        items.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    return items


def norm(path):
    return path.split("?")[0].strip("/").lower()


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]

    posts = fetch_all(wp_url, user, app_pw, "wp-json/wp/v2/posts")
    pages = fetch_all(wp_url, user, app_pw, "wp-json/wp/v2/pages")
    all_items = [{"type": "post", **p} for p in posts] + [{"type": "page", **p} for p in pages]
    print(f"Scanned {len(posts)} published posts + {len(pages)} published pages.")

    live_slugs = {norm(it["slug"]) for it in all_items}
    live_slugs.add("")  # homepage

    total_links = 0
    broken = []
    for it in all_items:
        content = it.get("content", {}).get("raw", "")
        seen_in_this_post = set()
        for m in _LINK_RE.finditer(content):
            path = m.group(1)
            n = norm(path)
            total_links += 1
            if n in live_slugs:
                continue
            if n.startswith("wp-content") or n.startswith("wp-admin") or n.startswith("wp-json"):
                continue
            if path in seen_in_this_post:
                continue
            seen_in_this_post.add(path)
            broken.append({
                "source_type": it["type"], "source_id": it["id"], "source_slug": it["slug"],
                "source_link": it["link"], "dead_target": path,
            })

    print(f"\nTotal internal hrefs found: {total_links}")
    print(f"Broken internal links (target not a live published slug): {len(broken)}")

    by_source = {}
    for b in broken:
        by_source.setdefault((b["source_type"], b["source_slug"]), []).append(b["dead_target"])

    print(f"\n===== BROKEN LINKS GROUPED BY SOURCE PAGE ({len(by_source)} source pages affected) =====")
    for (stype, sslug), targets in sorted(by_source.items(), key=lambda x: -len(x[1])):
        print(f"\n[{stype}] {sslug}  ({len(targets)} broken link(s))")
        for t in targets:
            print(f"    -> {t}")

    with open("all_broken_internal_links.json", "w", encoding="utf-8") as f:
        json.dump(broken, f, indent=2, ensure_ascii=False)
    print(f"\nSaved full list ({len(broken)} entries) to all_broken_internal_links.json")


if __name__ == "__main__":
    main()
