#!/usr/bin/env python3
"""
Phase 7 - Sauvegarde d'un post AVANT toute correction.
LECTURE SEULE : ne fait que des GET, exporte le contenu actuel dans backups/.

Usage : python scripts/adsense_backup.py <slug_ou_post_id>
"""

import os
import sys
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
SESSION.headers.update({"User-Agent": "adsense-backup-bot/1.0"})


def find_post(identifier):
    """Accepte un slug ou un ID numerique."""
    if identifier.isdigit():
        r = SESSION.get(f"{WP_URL}/wp-json/wp/v2/posts/{identifier}", timeout=30)
        r.raise_for_status()
        return r.json()
    r = SESSION.get(f"{WP_URL}/wp-json/wp/v2/posts", params={"slug": identifier}, timeout=30)
    r.raise_for_status()
    results = r.json()
    if not results:
        raise SystemExit(f"ERREUR : aucun post trouve pour '{identifier}'")
    return results[0]


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage : python scripts/adsense_backup.py <slug_ou_post_id>")

    identifier = sys.argv[1]
    post = find_post(identifier)

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = f"backups/adsense-fix-{stamp}"
    os.makedirs(backup_dir, exist_ok=True)

    post_id = post["id"]
    slug = post["slug"]

    with open(f"{backup_dir}/post-{post_id}-{slug}-content.html", "w", encoding="utf-8") as f:
        f.write(post["content"]["rendered"])

    meta = {
        "id": post["id"],
        "slug": post["slug"],
        "status": post["status"],
        "title": post["title"]["rendered"],
        "date": post["date"],
        "modified": post["modified"],
        "link": post["link"],
    }
    with open(f"{backup_dir}/post-{post_id}-{slug}-meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"Sauvegarde creee : {backup_dir}/post-{post_id}-{slug}-content.html")
    print(f"Post ID : {post_id} | Slug : {slug} | Statut : {post['status']}")


if __name__ == "__main__":
    main()
