#!/usr/bin/env python3
"""
Audit AdSense en LECTURE SEULE pour MoneyAbroadGuide.com
Equivalent des Phases 0-6 du Bloc 1, adapte a l'API REST WordPress
(reutilise WORDPRESS_URL / WORDPRESS_USERNAME / WORDPRESS_APP_PASSWORD,
deja utilises par les agents NEXUS-14).

REGLE ABSOLUE : ce script ne fait AUCUN appel POST/PUT/DELETE vers WordPress.
Uniquement des GET. Il n'ecrit que dans audit/ (rapport local, commite par le workflow).
"""

import os
import re
import json
import datetime
import requests
from requests.auth import HTTPBasicAuth
import socket
_orig_getaddrinfo = socket.getaddrinfo
def _force_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _force_ipv4
WP_URL = os.environ["WORDPRESS_URL"].rstrip("/")
WP_USER = os.environ["WORDPRESS_USERNAME"]
WP_APP_PASSWORD = os.environ["WORDPRESS_APP_PASSWORD"]
AUTH = HTTPBasicAuth(WP_USER, WP_APP_PASSWORD)

SESSION = requests.Session()
SESSION.auth = AUTH
SESSION.headers.update({"User-Agent": "adsense-audit-bot/1.0"})

TODAY = datetime.date.today().isoformat()
REPORT_DIR = "audit"
REPORT_PATH = f"{REPORT_DIR}/adsense-audit-{TODAY}.md"

SUSPICIOUS_PHRASES = [
    "340 newcomers", "according to our survey", "our survey", "our data shows",
    "our research shows", "we surveyed", "based on our data",
    "hundreds of newcomers", "our readers reported",
]

INTERNAL_NOTES_MARKERS = [
    "notes internes", "internal notes", "todo", "fixme", "lorem ipsum",
    "as an ai", "claude", "chatgpt", "nexus-14", "prompt:",
]

USA_ARTICLE_SLUG = "best-banks-newcomers-usa-2026"
DEAD_LINK_SLUG = "best-us-banks-for-foreigners-2026-guide"
CANADA_CANDIDATES = [
    "best-banks-newcomers-canada-2026",
    "best-banks-newcomers-canada",
    "best-newcomer-bank-accounts-in-canada-complete-guide-for-canada-immigrants-2026",
    "rbc-vs-scotiabank-vs-td-newcomers-canada-2026",
]
NEXUS14_PRIORITY_SLUGS = [
    "taxes-for-new-immigrants-to-the-usa-2026",
    "how-to-build-credit-in-usa-without-ssn",
    "open-bank-account-newcomer-usa-2026",
    "us-expat-tax-filing-guide-2026",
]

findings = {
    "phase0": {},
    "phase1": {},
    "phase2": {},
    "phase3": [],
    "phase4": [],
    "phase5": {},
    "errors": [],
}


def get(path, params=None):
    url = f"{WP_URL}{path}"
    r = SESSION.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def strip_html(html):
    return re.sub(r"<[^>]+>", " ", html or "")


def word_count(html):
    return len(strip_html(html).split())


def find_post_by_slug(slug, post_type="posts"):
    try:
        results = get(f"/wp-json/wp/v2/{post_type}", {"slug": slug})
        return results[0] if results else None
    except Exception as e:
        findings["errors"].append(f"find_post_by_slug({slug}): {e}")
        return None


def all_posts(per_page=50, max_pages=20):
    posts = []
    for page in range(1, max_pages + 1):
        try:
            r = SESSION.get(
                f"{WP_URL}/wp-json/wp/v2/posts",
                params={"per_page": per_page, "page": page, "status": "publish"},
                timeout=30,
            )
            if r.status_code == 400:
                break
            r.raise_for_status()
            batch = r.json()
            if not batch:
                break
            posts.extend(batch)
        except Exception as e:
            findings["errors"].append(f"all_posts page {page}: {e}")
            break
    return posts


def detect_suspicious(text):
    text_lower = text.lower()
    return [p for p in SUSPICIOUS_PHRASES if p.lower() in text_lower]


def detect_internal_leak(text):
    text_lower = text.lower()
    return [m for m in INTERNAL_NOTES_MARKERS if m in text_lower]


def count_tables(html):
    return len(re.findall(r"<table", html or "", re.IGNORECASE))


def count_headings(html, level):
    return len(re.findall(fr"<h{level}[\s>]", html or "", re.IGNORECASE))


def extract_links(html):
    return re.findall(r'href="([^"]+)"', html or "")


def phase0():
    try:
        info = get("/wp-json/")
        findings["phase0"] = {
            "site_name": info.get("name"),
            "site_url": info.get("url") or info.get("home"),
            "description": info.get("description"),
            "note": "Liste des plugins actifs non accessible via REST API standard. "
                    "A verifier manuellement (wp-admin > Plugins) si necessaire.",
        }
    except Exception as e:
        findings["errors"].append(f"phase0: {e}")


def phase1():
    post = find_post_by_slug(USA_ARTICLE_SLUG)
    if not post:
        findings["phase1"] = {"status": "INTROUVABLE", "slug": USA_ARTICLE_SLUG}
        return

    content = post["content"]["rendered"]
    text = strip_html(content)

    findings["phase1"] = {
        "post_id": post["id"],
        "status": post["status"],
        "modified": post["modified"],
        "word_count": word_count(content),
        "h1_count": count_headings(content, 1),
        "h2_count": count_headings(content, 2),
        "h3_count": count_headings(content, 3),
        "table_count": count_tables(content),
        "link_count": len(extract_links(content)),
        "suspicious_phrases_found": detect_suspicious(text),
        "internal_leak_markers": detect_internal_leak(text),
    }


def phase2():
    dead_url = f"{WP_URL}/{DEAD_LINK_SLUG}/"
    http_status = None
    try:
        r = SESSION.head(dead_url, allow_redirects=True, timeout=15)
        http_status = r.status_code
    except Exception as e:
        findings["errors"].append(f"phase2 curl: {e}")

    referencing_posts = []
    try:
        results = get("/wp-json/wp/v2/posts", {"search": DEAD_LINK_SLUG, "per_page": 50})
        for p in results:
            if DEAD_LINK_SLUG in p["content"]["rendered"]:
                referencing_posts.append({"id": p["id"], "slug": p["slug"], "title": p["title"]["rendered"]})
    except Exception as e:
        findings["errors"].append(f"phase2 search: {e}")

    findings["phase2"] = {
        "dead_url": dead_url,
        "http_status": http_status,
        "still_broken": http_status not in (200,) if http_status else "inconnu",
        "referencing_posts": referencing_posts,
    }


def phase3():
    pages_data = []
    for slug in CANADA_CANDIDATES:
        post = find_post_by_slug(slug)
        if not post:
            pages_data.append({"slug": slug, "status": "INTROUVABLE"})
            continue
        content = post["content"]["rendered"]
        pages_data.append({
            "slug": slug,
            "post_id": post["id"],
            "status": post["status"],
            "title": post["title"]["rendered"],
            "word_count": word_count(content),
            "h2_count": count_headings(content, 2),
            "table_count": count_tables(content),
        })

    texts = {}
    for slug in CANADA_CANDIDATES:
        post = find_post_by_slug(slug)
        if post:
            texts[slug] = set(strip_html(post["content"]["rendered"]).lower().split())

    similarities = []
    slugs = list(texts.keys())
    for i in range(len(slugs)):
        for j in range(i + 1, len(slugs)):
            a, b = texts[slugs[i]], texts[slugs[j]]
            if not a or not b:
                continue
            overlap = len(a & b) / max(1, len(a | b))
            similarities.append({"pair": [slugs[i], slugs[j]], "jaccard_similarity": round(overlap, 3)})

    findings["phase3"] = {"pages": pages_data, "similarities": similarities}


def phase4():
    results = []
    for slug in NEXUS14_PRIORITY_SLUGS:
        post = find_post_by_slug(slug)
        if not post:
            results.append({"slug": slug, "status": "INTROUVABLE", "severity": "P1"})
            continue
        content = post["content"]["rendered"]
        text = strip_html(content)
        suspicious = detect_suspicious(text)
        leaks = detect_internal_leak(text)
        h1s = count_headings(content, 1)
        severity = "P2"
        if suspicious or leaks:
            severity = "P0"
        elif h1s > 1 or word_count(content) < 800:
            severity = "P1"

        results.append({
            "slug": slug,
            "post_id": post["id"],
            "word_count": word_count(content),
            "h1_count": h1s,
            "suspicious_phrases_found": suspicious,
            "internal_leak_markers": leaks,
            "severity": severity,
        })
    findings["phase4"] = results


def phase5():
    posts = all_posts()
    weak_pages = []
    leak_pages = []
    suspicious_pages = []

    for p in posts:
        content = p["content"]["rendered"]
        text = strip_html(content)
        wc = word_count(content)
        h2s = count_headings(content, 2)

        if wc < 800 or h2s == 0:
            weak_pages.append({"slug": p["slug"], "post_id": p["id"], "word_count": wc, "h2_count": h2s})

        leaks = detect_internal_leak(text)
        if leaks:
            leak_pages.append({"slug": p["slug"], "post_id": p["id"], "markers": leaks})

        suspicious = detect_suspicious(text)
        if suspicious:
            suspicious_pages.append({"slug": p["slug"], "post_id": p["id"], "phrases": suspicious})

    findings["phase5"] = {
        "total_posts_scanned": len(posts),
        "weak_pages": weak_pages,
        "internal_leak_pages": leak_pages,
        "suspicious_claim_pages": suspicious_pages,
    }


def phase6():
    p0 = []
    p1 = []
    p2 = []

    if findings["phase1"].get("suspicious_phrases_found") or findings["phase1"].get("internal_leak_markers"):
        p0.append(f"{USA_ARTICLE_SLUG} (article USA corrompu — Phase 1)")

    if findings["phase2"].get("still_broken"):
        p1.append(f"Lien mort actif : {DEAD_LINK_SLUG}")

    for item in findings["phase4"]:
        if item.get("severity") == "P0":
            p0.append(f"{item['slug']} (NEXUS-14 — contenu suspect)")
        elif item.get("severity") == "P1":
            p1.append(f"{item['slug']} (NEXUS-14 — a verifier)")

    for item in findings["phase5"].get("internal_leak_pages", []):
        p0.append(f"{item['slug']} (contenu interne visible publiquement)")

    for item in findings["phase5"].get("suspicious_claim_pages", []):
        p0.append(f"{item['slug']} (statistiques/sondage non verifiable)")

    for item in findings["phase5"].get("weak_pages", []):
        p2.append(f"{item['slug']} (contenu faible : {item['word_count']} mots)")

    if p0:
        readiness = "PAS PRET"
    elif p1:
        readiness = "PRESQUE PRET"
    else:
        readiness = "PRET (a confirmer manuellement)"

    lines = []
    lines.append(f"# Rapport d'audit AdSense — {TODAY}")
    lines.append("")
    lines.append(f"**Evaluation automatique : {readiness}**")
    lines.append("")
    lines.append("> Rapport genere automatiquement en LECTURE SEULE via l'API REST WordPress. "
                  "Aucune modification n'a ete effectuee sur le site. "
                  "Validation humaine requise avant toute correction (Bloc 2 / Bloc 3).")
    lines.append("")
    lines.append(f"## Resume — P0: {len(p0)} | P1: {len(p1)} | P2: {len(p2)}")
    lines.append("")

    lines.append("### P0 — Urgent")
    lines.extend([f"- {x}" for x in p0] or ["- Aucun"])
    lines.append("")
    lines.append("### P1 — A traiter")
    lines.extend([f"- {x}" for x in p1] or ["- Aucun"])
    lines.append("")
    lines.append("### P2 — A surveiller")
    lines.extend([f"- {x}" for x in p2] or ["- Aucun"])
    lines.append("")

    lines.append("## Detail Phase 0 — Site")
    lines.append("```json")
    lines.append(json.dumps(findings["phase0"], indent=2, ensure_ascii=False))
    lines.append("```")
    lines.append("")

    lines.append(f"## Detail Phase 1 — Article USA ({USA_ARTICLE_SLUG})")
    lines.append("```json")
    lines.append(json.dumps(findings["phase1"], indent=2, ensure_ascii=False))
    lines.append("```")
    lines.append("")

    lines.append(f"## Detail Phase 2 — Lien mort ({DEAD_LINK_SLUG})")
    lines.append("```json")
    lines.append(json.dumps(findings["phase2"], indent=2, ensure_ascii=False))
    lines.append("```")
    lines.append("")

    lines.append("## Detail Phase 3 — Pages Canada")
    lines.append("```json")
    lines.append(json.dumps(findings["phase3"], indent=2, ensure_ascii=False))
    lines.append("```")
    lines.append("")

    lines.append("## Detail Phase 4 — Pages prioritaires NEXUS-14")
    lines.append("```json")
    lines.append(json.dumps(findings["phase4"], indent=2, ensure_ascii=False))
    lines.append("```")
    lines.append("")

    lines.append(f"## Detail Phase 5 — Audit global ({findings['phase5'].get('total_posts_scanned', 0)} posts scannes)")
    lines.append("```json")
    lines.append(json.dumps(findings["phase5"], indent=2, ensure_ascii=False))
    lines.append("```")
    lines.append("")

    if findings["errors"]:
        lines.append("## Erreurs rencontrees pendant l'audit")
        lines.extend([f"- {e}" for e in findings["errors"]])
        lines.append("")

    lines.append("---")
    lines.append("*Prochaine etape : lire ce rapport, puis lancer le Bloc 2 (sauvegardes + corrections) "
                  "en session Claude Code supervisee — ce workflow ne corrige rien automatiquement.*")

    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Rapport genere : {REPORT_PATH}")
    print(f"Evaluation : {readiness} | P0={len(p0)} P1={len(p1)} P2={len(p2)}")


if __name__ == "__main__":
    phase0()
    phase1()
    phase2()
    phase3()
    phase4()
    phase5()
    phase6()
