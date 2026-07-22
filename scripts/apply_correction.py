#!/usr/bin/env python3
"""
Applique UNE correction vers WordPress, apres validation humaine (GitHub Environment).
Ce script ne s'execute QUE si le job GitHub Actions a deja passe l'etape d'approbation.

Usage : python scripts/apply_correction.py <post_id> <fichier_html_corrige>
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
SESSION.headers.update({"User-Agent": "adsense-correction-bot/1.0"})


def main():
    if len(sys.argv) < 3:
        raise SystemExit("Usage : python scripts/apply_correction.py <post_id> <fichier_html>")

    post_id = sys.argv[1]
    html_path = sys.argv[2]

    if not os.path.exists(html_path):
        raise SystemExit(f"ERREUR : fichier introuvable : {html_path}")

    with open(html_path, "r", encoding="utf-8") as f:
        new_content = f.read()

    if not new_content.strip():
        raise SystemExit("ERREUR : le fichier de correction est vide. Rien n'est envoye.")

    forbidden_markers = ["notes internes", "internal notes", "TODO", "FIXME",
                          "as an ai", "```", "---\ntitle:"]
    lowered = new_content.lower()
    hits = [m for m in forbidden_markers if m.lower() in lowered]
    if hits:
        raise SystemExit(f"BLOQUE : le fichier contient encore des residus suspects : {hits}. "
                          f"Corrige le fichier avant de relancer.")

    r = SESSION.get(f"{WP_URL}/wp-json/wp/v2/posts/{post_id}", timeout=30)
    r.raise_for_status()
    before = r.json()
    print(f"AVANT : post {post_id} ({before['slug']}) — {len(before['content']['rendered'])} caracteres")

    update = SESSION.post(
        f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
        json={"content": new_content},
        timeout=30,
    )
    update.raise_for_status()
    after = update.json()
    print(f"APRES : post {post_id} — {len(after['content']['rendered'])} caracteres")
    print(f"Modifie le : {after['modified']}")

    check = SESSION.get(after["link"], timeout=30)
    print(f"Verification HTTP publique : {check.status_code} sur {after['link']}")
    if check.status_code != 200:
        print("ATTENTION : la page publique ne repond pas en 200. Verification manuelle requise.")

    print("Correction appliquee. Verification visuelle manuelle recommandee avant de considerer termine.")


if __name__ == "__main__":
    main()
