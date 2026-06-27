#!/usr/bin/env python3
"""
NEXUS-14 — Image Backfill V2 (SAFE MODE)

Adds ONLY a featured image to already-published posts that have none.

SAFETY GUARANTEES (V2):
  * NEVER modifies post content (no Gutenberg/Elementor/body rewrite).
  * NEVER inserts inline images.
  * Only sets `featured_media` on the post + writes media metadata.
  * Photographic prompts only — no infographics, charts, diagrams, or text.
  * Rejects placeholder images (never sets a blank placeholder as featured).
  * Idempotent: skips any post that already has featured_media.

Reuses Agent 10 (ImageProductionAgent) for Gemini/Nano Banana generation
and WordPress Media Library upload. Does NOT use Agent 09's graphic prompts.
No AWS. Secrets: GEMINI_API_KEY, NANO_BANANA_KEY, WORDPRESS_URL,
WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD.
"""

import os
import re
import sys
import json
import asyncio
import argparse
import tempfile
from pathlib import Path
from datetime import datetime

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agents.agent_10_image_production import ImageProductionAgent

WP_URL = os.getenv("WORDPRESS_URL", "").rstrip("/")
WP_USER = os.getenv("WORDPRESS_USERNAME", "")
WP_PASS = os.getenv("WORDPRESS_APP_PASSWORD", "")
AUTH = (WP_USER, WP_PASS)
REST = f"{WP_URL}/wp-json/wp/v2"

PHOTO_STYLE = (
    "ultra realistic editorial photograph, professional DSLR, natural lighting, "
    "shallow depth of field, real people, authentic candid moment, documentary style, "
    "high detail, 16:9 aspect ratio. "
    "STRICTLY NO text, NO words, NO captions, NO logos, NO watermark, "
    "NO infographic, NO chart, NO diagram, NO illustration, NO cartoon, NO screenshot."
    "NO LOGOS. NO BRAND NAMES. NO COMPANY NAMES. NO BANK NAMES. "
    "NO INTERAC. NO SCOTIABANK. NO RBC. NO TD. NO BMO. "
    "NO READABLE TEXT. NO SIGNAGE. NO NAMEPLATES. NO COMPUTER SCREENS. "
    "NO POSTERS. NO DOCUMENTS WITH TEXT. NO LETTERS. NO WORDS. NO WATERMARKS. "
    "All surfaces must be blank, generic and unbranded."
)

MARKET_SCENE = {
    "USA": "real newcomer family in an authentic United States setting — modern American bank branch, "
           "apartment, or financial advisor meeting; diverse multicultural people; warm natural light",
    "CANADA": "real newcomer family in an authentic Canadian setting — Toronto or Vancouver bank branch, "
              "apartment, or advisor meeting; diverse multicultural people; warm natural light",
    "": "real diverse newcomer family in an authentic North American financial setting; "
        "candid, welcoming atmosphere; natural light",
}


def wp_get(path, **params):
    r = requests.get(f"{REST}{path}", params=params, auth=AUTH, timeout=60)
    r.raise_for_status()
    return r.json()


def wp_post(path, payload):
    r = requests.post(f"{REST}{path}", json=payload, auth=AUTH, timeout=90)
    r.raise_for_status()
    return r.json()


def fetch_published_posts(max_pages=20):
    posts, page = [], 1
    while page <= max_pages:
        batch = wp_get("/posts", status="publish", per_page=100, page=page,
                       _fields="id,title,featured_media,categories,link,slug")
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return posts


def needs_featured(post):
    return not post.get("featured_media")


def market_of(post, market_filter):
    if not market_filter:
        return True
    title = (post.get("title") or {}).get("rendered", "").lower()
    is_ca = any(k in title for k in ["canada", "canadian", "cra", "tfsa", "rrsp"])
    is_us = any(k in title for k in ["usa", "u.s.", "united states", "irs", "ssn", "401k"])
    if market_filter.upper() == "CANADA":
        return is_ca or not is_us
    if market_filter.upper() == "USA":
        return is_us or not is_ca
    return True


def build_featured_prompt(post, market):
    title = (post.get("title") or {}).get("rendered", "Newcomer finance guide")
    title = re.sub(r"<[^>]+>", "", title)
    scene = MARKET_SCENE.get((market or "").upper(), MARKET_SCENE[""])
    seo_slug = re.sub(r"[^a-z0-9]+", "-",
                      (post.get("slug") or f"post-{post['id']}").lower()).strip("-")
    return {
        "featured_image": {
            "type": "featured",
            "prompt": f"{scene}. Context: {title}. {PHOTO_STYLE}",
            "alt_text": f"{title} — newcomer financial guidance",
            "caption": title,
            "description": f"Editorial photograph illustrating: {title}.",
            "filename": f"{seo_slug}-featured",
            "aspect_ratio": "16:9",
        }
    }


def is_placeholder(img):
    fn = (img.get("filename") or "").lower()
    status = (img.get("status") or "").upper()
    if "placeholder" in fn:
        return True
    if status and status not in ("SUCCESS",):
        return True
    size = img.get("file_size_bytes", 0)
    if size and size < 20000:
        return True
    return False


async def process_post(post, workdir, dry_run, market):
    pid = post["id"]
    title = re.sub(r"<[^>]+>", "", (post.get("title") or {}).get("rendered", ""))
    print(f"\n=== Post {pid}: {title[:70]} ===")

    out_dir = workdir / f"post_{pid}"
    out_dir.mkdir(parents=True, exist_ok=True)

    prompts = build_featured_prompt(post, market)
    prompts_path = out_dir / "image_prompts.json"
    prompts_path.write_text(json.dumps({"prompts": prompts}, indent=2,
                                       ensure_ascii=False), encoding="utf-8")

    if dry_run:
        return {"post_id": pid, "status": "DRY_RUN",
                "prompt": prompts["featured_image"]["prompt"][:120]}

    a10 = ImageProductionAgent(config={})
    await a10.run(image_prompts_path=str(prompts_path),
                  output_dir=str(out_dir), min_images=1)

    gen_report = out_dir / "generated_images_report.json"
    if not gen_report.exists():
        return {"post_id": pid, "status": "NO_REPORT"}
    images = json.loads(gen_report.read_text(encoding="utf-8")).get("images", [])

    featured = next((i for i in images
                     if i.get("type") == "featured"
                     and i.get("wp_media_id")
                     and not is_placeholder(i)), None)
    if not featured:
        return {"post_id": pid, "status": "REJECTED_NO_REAL_IMAGE",
                "detail": "generation failed or returned placeholder only"}

    mid = featured["wp_media_id"]

    try:
        wp_post(f"/media/{mid}", {
            "alt_text": featured.get("alt_text", ""),
            "title": featured.get("alt_text", "") or title,
            "caption": featured.get("caption", ""),
            "description": featured.get("description", ""),
        })
    except Exception as e:
        print(f"  [warn] media metadata update failed: {e}")

    updated = wp_post(f"/posts/{pid}", {"featured_media": mid})

    return {"post_id": pid, "status": "FEATURED_SET",
            "featured_media": mid,
            "alt": featured.get("alt_text", ""),
            "link": updated.get("link")}


async def main_async(args):
    print(f"NEXUS-14 Image Backfill V2 (SAFE) — {datetime.now().isoformat()}")
    print(f"WP: {WP_URL}  dry_run={args.dry_run}  market={args.market or 'ALL'}")

    posts = fetch_published_posts()
    print(f"Fetched {len(posts)} published posts")

    if args.article_ids:
        wanted = {int(x) for x in re.split(r"[,\s]+", args.article_ids) if x.strip()}
        # Explicit IDs: process exactly these posts even if they already
        # have a featured image (allows regeneration/replacement).
        candidates = [p for p in posts if p["id"] in wanted]
    else:
        # No IDs: preserve original behavior — imageless posts only.
        candidates = [p for p in posts if needs_featured(p)]
    if args.category:
        cat = int(args.category)
        candidates = [p for p in candidates if cat in (p.get("categories") or [])]
    if args.market:
        candidates = [p for p in candidates if market_of(p, args.market)]
    if args.max_articles:
        candidates = candidates[: args.max_articles]

    print(f"Candidates (no featured image): {len(candidates)} -> "
          f"{[p['id'] for p in candidates]}")

    results = []
    workdir = Path(tempfile.mkdtemp(prefix="backfill_v2_"))
    for post in candidates:
        try:
            results.append(await process_post(post, workdir, args.dry_run, args.market))
        except Exception as e:
            print(f"  [ERROR] post {post['id']}: {e}")
            results.append({"post_id": post["id"], "status": "ERROR", "error": str(e)})
        await asyncio.sleep(args.delay)

    report = {
        "timestamp": datetime.now().isoformat(),
        "mode": "SAFE_FEATURED_ONLY",
        "dry_run": args.dry_run,
        "candidates": [p["id"] for p in candidates],
        "results": results,
        "summary": {
            "total": len(results),
            "featured_set": sum(1 for r in results if r.get("status") == "FEATURED_SET"),
            "rejected": sum(1 for r in results if r.get("status") == "REJECTED_NO_REAL_IMAGE"),
            "errors": sum(1 for r in results if r.get("status") == "ERROR"),
            "dry_run": sum(1 for r in results if r.get("status") == "DRY_RUN"),
        },
    }
    out = Path("output"); out.mkdir(exist_ok=True)
    (out / "backfill_images_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n==== SUMMARY ====")
    print(json.dumps(report["summary"], indent=2))


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", default="")
    ap.add_argument("--article-ids", default="")
    ap.add_argument("--category", default="")
    ap.add_argument("--max-articles", type=int, default=0)
    ap.add_argument("--delay", type=float, default=3.0)
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args()


if __name__ == "__main__":
    if not (WP_URL and WP_USER and WP_PASS):
        print("FATAL: WORDPRESS_URL / USERNAME / APP_PASSWORD required")
        sys.exit(1)
    asyncio.run(main_async(parse_args()))
