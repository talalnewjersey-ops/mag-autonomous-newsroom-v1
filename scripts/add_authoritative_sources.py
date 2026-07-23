#!/usr/bin/env python3
"""
Ajoute une section "Official Resources" en fin d'article, pour les articles
sans aucune source autoritaire (.gov) detectee par low_value_content_audit.py.

SECURITE : ce script n'AJOUTE JAMAIS de contenu que par append en fin de post.
Il ne supprime et ne remplace RIEN d'existant. Il verifie d'abord qu'une
section "Official Resources" n'existe pas deja (evite les doublons si relance).

Modes :
  --dry-run   : affiche ce qui serait ajoute, ne touche pas a WordPress (defaut)
  --apply     : applique reellement les modifications (POST vers WordPress)

Usage :
  python scripts/add_authoritative_sources.py --dry-run
  python scripts/add_authoritative_sources.py --apply
"""

import os
import sys
import socket
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
SESSION.headers.update({"User-Agent": "adsense-source-enrichment-bot/1.0"})

# Session separee pour verifier les liens EXTERNES (.gov, canada.ca...).
# Ces sites bloquent souvent les User-Agent "bot" avec de faux 404/403 —
# on utilise donc un User-Agent de navigateur standard, sans l'auth WordPress.
EXTERNAL_CHECK_SESSION = requests.Session()
EXTERNAL_CHECK_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
})

MARKER = "<!-- official-resources-block -->"

INTRO_VARIANTS = [
    "For authoritative information on this topic, consult these official government sources:",
    "The following official government resources provide additional verified information on this subject:",
    "To confirm the details above, you can consult these official sources directly:",
    "These government resources offer additional context and the most current official guidance:",
]

SOURCES_MAP = {
    "best-money-transfer-apps-immigrants": [
        ("Consumer Financial Protection Bureau — International Money Transfers", "https://www.consumerfinance.gov/consumer-tools/international-money-transfers/"),
    ],
    "student-bank-account-canada-newcomers-2026": [
        ("Government of Canada — Banking for Newcomers", "https://www.canada.ca/en/financial-consumer-agency/services/banking.html"),
    ],
    "tfsa-newcomers-canada-2026": [
        ("Canada Revenue Agency — Tax-Free Savings Account (TFSA)", "https://www.canada.ca/en/revenue-agency/services/tax/individuals/topics/tax-free-savings-account.html"),
    ],
    "taxes-new-immigrants-canada-cra-guide-2026": [
        ("Canada Revenue Agency — Newcomers to Canada", "https://www.canada.ca/en/revenue-agency/services/tax/individuals/segments/tax-information-newcomers-canada-immigrants.html"),
    ],
    "rbc-vs-scotiabank-vs-td-newcomers-canada-2026": [
        ("Government of Canada — Choosing a Bank Account", "https://www.canada.ca/en/financial-consumer-agency/services/banking.html"),
    ],
    "bank-newcomer-bonus-300-cad-canada-2026": [
        ("Government of Canada — Financial Consumer Agency", "https://www.canada.ca/en/financial-consumer-agency.html"),
    ],
    "cheapest-provinces-canada-immigrants-2026": [
        ("Government of Canada — Cost of Living Information", "https://www.canada.ca/en/immigration-refugees-citizenship/services/new-immigrants/new-life-canada/living-costs.html"),
    ],
    "best-banks-iranian-newcomers-canada-2026": [
        ("Government of Canada — Banking for Newcomers", "https://www.canada.ca/en/financial-consumer-agency/services/banking.html"),
    ],
    "taxes-for-new-immigrants-to-the-usa-2026": [
        ("IRS — Taxation of Nonresident Aliens / New Immigrants", "https://www.irs.gov/individuals/international-taxpayers/taxation-of-nonresident-aliens"),
    ],
    "how-to-get-itin-number-usa-2026": [
        ("IRS — Individual Taxpayer Identification Number (ITIN)", "https://www.irs.gov/individuals/individual-taxpayer-identification-number"),
    ],
    "moving-to-canada-checklist-2026": [
        ("Government of Canada — New Immigrants Checklist", "https://www.canada.ca/en/immigration-refugees-citizenship/services/new-immigrants.html"),
    ],
    "best-phone-plans-newcomers-usa-2026": [
        ("FCC — Consumer Guide to Phone Service", "https://www.fcc.gov/consumers"),
    ],
    "first-apartment-usa-new-immigrants-2026": [
        ("HUD — Renting a Home", "https://www.hud.gov/topics/rental_assistance"),
    ],
    "best-high-yield-savings-accounts-newcomers-usa": [
        ("FDIC — Deposit Insurance & Savings Accounts", "https://www.fdic.gov/resources/deposit-insurance/"),
    ],
    "wise-vs-remitly-canada-2026": [
        ("Government of Canada — Sending Money Internationally", "https://www.canada.ca/en/financial-consumer-agency/services/banking.html"),
    ],
    "cost-of-living-canada-2026": [
        ("Government of Canada — Cost of Living for Newcomers", "https://www.canada.ca/en/immigration-refugees-citizenship/services/new-immigrants/new-life-canada/living-costs.html"),
    ],
    "cost-of-living-usa-2026": [
        ("Consumer Financial Protection Bureau — Budgeting", "https://www.consumerfinance.gov/consumer-tools/budgeting/"),
    ],
    "canada-budget-planner-2026": [
        ("Government of Canada — Budget Planner", "https://itools-ioutils.fcac-acfc.gc.ca/BP-PB/budget-planner"),
    ],
    "usa-budget-planner-2026": [
        ("Consumer Financial Protection Bureau — Budgeting Tools", "https://www.consumerfinance.gov/consumer-tools/budgeting/"),
    ],
}


def find_post_by_slug(slug):
    r = SESSION.get(f"{WP_URL}/wp-json/wp/v2/posts", params={"slug": slug}, timeout=30)
    r.raise_for_status()
    results = r.json()
    return results[0] if results else None


def verify_all_source_links():
    """Verifie CHAQUE url unique du mapping AVANT tout traitement.
    Utilise un User-Agent de navigateur (EXTERNAL_CHECK_SESSION) car beaucoup
    de sites .gov bloquent les requetes avec un User-Agent generique de bot.
    Retourne un dict url -> (ok: bool, detail: str)."""
    import time

    all_urls = set()
    for sources in SOURCES_MAP.values():
        for _, url in sources:
            all_urls.add(url)

    status = {}
    print(f"=== Verification de {len(all_urls)} URLs sources uniques (User-Agent navigateur) ===\n")
    for url in sorted(all_urls):
        try:
            r = EXTERNAL_CHECK_SESSION.get(url, timeout=25, allow_redirects=True)
            ok = r.status_code == 200
            status[url] = (ok, f"HTTP {r.status_code}" + (f" (apres {len(r.history)} redirection(s))" if r.history else ""))
        except Exception as e:
            status[url] = (False, f"erreur : {e}")
        marker = "✅" if status[url][0] else "❌"
        print(f"{marker} {url} — {status[url][1]}")
        time.sleep(0.5)
    print("")
    return status


def build_sources_block(slug, sources):
    intro = INTRO_VARIANTS[hash(slug) % len(INTRO_VARIANTS)]
    items = "\n".join(
        f'<li><a href="{url}" target="_blank" rel="noopener noreferrer">{label}</a></li>'
        for label, url in sources
    )
    return (
        f"\n{MARKER}\n"
        f'<h2>Official Resources</h2>\n'
        f'<p>{intro}</p>\n'
        f"<ul>\n{items}\n</ul>\n"
    )


def process_slug(slug, sources, apply_changes, link_status):
    post = find_post_by_slug(slug)
    if not post:
        print(f"[SKIP] {slug} — introuvable")
        return {"slug": slug, "status": "introuvable"}

    content = post["content"]["rendered"]
    if MARKER in content:
        print(f"[SKIP] {slug} — section deja presente, pas de doublon ajoute")
        return {"slug": slug, "status": "deja_present"}

    broken = [url for _, url in sources if not link_status.get(url, (False, ""))[0]]
    if broken:
        print(f"[BLOQUE] {slug} — lien(s) source casse(s) detecte(s), aucune modification appliquee : {broken}")
        return {"slug": slug, "status": "bloque_lien_casse", "broken_links": broken}

    block = build_sources_block(slug, sources)
    new_content = content + block

    if not apply_changes:
        print(f"[DRY-RUN] {slug} (post {post['id']}) — ajouterait :")
        print(block)
        return {"slug": slug, "status": "dry_run_ok", "post_id": post["id"]}

    update = SESSION.post(
        f"{WP_URL}/wp-json/wp/v2/posts/{post['id']}",
        json={"content": new_content},
        timeout=30,
    )
    update.raise_for_status()
    after = update.json()

    check = SESSION.get(after["link"], timeout=30)
    marker_present = MARKER in check.text
    print(f"[APPLIQUE] {slug} (post {post['id']}) — HTTP {check.status_code}, "
          f"section presente sur la page : {'oui' if marker_present else 'NON — A VERIFIER'}")

    return {
        "slug": slug,
        "status": "applique",
        "post_id": post["id"],
        "http_check": check.status_code,
        "marker_confirmed_live": marker_present,
    }


def main():
    apply_changes = "--apply" in sys.argv
    mode = "APPLY (ecriture reelle)" if apply_changes else "DRY-RUN (aucune ecriture)"
    print(f"=== Mode : {mode} ===")
    print(f"=== {len(SOURCES_MAP)} articles cibles ===\n")

    link_status = verify_all_source_links()
    broken_count = sum(1 for ok, _ in link_status.values() if not ok)
    if broken_count:
        print(f"⚠️ {broken_count} lien(s) source casse(s) detecte(s). "
              f"Les articles concernes seront BLOQUES automatiquement (aucune modification).\n")
    else:
        print("✅ Tous les liens sources sont valides.\n")

    results = []
    for slug, sources in SOURCES_MAP.items():
        result = process_slug(slug, sources, apply_changes, link_status)
        results.append(result)
        print("")

    print("=== Resume ===")
    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
        detail = ""
        if r["status"] == "applique":
            detail = f" (HTTP {r['http_check']}, section confirmee : {r['marker_confirmed_live']})"
        elif r["status"] == "bloque_lien_casse":
            detail = f" (liens casses : {r['broken_links']})"
        print(f"- {r['slug']} : {r['status']}{detail}")

    print("\n=== Totaux ===")
    for status_name, count in counts.items():
        print(f"{status_name} : {count}")

    if apply_changes and counts.get("bloque_lien_casse", 0) > 0:
        print("\n⚠️ ACTION REQUISE : corrige les URLs cassees dans SOURCES_MAP puis relance "
              "pour traiter les articles bloques.")


if __name__ == "__main__":
    main()
