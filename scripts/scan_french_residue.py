"""Read-only diagnostic: NOT a real language detector -- a targeted scan for
the most obvious French-language leftovers on this English-language site
(accented characters, the specific emoji marker the user first spotted, and
common French words/phrases). Catches visible cases only; makes no claim of
completeness the way real language detection would.

Part of the published-content audit workstream. Never writes to WordPress.
"""
import base64
import json
import os
import re
import urllib.request


FRENCH_PATTERNS = [
    ("emoji_prochaine_etape", re.compile(r"👉\s*Prochaine\s*[ée]tape", re.IGNORECASE)),
    ("emoji_arrow_marker", re.compile(r"👉")),
    ("french_word_etape", re.compile(r"\b[ÉéEe]tape\b")),
    ("french_phrase_prochaine_etape", re.compile(r"[Pp]rochaine\s*[ée]tape")),
    ("french_word_guide_complet", re.compile(r"[Gg]uide\s+complet")),
    ("french_word_decouvrez", re.compile(r"[Dd][ée]couvrez")),
    ("french_word_cliquez", re.compile(r"[Cc]liquez")),
    ("french_word_conseils", re.compile(r"\b[Cc]onseils\b")),
    ("french_accented_chars", re.compile(r"[éèêëàâçîïôùû]", re.IGNORECASE)),
]


def _auth_header(user, app_password):
    creds = f"{user}:{app_password}"
    return "Basic " + base64.b64encode(creds.encode()).decode()


def fetch_all_published(wp_url, user, app_password, per_page=50):
    auth = _auth_header(user, app_password)
    posts = []
    page = 1
    while True:
        url = (f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts?status=publish&per_page={per_page}"
               f"&page={page}&_fields=id,title,slug,link,content,excerpt")
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


def _strip_html_light(html):
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", text)


def scan_post(post):
    title = post.get("title", {}).get("rendered", "")
    content_text = _strip_html_light(post.get("content", {}).get("rendered", ""))
    excerpt_text = _strip_html_light(post.get("excerpt", {}).get("rendered", ""))

    findings = []
    for label, pattern in FRENCH_PATTERNS:
        for field_name, text in (("title", title), ("content", content_text), ("excerpt", excerpt_text)):
            for m in pattern.finditer(text):
                lo, hi = max(0, m.start() - 60), min(len(text), m.end() + 60)
                findings.append({
                    "pattern": label,
                    "field": field_name,
                    "matched_text": m.group(0),
                    "context": text[lo:hi].strip(),
                })

    if findings:
        return {
            "id": post.get("id"),
            "slug": post.get("slug"),
            "title": title,
            "link": post.get("link"),
            "findings": findings,
        }
    return None


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]

    posts = fetch_all_published(wp_url, user, app_pw)
    print(f"Scanned {len(posts)} published posts for French-language leftovers.")

    results = []
    for post in posts:
        r = scan_post(post)
        if r:
            results.append(r)

    print(f"\n===== {len(results)} POST(S) WITH POSSIBLE FRENCH RESIDUE =====\n")
    for r in results:
        print(f"id={r['id']} | slug={r['slug']} | {r['link']}")
        for f in r["findings"]:
            print(f"    [{f['pattern']}] ({f['field']}) matched: {f['matched_text']!r}")
            print(f"        context: ...{f['context']}...")
        print()

    with open("french_residue_scan_results.json", "w", encoding="utf-8") as f:
        json.dump({"total_posts_scanned": len(posts), "posts_with_findings": results}, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
