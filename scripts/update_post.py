#!/usr/bin/env python3
"""
NEXUS-14: Push polished article content back to a WordPress draft post.
Reads drafts/wp_post_<id>_content_revised.html and updates the post via the
REST API, keeping status as draft.
"""
import os
import time
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
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; NEXUS14/2.0)",
}

content_path = f"drafts/wp_post_{POST_ID}_content_revised.html"
with open(content_path, "r", encoding="utf-8") as f:
    content = f.read()

payload = {
    "title": "Best Way to Send Money From the USA to Canada (2026 Guide)",
    "content": content,
    "slug": "best-way-to-send-money-usa-to-canada-2026",
    "status": "draft",
    "meta": {
        "_yoast_wpseo_title": "Best Way to Send Money From the USA to Canada (2026) | MoneyAbroadGuide",
        "_yoast_wpseo_metadesc": "Complete guide to the best way to send money from the USA to Canada in 2026. Compare top services, fees, exchange rates and expert tips for USA residents.",
        "_yoast_wpseo_focuskw": "best way to send money from USA to Canada",
    },
}

url = f"{WP_URL}/wp-json/wp/v2/posts/{POST_ID}"
print("POST", url)

r = None
for attempt in range(1, 6):
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    print(f"Status: {r.status_code} (attempt {attempt})")
    if r.status_code in (200, 201):
        break
    if r.status_code in (403, 429) or r.status_code >= 500:
        wait = 2 ** attempt
        print(f"  retrying in {wait}s...")
        time.sleep(wait)
        continue
    break

r.raise_for_status()
result = r.json()
print("Updated post ID:", result.get("id"))
print("Status:", result.get("status"))
print("Slug:", result.get("slug"))
print("Link:", result.get("link"))
