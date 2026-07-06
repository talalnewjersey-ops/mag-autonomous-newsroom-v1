"""Read-only diagnostic: scans every PUBLISHED WordPress post for leaked
pipeline-internal text (agent notes, gate/tier markers, version strings,
template placeholders) that was never meant to reach a reader.

Separate workstream from the article-generation pipeline (production_v2.yml
is untouched). Never writes to WordPress. Never deletes, redirects, or
merges anything -- this only lists candidates for the user to review one at
a time, per their explicit process.
"""
import base64
import json
import os
import re
import urllib.request


# Known/likely pipeline-internal strings that must never appear in reader-
# facing content. Each entry: (label, compiled regex). Broad enough to catch
# variants, narrow enough to avoid flagging legitimate reader-facing text
# (e.g. a genuine "tier" or "quick answer" heading is fine on its own --
# only the exact internal phrasings below are flagged).
RESIDUE_PATTERNS = [
    ("affiliate_placeholder_leak", re.compile(r"No affiliate opportunities detected[^.]*", re.IGNORECASE)),
    ("nexus_version_marker", re.compile(r"NEXUS-14\s*V?\d\.\d", re.IGNORECASE)),
    ("tier_marker", re.compile(r"\*\*Tier\*\*:\s*(?:OPPORTUNITY|STANDARD|PILLAR|GOLD)", re.IGNORECASE)),
    ("agent_log_tag", re.compile(r"\[AGENT-\d\d?\]")),
    ("gate_internal_name", re.compile(r"\b(?:COUCHE-[123]|G-Substance|G3 (?:PASS|FAIL|DUP)|GATE [ABC]\b)")),
    ("retry_internal_note", re.compile(r"retry attempt \d/\d|GATE .*(?:PASS|FAIL).*attempt")),
    ("categories_not_covered", re.compile(r"Categories not covered", re.IGNORECASE)),
    ("template_placeholder", re.compile(r"\{[a-zA-Z_]+\}|\[(?:TODO|FIXME|TBD|INSERT|PLACEHOLDER)[^\]]*\]", re.IGNORECASE)),
    ("literal_none_or_undefined", re.compile(r"\b(?:undefined|null)\b(?!\s*[-:])")),
    ("lorem_ipsum", re.compile(r"lorem ipsum", re.IGNORECASE)),
    ("tier_validation_note", re.compile(r"TIER \w+ VALIDATION", re.IGNORECASE)),
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
    # keep it simple/deterministic: collapse tags to spaces so a pattern
    # spanning a tag boundary still matches, without pulling in a full HTML
    # parser for a read-only scan.
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", text)


def scan_post(post):
    title = post.get("title", {}).get("rendered", "")
    content_html = post.get("content", {}).get("rendered", "")
    excerpt_html = post.get("excerpt", {}).get("rendered", "")
    content_text = _strip_html_light(content_html)
    excerpt_text = _strip_html_light(excerpt_html)

    findings = []
    for label, pattern in RESIDUE_PATTERNS:
        for field_name, text in (("content", content_text), ("excerpt", excerpt_text)):
            for m in pattern.finditer(text):
                lo, hi = max(0, m.start() - 60), min(len(text), m.end() + 60)
                findings.append({
                    "pattern": label,
                    "field": field_name,
                    "matched_text": m.group(0),
                    "context": text[lo:hi].strip(),
                })

    # Structural excerpt check (2026-07-06, user-reported case): an
    # auto-generated excerpt that starts with a heading-like fragment
    # immediately butted against the affiliate disclosure line (e.g.
    # "Quick Answer Affiliate disclosure: We earn a commission...") reads
    # as broken, not smooth prose -- flagged separately since it's a
    # STRUCTURE issue (WordPress's auto-excerpt truncation), not a leaked
    # literal string.
    excerpt_stripped = excerpt_text.strip()
    if "Affiliate disclosure:" in excerpt_stripped[:80] and not excerpt_stripped.startswith("Affiliate disclosure"):
        findings.append({
            "pattern": "excerpt_structure_glued",
            "field": "excerpt",
            "matched_text": excerpt_stripped[:80],
            "context": excerpt_stripped[:160],
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
    print(f"Scanned {len(posts)} published posts.")

    results = []
    for post in posts:
        r = scan_post(post)
        if r:
            results.append(r)

    print(f"\n===== {len(results)} POST(S) WITH RESIDUE FOUND =====\n")
    for r in results:
        print(f"id={r['id']} | slug={r['slug']} | {r['link']}")
        for f in r["findings"]:
            print(f"    [{f['pattern']}] ({f['field']}) matched: {f['matched_text']!r}")
            print(f"        context: ...{f['context']}...")
        print()

    with open("residue_scan_results.json", "w", encoding="utf-8") as f:
        json.dump({"total_posts_scanned": len(posts), "posts_with_findings": results}, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
