#!/usr/bin/env python3
"""
NEXUS-14: Draft Quality Report
Audits every WordPress draft against the NEXUS-14 QUALITY_RULES
(see README.md / config/config.yaml / agents/agent_13_chief_editor.py):

  - min_word_count   : 5000
  - min_images       : 4 (featured + inline)
  - featured_image   : required
  - faq_required     : required (>= 8 Q&A recommended)
  - author_required  : required
  - author_bio       : required
  - min_seo_score    : 95   (heuristic, same formula as produce_article.py)
  - min_eeat_score   : 95   (heuristic, same formula as produce_article.py)
  - internal_links   : >= 5 (used by produce_article.py quality gate)
  - no_broken_links  : best-effort HEAD check on external links

Verdict mirrors agent_13_chief_editor.py:
  READY_TO_PUBLISH : every rule passes
  REJECTED         : any critical failure (no featured image, no FAQ,
                     no author, SEO < 50, EEAT < 50, word_count < 3000)
  NEEDS_CORRECTION : anything else
"""
import os
import re
import json
import requests
from base64 import b64encode

WP_URL = os.environ.get("WORDPRESS_URL", "https://moneyabroadguide.com").rstrip("/")
WP_USER = os.environ.get("WORDPRESS_USERNAME", "")
WP_PASS = os.environ.get("WORDPRESS_PASSWORD", "")
CHECK_LINKS = os.environ.get("CHECK_LINKS", "true").lower() != "false"
MAX_LINK_CHECKS = int(os.environ.get("MAX_LINK_CHECKS", "30"))

creds = b64encode((WP_USER + ":" + WP_PASS).encode()).decode()
HDR = {"Authorization": "Basic " + creds, "Accept": "application/json"}

# Thresholds from config/config.yaml -> quality_rules
RULES = {
    "min_word_count": 5000,
    "min_images": 4,
    "min_seo_score": 95,
    "min_eeat_score": 95,
    "min_internal_links": 5,
    "min_faq_questions": 8,
}


def strip_tags(html):
    return re.sub(r"<[^>]+>", " ", html or "")


def fetch_all_drafts():
    posts, page = [], 1
    while True:
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts",
            headers=HDR,
            params={
                "status": "draft",
                "per_page": 50,
                "page": page,
                "orderby": "id",
                "order": "asc",
                "_fields": "id,title,link,date,author,featured_media,content",
            },
            timeout=30,
        )
        if r.status_code != 200:
            print(f"  WP error {r.status_code}: {r.text[:150]}")
            break
        data = r.json()
        if not data:
            break
        posts.extend(data)
        if len(data) < 50:
            break
        page += 1
    return posts


_author_cache = {}


def fetch_author(author_id):
    if author_id in _author_cache:
        return _author_cache[author_id]
    name, bio = "", ""
    try:
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/users/{author_id}",
            headers=HDR,
            params={"context": "edit"},
            timeout=20,
        )
        if r.status_code == 200:
            d = r.json()
            name = d.get("name", "")
            bio = d.get("description", "")
    except Exception as e:
        print(f"  Author lookup error ({author_id}): {e}")
    _author_cache[author_id] = (name, bio)
    return name, bio


def seo_score_for(title, content):
    score = 0
    words_in_topic = [w for w in title.lower().split() if len(w) > 3]
    found_kw = sum(1 for w in words_in_topic if w in content.lower())
    kw_density = found_kw / max(len(words_in_topic), 1)
    if kw_density >= 0.7:
        score += 25
    if content.count("<h2>") >= 5:
        score += 20
    if "<table" in content:
        score += 15
    if len(strip_tags(content).split()) >= 5000:
        score += 20
    if "href=" in content:
        score += 15
    if "faq" in content.lower() or "frequently asked" in content.lower():
        score += 5
    return score


def eeat_score_for(content):
    score = 0
    cl = content.lower()
    if any(w in cl for w in ["expert", "research", "study", "data", "statistic", "analysis"]):
        score += 20
    if any(w in cl for w in ["review", "comparison", "tested", "versus", "vs"]):
        score += 20
    if any(w in cl for w in ["fee", "cost", "price", "rate", "percent", "%"]):
        score += 20
    if len(strip_tags(content).split()) >= 5000:
        score += 20
    if "faq" in cl or "frequently asked" in cl:
        score += 10
    if "ebook" in cl or "free guide" in cl or "download" in cl:
        score += 10
    return score


def check_links(content, link_cache):
    hrefs = re.findall(r'href="(https?://[^"]+)"', content)
    external = [h for h in hrefs if "moneyabroadguide.com" not in h]
    broken = []
    for url in external:
        if url not in link_cache:
            if not CHECK_LINKS or len(link_cache) >= MAX_LINK_CHECKS:
                link_cache[url] = None  # unverified
                continue
            try:
                r = requests.head(url, timeout=8, allow_redirects=True,
                                   headers={"User-Agent": "Mozilla/5.0 (NEXUS14-QA)"})
                link_cache[url] = r.status_code
            except Exception:
                link_cache[url] = -1  # unreachable / unverified
        status = link_cache[url]
        if status is not None and (status >= 400 or status == -1):
            broken.append((url, status))
    return broken


def main():
    print("=" * 70)
    print("RAPPORT QUALITE - ARTICLES EN DRAFT (NEXUS-14)")
    print("=" * 70)

    posts = fetch_all_drafts()
    print(f"Total drafts: {len(posts)}")
    print()

    link_cache = {}
    rows = []

    for post in posts:
        pid = post["id"]
        title = strip_tags(post["title"]["rendered"]).strip()
        content = post.get("content", {}).get("rendered", "")
        plain = strip_tags(content)
        word_count = len(plain.split())

        featured = bool(post.get("featured_media"))
        inline_imgs = len(re.findall(r"<img ", content, re.IGNORECASE))
        total_images = (1 if featured else 0) + inline_imgs

        cl = content.lower()
        has_faq = "faq" in cl or "frequently asked" in cl
        faq_questions = cl.count("?")

        hrefs = re.findall(r'href="(https?://[^"]+)"', content)
        internal_links = sum(1 for h in hrefs if "moneyabroadguide.com" in h)

        seo = seo_score_for(title, content)
        eeat = eeat_score_for(content)

        author_id = post.get("author")
        author_name, author_bio = fetch_author(author_id)

        broken = check_links(content, link_cache) if CHECK_LINKS else []

        checks = {
            "word_count_5000+":     word_count >= RULES["min_word_count"],
            "images_4+":            total_images >= RULES["min_images"],
            "featured_image":       featured,
            "faq_section":          has_faq,
            "faq_8+_questions":     faq_questions >= RULES["min_faq_questions"],
            "author_set":           bool(author_name),
            "author_bio":           bool(author_bio.strip()),
            "seo_score_95+":        seo >= RULES["min_seo_score"],
            "eeat_score_95+":       eeat >= RULES["min_eeat_score"],
            "internal_links_5+":    internal_links >= RULES["min_internal_links"],
            "no_broken_links":      len(broken) == 0,
        }

        # Mirror agent_13_chief_editor.py decision logic
        critical_fail = (
            not featured
            or not has_faq
            or not author_name
            or seo < 50
            or eeat < 50
            or word_count < 3000
        )
        if all(checks.values()):
            verdict = "READY_TO_PUBLISH"
        elif critical_fail:
            verdict = "REJECTED"
        else:
            verdict = "NEEDS_CORRECTION"

        rows.append({
            "id": pid,
            "title": title,
            "link": post.get("link", ""),
            "word_count": word_count,
            "total_images": total_images,
            "featured": featured,
            "inline_imgs": inline_imgs,
            "has_faq": has_faq,
            "faq_questions": faq_questions,
            "internal_links": internal_links,
            "seo": seo,
            "eeat": eeat,
            "author_name": author_name,
            "author_bio": bool(author_bio.strip()),
            "broken_links": broken,
            "checks": checks,
            "verdict": verdict,
        })

    # ---- Per-article report ----
    print("DETAIL PAR ARTICLE")
    print("-" * 70)
    for r in rows:
        fails = [k for k, v in r["checks"].items() if not v]
        print(f"[{r['id']}] {r['title'][:60]}")
        print(f"   verdict        : {r['verdict']}")
        print(f"   words          : {r['word_count']} (min {RULES['min_word_count']})")
        print(f"   images         : {r['total_images']} "
              f"(featured={'OUI' if r['featured'] else 'NON'}, inline={r['inline_imgs']}, min {RULES['min_images']})")
        print(f"   faq            : {'OUI' if r['has_faq'] else 'NON'} "
              f"({r['faq_questions']} '?' detectes, recommande >= {RULES['min_faq_questions']})")
        print(f"   internal links : {r['internal_links']} (min {RULES['min_internal_links']})")
        print(f"   SEO score      : {r['seo']} (min {RULES['min_seo_score']})")
        print(f"   EEAT score     : {r['eeat']} (min {RULES['min_eeat_score']})")
        print(f"   author         : {r['author_name'] or 'AUCUN'} "
              f"(bio={'OUI' if r['author_bio'] else 'NON'})")
        if r["broken_links"]:
            print(f"   broken links   : {len(r['broken_links'])} -> "
                  + ", ".join(f"{u} ({s})" for u, s in r["broken_links"][:5]))
        if fails:
            print(f"   ECHECS         : {', '.join(fails)}")
        print()

    # ---- Summary ----
    total = len(rows)
    print("=" * 70)
    print("RESUME FINAL")
    print("=" * 70)
    print(f"Total drafts analyses : {total}")
    for verdict in ("READY_TO_PUBLISH", "NEEDS_CORRECTION", "REJECTED"):
        n = sum(1 for r in rows if r["verdict"] == verdict)
        print(f"  {verdict:18}: {n}/{total}")
    print()

    if total:
        print("Conformite par regle:")
        for key in ["word_count_5000+", "images_4+", "featured_image", "faq_section",
                     "faq_8+_questions", "author_set", "author_bio",
                     "seo_score_95+", "eeat_score_95+", "internal_links_5+", "no_broken_links"]:
            n_ok = sum(1 for r in rows if r["checks"][key])
            print(f"  {key:20}: {n_ok}/{total} OK")

        avg_words = sum(r["word_count"] for r in rows) / total
        avg_seo = sum(r["seo"] for r in rows) / total
        avg_eeat = sum(r["eeat"] for r in rows) / total
        print()
        print(f"Moyenne mots   : {avg_words:.0f}")
        print(f"Moyenne SEO    : {avg_seo:.1f}")
        print(f"Moyenne EEAT   : {avg_eeat:.1f}")

    print("=" * 70)

    with open("draft_quality_report.json", "w") as f:
        json.dump({"rules": RULES, "drafts": rows}, f, indent=2, default=str)
    print("Report: draft_quality_report.json")


if __name__ == "__main__":
    main()
