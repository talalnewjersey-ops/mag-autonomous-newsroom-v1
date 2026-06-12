#!/usr/bin/env python3
"""
NEXUS-14: Fetch WordPress post content (raw + metadata) for editorial review.
Writes drafts/wp_post_<id>_content.html and drafts/wp_post_<id>_meta.json
"""
import os
import json
import base64
import requests

WP_URL = os.environ.get("WORDPRESS_URL", "https://moneyabroadguide.com").rstrip("/")
WP_USER = os.environ.get("WORDPRESS_USERNAME", "")
WP_PASS = os.environ.get("WORDPRESS_PASSWORD", "")
POST_ID = os.environ.get("POST_ID", "").strip()

if not POST_ID:
    raise SystemExit("POST_ID env var is required")

creds = base64.b64encode((WP_USER + ":" + WP_PASS).encode()).decode()
headers = {
    "Authorization": "Basic " + creds,
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; NEXUS14/2.0)",
}

url = f"{WP_URL}/wp-json/wp/v2/posts/{POST_ID}?context=edit"
print("GET", url)
r = requests.get(url, headers=headers, timeout=60)
print("Status:", r.status_code)
r.raise_for_status()
post = r.json()

content = post.get("content", {}).get("raw") or post.get("content", {}).get("rendered") or ""
title = post.get("title", {}).get("raw") or post.get("title", {}).get("rendered") or ""

os.makedirs("drafts", exist_ok=True)

with open(f"drafts/wp_post_{POST_ID}_content.html", "w", encoding="utf-8") as f:
    f.write(content)

meta = {
    "id": post.get("id"),
    "title": title,
    "slug": post.get("slug"),
    "status": post.get("status"),
    "link": post.get("link"),
    "categories": post.get("categories"),
    "author": post.get("author"),
    "date": post.get("date"),
    "modified": post.get("modified"),
    "featured_media": post.get("featured_media"),
    "yoast_meta": {
        k: v for k, v in (post.get("meta") or {}).items()
        if "yoast" in k.lower()
    },
}
with open(f"drafts/wp_post_{POST_ID}_meta.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2)

print("Title:", title)
print("Status:", post.get("status"))
print("Word count:", len(content.split()))
print("Wrote drafts/wp_post_{}_content.html and _meta.json".format(POST_ID))
