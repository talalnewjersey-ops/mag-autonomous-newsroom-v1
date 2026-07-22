#!/usr/bin/env python3
"""
Phase 12 - Controles techniques finaux.
LECTURE SEULE : que des GET/HEAD. Verifie l'etat public reel du site
(pas seulement ce que l'API REST renvoie), pour attraper les problemes
que Phase 0-6 ne peuvent pas voir (cache, Elementor, rendu final).

Peut tourner independamment d'une correction : c'est un controle de sante
technique du site, utile a n'importe quel moment.
"""

import os
import re
import json
import socket
import datetime
import requests
from requests.auth import HTTPBasicAuth

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
SESSION.headers.update({"User-Agent": "adsense-technical-check-bot/1.0"})

TODAY = datetime.date.today().isoformat()
REPORT_DIR = "audit"
REPORT_PATH = f"{REPORT_DIR}/technical-checks-{TODAY}.md"

MARKDOWN_RESIDUE_PATTERNS = [
    r"^#{1,6}\s", r"\*\*[^*]+\*\*", r"^\s*-\s+\[", r"```", r"^---\s*$",
]
INTERNAL_LEAK_MARKERS = [
    "notes internes", "internal notes", "todo", "fixme",
    "as an ai", "nexus-14", "prompt:",
]

results = {
    "sitemap": {},
    "pages": [],
    "summary": {},
    "errors": [],
}


def all_published_posts(per_page=50, max_pages=20):
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
            results["errors"].append(f"all_published_posts page {page}: {e}")
            break
    return posts


def check_sitemap():
    for candidate in ["/sitemap_index.xml", "/wp-sitemap.xml", "/sitemap.xml"]:
        try:
            r = SESSION.get(f"{WP_URL}{candidate}", timeout=20)
            if r.status_code == 200 and "<" in r.text[:50]:
                url_count = len(re.findall(r"<loc>", r.text))
                results["sitemap"] = {
                    "found_at": candidate,
                    "http_status": r.status_code,
                    "entries_found_in_index": url_count,
                }
                return
        except Exception as e:
            results["errors"].append(f"check_sitemap {candidate}: {e}")
    results["sitemap"] = {"found_at": None, "note": "Aucun sitemap standard detecte automatiquement."}


def check_page(url, post_id, slug):
    entry = {"post_id": post_id, "slug": slug, "url": url}
    try:
        r = None
        last_error = None
        for attempt in range(1, 3):
            try:
                r = SESSION.get(url, allow_redirects=True, timeout=45)
                break
            except Exception as e:
                last_error = e
                if attempt == 2:
                    raise last_error
        entry["final_status"] = r.status_code
        entry["redirect_count"] = len(r.history)
        entry["redirect_chain"] = [h.status_code for h in r.history]

        if len(r.history) > 1:
            entry["issue_redirect_chain"] = True

        html = r.text

        # Canonical
        canon_match = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', html, re.IGNORECASE)
        entry["canonical"] = canon_match.group(1) if canon_match else None
        if entry["canonical"]:
            canon_domain = re.sub(r"^https?://", "", entry["canonical"]).split("/")[0]
            site_domain = re.sub(r"^https?://", "", WP_URL).split("/")[0]
            if canon_domain != site_domain:
                # Canonical pointe vers un AUTRE site : vrai probleme potentiel
                entry["issue_canonical_external"] = True
            elif entry["canonical"].rstrip("/") != url.rstrip("/"):
                # Canonical pointe vers une autre page DU MEME site : consolidation
                # SEO normale et souvent volontaire. Info seulement, pas une "issue_".
                entry["canonical_points_elsewhere_same_site"] = entry["canonical"]

        # Robots meta
        robots_match = re.search(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        entry["robots_meta"] = robots_match.group(1) if robots_match else None
        if entry["robots_meta"] and "noindex" in entry["robots_meta"].lower():
            entry["issue_unexpected_noindex"] = True

        # H1 count (page complete, pas juste post_content)
        h1_count = len(re.findall(r"<h1[\s>]", html, re.IGNORECASE))
        entry["h1_count"] = h1_count
        if h1_count == 0 or h1_count > 1:
            entry["issue_h1_count"] = h1_count

        # Residus markdown / contenu interne visibles publiquement
        text_lower = html.lower()
        leaks = [m for m in INTERNAL_LEAK_MARKERS if m in text_lower]
        if leaks:
            entry["issue_internal_leak"] = leaks

        md_hits = [p for p in MARKDOWN_RESIDUE_PATTERNS if re.search(p, html, re.MULTILINE)]
        if md_hits:
            entry["issue_markdown_residue"] = True

    except Exception as e:
        entry["error"] = str(e)
        results["errors"].append(f"check_page {url}: {e}")

    return entry


def main():
    check_sitemap()

    posts = all_published_posts()
    for p in posts:
        entry = check_page(p["link"], p["id"], p["slug"])
        results["pages"].append(entry)

    issues = [p for p in results["pages"] if any(k.startswith("issue_") for k in p)]
    broken = [p for p in results["pages"] if p.get("final_status") not in (200,) and "error" not in p]
    errored = [p for p in results["pages"] if "error" in p]

    results["summary"] = {
        "total_pages_checked": len(results["pages"]),
        "pages_with_issues": len(issues),
        "pages_broken_http": len(broken),
        "pages_fetch_errors": len(errored),
    }

    lines = []
    lines.append(f"# Rapport de controles techniques — {TODAY}")
    lines.append("")
    lines.append("> Controles en LECTURE SEULE sur l'etat public reel du site "
                  "(rendu final, apres cache/Elementor). Complementaire au rapport d'audit AdSense.")
    lines.append("")
    lines.append(f"## Resume — {results['summary']['total_pages_checked']} pages verifiees | "
                  f"{results['summary']['pages_with_issues']} avec probleme(s) | "
                  f"{results['summary']['pages_broken_http']} en erreur HTTP | "
                  f"{results['summary']['pages_fetch_errors']} injoignables")
    lines.append("")

    lines.append("## Sitemap")
    lines.append("```json")
    lines.append(json.dumps(results["sitemap"], indent=2, ensure_ascii=False))
    lines.append("```")
    lines.append("")

    if broken:
        lines.append("## Pages en erreur HTTP (ni 200)")
        for p in broken:
            lines.append(f"- {p['slug']} → statut {p.get('final_status')} — {p['url']}")
        lines.append("")

    consolidations = [p for p in results["pages"] if p.get("canonical_points_elsewhere_same_site")]
    if consolidations:
        lines.append("## Info (pas un probleme) — Consolidation SEO detectee")
        lines.append("Ces pages ont un canonical pointant vers une autre page du meme site "
                      "(pratique normale pour eviter le duplicate content) :")
        for p in consolidations:
            lines.append(f"- {p['slug']} → {p['canonical_points_elsewhere_same_site']}")
        lines.append("")

    if issues:
        lines.append("## Pages avec probleme(s) technique(s)")
        for p in issues:
            flags = [k.replace("issue_", "") for k in p if k.startswith("issue_")]
            lines.append(f"- **{p['slug']}** : {', '.join(flags)}")
            if p.get("redirect_count", 0) > 1:
                lines.append(f"  - Chaine de redirection : {p['redirect_chain']}")
            if p.get("canonical"):
                lines.append(f"  - Canonical trouve : {p['canonical']}")
            if p.get("h1_count") is not None and (p["h1_count"] == 0 or p["h1_count"] > 1):
                lines.append(f"  - Nombre de H1 sur la page rendue : {p['h1_count']}")
        lines.append("")
    else:
        lines.append("## Pages avec probleme(s) technique(s)")
        lines.append("Aucune.")
        lines.append("")

    if errored:
        lines.append("## Erreurs de recuperation")
        for p in errored:
            lines.append(f"- {p['slug']} : {p['error']}")
        lines.append("")

    if results["errors"]:
        lines.append("## Erreurs systeme rencontrees pendant le scan")
        lines.extend([f"- {e}" for e in results["errors"]])
        lines.append("")

    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Rapport genere : {REPORT_PATH}")
    print(json.dumps(results["summary"], indent=2))


if __name__ == "__main__":
    main()
