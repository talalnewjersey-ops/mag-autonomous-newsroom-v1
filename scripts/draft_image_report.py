#!/usr/bin/env python3
import requests, os, re
from base64 import b64encode
WP_URL = os.environ.get("WORDPRESS_URL","https://moneyabroadguide.com").rstrip("/")
WP_USER = os.environ.get("WORDPRESS_USERNAME","")
WP_PASS = os.environ.get("WORDPRESS_PASSWORD","")
creds = b64encode((WP_USER+":"+WP_PASS).encode()).decode()
HDR = {"Authorization":"Basic "+creds,"Accept":"application/json"}
all_posts = []
page = 1
while True:
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/posts", headers=HDR,
        params={"status":"draft","per_page":100,"page":page,
                "_fields":"id,title,featured_media,content"}, timeout=30)
    if r.status_code != 200:
        break
    data = r.json()
    if not data:
        break
    all_posts.extend(data)
    total_pages = int(r.headers.get("X-WP-TotalPages",1))
    if page >= total_pages:
        break
    page += 1
print("="*70)
print("RAPPORT IMAGES - ARTICLES EN DRAFT")
print("="*70)
print(f"Total drafts: {len(all_posts)}")
with_img = []
without_img = []
for post in all_posts:
    pid = post["id"]
    title = post["title"]["rendered"]
    featured = post.get("featured_media", 0)
    content = post.get("content",{}).get("rendered","")
    inline = len(re.findall(r'<img ', content, re.IGNORECASE))
    if featured and featured != 0:
        with_img.append((pid, title, featured, inline))
    else:
        without_img.append((pid, title, 0, inline))
print(f"\nARTICLES AVEC IMAGE FEATURED ({len(with_img)}):")
print("-"*70)
for pid, title, fid, inline in with_img:
    total = inline + 1
    print(f"  [{pid}] featured_id={fid} | inline={inline} | TOTAL={total}")
    print(f"         {title[:70]}")
print(f"\nARTICLES SANS IMAGE FEATURED ({len(without_img)}):")
print("-"*70)
for pid, title, fid, inline in without_img:
    status = "INLINE ONLY" if inline > 0 else "AUCUNE IMAGE"
    print(f"  [{pid}] featured=NON | inline={inline} | {status}")
    print(f"         {title[:70]}")
no_img = [p for p in without_img if p[3] == 0]
inline_only = [p for p in without_img if p[3] > 0]
print("\n"+"="*70)
print("RESUME FINAL:")
print(f"  Total drafts          : {len(all_posts)}")
print(f"  Avec image featured   : {len(with_img)}")
print(f"  Sans image featured   : {len(without_img)}")
print(f"  Sans AUCUNE image     : {len(no_img)}")
print(f"  Inline seulement      : {len(inline_only)}")
print("="*70)
