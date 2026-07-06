"""Read-only diagnostic: builds a full inventory of every published post
(id, slug, link, title, dates, categories, word count) PLUS an internal
link graph (which posts link to which, counted from content) so duplicate
groups can be assessed against objective signals -- not guessed.

Part of the published-content audit workstream, ÉTAPE 2 (duplicates)
PLANNING phase. Never writes to WordPress. Never deletes, redirects, or
merges anything.
"""
import base64
import json
import os
import re
import urllib.request
from collections import Counter


def _auth_header(user, app_password):
    creds = f"{user}:{app_password}"
    return "Basic " + base64.b64encode(creds.encode()).decode()


def fetch_all_published(wp_url, user, app_password, per_page=50):
    auth = _auth_header(user, app_password)
    posts = []
    page = 1
    while True:
        url = (f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts?status=publish&per_page={per_page}"
               f"&page={page}&_fields=id,title,slug,link,date,modified,content,categories")
        req = urllib.request.Request(url, headers={"Authorization": auth})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                batch = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"ERROR fetching page {page}: {e}")
            break
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    return posts


def fetch_categories(wp_url, user, app_password):
    auth = _auth_header(user, app_password)
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/categories?per_page=100&_fields=id,name"
    req = urllib.request.Request(url, headers={"Authorization": auth})
    with urllib.request.urlopen(req, timeout=30) as resp:
        cats = json.loads(resp.read().decode("utf-8"))
    return {c["id"]: c["name"] for c in cats}


def _strip_html_light(html):
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", text)


_LINK_RE = re.compile(r'href="(https?://moneyabroadguide\.com/[^"#?]+/?)"')


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]

    posts = fetch_all_published(wp_url, user, app_pw)
    print(f"Fetched {len(posts)} published posts.")
    cat_names = fetch_categories(wp_url, user, app_pw)

    # normalize every post's own link for matching against found hrefs
    def _norm(url):
        return url.rstrip("/").lower()

    link_by_norm = {_norm(p["link"]): p["id"] for p in posts}

    inbound_counts = Counter()
    outbound_links_by_post = {}

    inventory = []
    for p in posts:
        content_html = p.get("content", {}).get("rendered", "")
        content_text = _strip_html_light(content_html)
        word_count = len(content_text.split())

        hrefs = _LINK_RE.findall(content_html)
        target_ids = set()
        for href in hrefs:
            target_id = link_by_norm.get(_norm(href))
            if target_id and target_id != p["id"]:
                target_ids.add(target_id)
        outbound_links_by_post[p["id"]] = sorted(target_ids)
        for tid in target_ids:
            inbound_counts[tid] += 1

        inventory.append({
            "id": p["id"],
            "slug": p["slug"],
            "link": p["link"],
            "title": p.get("title", {}).get("rendered", ""),
            "date": p.get("date"),
            "modified": p.get("modified"),
            "categories": [cat_names.get(c, str(c)) for c in p.get("categories", [])],
            "word_count": word_count,
        })

    for item in inventory:
        item["inbound_internal_links"] = inbound_counts.get(item["id"], 0)
        item["outbound_internal_links"] = len(outbound_links_by_post.get(item["id"], []))

    inventory.sort(key=lambda x: x["slug"])

    print("\n===== FULL INVENTORY =====\n")
    for item in inventory:
        print(f"id={item['id']} | slug={item['slug']} | words={item['word_count']} | "
              f"inbound={item['inbound_internal_links']} | outbound={item['outbound_internal_links']} | "
              f"date={item['date']} | categories={item['categories']}")
        print(f"    title: {item['title']}")
        print(f"    link: {item['link']}")

    with open("duplicate_inventory_results.json", "w", encoding="utf-8") as f:
        json.dump({"total_posts": len(inventory), "posts": inventory}, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
