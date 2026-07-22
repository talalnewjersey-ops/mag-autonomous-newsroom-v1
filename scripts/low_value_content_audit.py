#!/usr/bin/env python3
"""
Audit specifique "Low Value Content" (motif de refus AdSense).
LECTURE SEULE. Complementaire a adsense_audit.py (Bloc 1) et
phase12_technical_checks.py — celui-ci cible les 4 criteres que Google
cite explicitement : minimum content, unicite, thin content, qualite globale.

IMPORTANT : ce script fournit des SIGNAUX, pas un verdict. La decision
finale de resoumettre reste un jugement editorial humain.
"""

import os
import re
import json
import socket
import datetime
import itertools
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
SESSION.headers.update({"User-Agent": "adsense-low-value-audit-bot/1.0"})

TODAY = datetime.date.today().isoformat()
REPORT_DIR = "audit"
REPORT_PATH = f"{REPORT_DIR}/low-value-content-audit-{TODAY}.md"

THIN_CONTENT_WORDS = 800
SIMILARITY_ALERT_THRESHOLD = 0.45

TRUST_PAGE_SLUGS = {
    "About": ["about", "about-us"],
    "Contact": ["contact", "contact-us"],
    "Privacy Policy": ["privacy-policy", "privacy"],
    "Terms": ["terms", "terms-of-service", "terms-and-conditions"],
    "Editorial Policy": ["editorial-policy"],
    "Affiliate Disclosure": ["affiliate-disclosure", "disclosure"],
    "Disclaimer": ["disclaimer"],
}

AUTHORITATIVE_DOMAINS = [
    "irs.gov", "cra-arc.gc.ca", "canada.ca", "uscis.gov", "fdic.gov",
    "consumerfinance.gov", ".gov", "federalreserve.gov",
]

results = {
    "trust_pages": {},
    "content_stats": {},
    "thin_pages": [],
    "similarity_alerts": [],
    "eeat_signals": [],
    "errors": [],
}


def strip_html(html):
    return re.sub(r"<[^>]+>", " ", html or "")


def word_count(html):
    return len(strip_html(html).split())


def find_page_by_slugs(slug_candidates):
    for slug in slug_candidates:
        for post_type in ["pages", "posts"]:
            try:
                r = SESSION.get(f"{WP_URL}/wp-json/wp/v2/{post_type}", params={"slug": slug}, timeout=20)
                r.raise_for_status()
                found = r.json()
                if found:
                    return found[0]
            except Exception as e:
                results["errors"].append(f"find_page_by_slugs({slug}): {e}")
    return None


def check_trust_pages():
    for label, slugs in TRUST_PAGE_SLUGS.items():
        page = find_page_by_slugs(slugs)
        if page:
            wc = word_count(page["content"]["rendered"])
            results["trust_pages"][label] = {
                "found": True,
                "slug": page["slug"],
                "word_count": wc,
                "thin": wc < 150,
            }
        else:
            results["trust_pages"][label] = {"found": False}


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


def count_authoritative_links(html):
    links = re.findall(r'href="([^"]+)"', html or "")
    count = 0
    for link in links:
        if any(domain in link for domain in AUTHORITATIVE_DOMAINS):
            count += 1
    return count


def main():
    check_trust_pages()

    posts = all_published_posts()
    word_counts = []
    texts_for_similarity = {}

    for p in posts:
        content = p["content"]["rendered"]
        text = strip_html(content)
        wc = word_count(content)
        word_counts.append(wc)

        if wc < THIN_CONTENT_WORDS:
            results["thin_pages"].append({"slug": p["slug"], "post_id": p["id"], "word_count": wc})

        auth_links = count_authoritative_links(content)
        has_author = bool(p.get("author"))
        results["eeat_signals"].append({
            "slug": p["slug"],
            "post_id": p["id"],
            "authoritative_source_links": auth_links,
            "has_author_field": has_author,
            "modified": p.get("modified"),
            "low_eeat_signal": auth_links == 0,
        })

        words = set(text.lower().split())
        texts_for_similarity[p["slug"]] = words

    if word_counts:
        results["content_stats"] = {
            "total_posts": len(word_counts),
            "avg_word_count": round(sum(word_counts) / len(word_counts)),
            "min_word_count": min(word_counts),
            "max_word_count": max(word_counts),
            "posts_under_threshold": len(results["thin_pages"]),
        }

    slugs = list(texts_for_similarity.keys())
    for a, b in itertools.combinations(slugs, 2):
        set_a, set_b = texts_for_similarity[a], texts_for_similarity[b]
        if not set_a or not set_b:
            continue
        similarity = len(set_a & set_b) / max(1, len(set_a | set_b))
        if similarity >= SIMILARITY_ALERT_THRESHOLD:
            results["similarity_alerts"].append({
                "pair": [a, b],
                "jaccard_similarity": round(similarity, 3),
            })

    results["similarity_alerts"].sort(key=lambda x: -x["jaccard_similarity"])

    lines = []
    lines.append(f"# Audit \"Low Value Content\" (motif AdSense) — {TODAY}")
    lines.append("")
    lines.append("> Ce rapport fournit des SIGNAUX quantitatifs, pas un verdict. "
                  "La decision de resoumettre a AdSense reste un jugement editorial humain, "
                  "notamment sur ce que ces chiffres ne peuvent pas mesurer : la qualite reelle "
                  "de la redaction, la pertinence pour le lecteur, la confiance percue.")
    lines.append("")

    lines.append("## 1. Pages de confiance (trust pages)")
    lines.append("Google evalue explicitement leur presence pour juger de la fiabilite du site.")
    lines.append("")
    for label, info in results["trust_pages"].items():
        if info["found"]:
            flag = " ⚠️ CONTENU TRES COURT" if info.get("thin") else ""
            lines.append(f"- ✅ {label} : trouvee (`{info['slug']}`, {info['word_count']} mots){flag}")
        else:
            lines.append(f"- ❌ {label} : **INTROUVABLE** — a creer ou renommer avec un slug standard")
    lines.append("")

    lines.append("## 2. Profondeur du contenu (site entier)")
    cs = results["content_stats"]
    lines.append(f"- {cs.get('total_posts', 0)} articles publies analyses")
    lines.append(f"- Longueur moyenne : {cs.get('avg_word_count', 0)} mots")
    lines.append(f"- Min / Max : {cs.get('min_word_count', 0)} / {cs.get('max_word_count', 0)} mots")
    lines.append(f"- Articles sous le seuil de {THIN_CONTENT_WORDS} mots : {cs.get('posts_under_threshold', 0)}")
    lines.append("")
    if results["thin_pages"]:
        lines.append("### Articles a verifier en priorite (contenu court)")
        for p in sorted(results["thin_pages"], key=lambda x: x["word_count"]):
            lines.append(f"- {p['slug']} — {p['word_count']} mots")
        lines.append("")

    lines.append(f"## 3. Similarite site-large (seuil d'alerte : {SIMILARITY_ALERT_THRESHOLD})")
    lines.append("Contrairement au Bloc 1 (limite aux pages Canada), ceci compare TOUS les articles entre eux.")
    lines.append("")
    if results["similarity_alerts"]:
        lines.append("### Paires a verifier manuellement (risque de cannibalisation/contenu repetitif)")
        for s in results["similarity_alerts"][:20]:
            lines.append(f"- {s['pair'][0]} ↔ {s['pair'][1]} — similarite {s['jaccard_similarity']}")
        if len(results["similarity_alerts"]) > 20:
            lines.append(f"- ... et {len(results['similarity_alerts']) - 20} autres paires au-dessus du seuil")
    else:
        lines.append(f"Aucune paire au-dessus du seuil de {SIMILARITY_ALERT_THRESHOLD}.")
    lines.append("")

    low_eeat = [e for e in results["eeat_signals"] if e["low_eeat_signal"]]
    lines.append("## 4. Signaux E-E-A-T (autorite / fiabilite)")
    lines.append(f"Articles sans aucun lien vers une source officielle (.gov, IRS, CRA, FDIC...) : {len(low_eeat)}")
    lines.append("")
    if low_eeat:
        lines.append("### Articles sans source autoritaire citee")
        for e in low_eeat:
            lines.append(f"- {e['slug']}")
        lines.append("")

    if results["errors"]:
        lines.append("## Erreurs rencontrees")
        lines.extend([f"- {e}" for e in results["errors"]])
        lines.append("")

    lines.append("---")
    lines.append("### Checklist manuelle recommandee avant resoumission")
    lines.append("- [ ] Lire 4-5 articles au hasard comme un vrai visiteur (pas seulement ceux deja audites)")
    lines.append("- [ ] Verifier que les pages de confiance manquantes ci-dessus sont creees")
    lines.append("- [ ] Pour chaque paire de similarite elevee : confirmer une intention de recherche differente ou fusionner")
    lines.append("- [ ] Confirmer que les articles courts listes ont malgre tout une vraie valeur (pas juste \"thin\")")

    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Rapport genere : {REPORT_PATH}")
    print(json.dumps(results["content_stats"], indent=2))


if __name__ == "__main__":
    main()
