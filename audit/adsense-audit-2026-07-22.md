# Rapport d'audit AdSense — 2026-07-22

**Evaluation automatique : PRESQUE PRET**

> Rapport genere automatiquement en LECTURE SEULE via l'API REST WordPress. Aucune modification n'a ete effectuee sur le site. Validation humaine requise avant toute correction (Bloc 2 / Bloc 3).

## Resume — P0: 0 | P1: 5 | P2: 0

### P0 — Urgent
- Aucun

### P1 — A traiter
- Lien mort actif : best-us-banks-for-foreigners-2026-guide
- taxes-for-new-immigrants-to-the-usa-2026 (NEXUS-14 — a verifier)
- how-to-build-credit-in-usa-without-ssn (NEXUS-14 — a verifier)
- open-bank-account-newcomer-usa-2026 (NEXUS-14 — a verifier)
- us-expat-tax-filing-guide-2026 (NEXUS-14 — a verifier)

### P2 — A surveiller
- Aucun

## Detail Phase 0 — Site
```json
{}
```

## Detail Phase 1 — Article USA (best-banks-newcomers-usa-2026)
```json
{
  "status": "INTROUVABLE",
  "slug": "best-banks-newcomers-usa-2026"
}
```

## Detail Phase 2 — Lien mort (best-us-banks-for-foreigners-2026-guide)
```json
{
  "dead_url": "https://moneyabroadguide.com/best-us-banks-for-foreigners-2026-guide/",
  "http_status": null,
  "still_broken": "inconnu",
  "referencing_posts": []
}
```

## Detail Phase 3 — Pages Canada
```json
{
  "pages": [
    {
      "slug": "best-banks-newcomers-canada-2026",
      "status": "INTROUVABLE"
    },
    {
      "slug": "best-banks-newcomers-canada",
      "status": "INTROUVABLE"
    },
    {
      "slug": "best-newcomer-bank-accounts-in-canada-complete-guide-for-canada-immigrants-2026",
      "status": "INTROUVABLE"
    },
    {
      "slug": "rbc-vs-scotiabank-vs-td-newcomers-canada-2026",
      "status": "INTROUVABLE"
    }
  ],
  "similarities": []
}
```

## Detail Phase 4 — Pages prioritaires NEXUS-14
```json
[
  {
    "slug": "taxes-for-new-immigrants-to-the-usa-2026",
    "status": "INTROUVABLE",
    "severity": "P1"
  },
  {
    "slug": "how-to-build-credit-in-usa-without-ssn",
    "status": "INTROUVABLE",
    "severity": "P1"
  },
  {
    "slug": "open-bank-account-newcomer-usa-2026",
    "status": "INTROUVABLE",
    "severity": "P1"
  },
  {
    "slug": "us-expat-tax-filing-guide-2026",
    "status": "INTROUVABLE",
    "severity": "P1"
  }
]
```

## Detail Phase 5 — Audit global (0 posts scannes)
```json
{
  "total_posts_scanned": 0,
  "weak_pages": [],
  "internal_leak_pages": [],
  "suspicious_claim_pages": []
}
```

## Erreurs rencontrees pendant l'audit
- phase0: HTTPSConnectionPool(host='moneyabroadguide.com', port=443): Max retries exceeded with url: /wp-json/ (Caused by NewConnectionError("HTTPSConnection(host='moneyabroadguide.com', port=443): Failed to establish a new connection: [Errno 101] Network is unreachable"))
- find_post_by_slug(best-banks-newcomers-usa-2026): HTTPSConnectionPool(host='moneyabroadguide.com', port=443): Max retries exceeded with url: /wp-json/wp/v2/posts?slug=best-banks-newcomers-usa-2026 (Caused by NewConnectionError("HTTPSConnection(host='moneyabroadguide.com', port=443): Failed to establish a new connection: [Errno 101] Network is unreachable"))
- phase2 curl: HTTPSConnectionPool(host='moneyabroadguide.com', port=443): Max retries exceeded with url: /best-us-banks-for-foreigners-2026-guide/ (Caused by NewConnectionError("HTTPSConnection(host='moneyabroadguide.com', port=443): Failed to establish a new connection: [Errno 101] Network is unreachable"))
- phase2 search: HTTPSConnectionPool(host='moneyabroadguide.com', port=443): Max retries exceeded with url: /wp-json/wp/v2/posts?search=best-us-banks-for-foreigners-2026-guide&per_page=50 (Caused by NewConnectionError("HTTPSConnection(host='moneyabroadguide.com', port=443): Failed to establish a new connection: [Errno 101] Network is unreachable"))
- find_post_by_slug(best-banks-newcomers-canada-2026): HTTPSConnectionPool(host='moneyabroadguide.com', port=443): Max retries exceeded with url: /wp-json/wp/v2/posts?slug=best-banks-newcomers-canada-2026 (Caused by NewConnectionError("HTTPSConnection(host='moneyabroadguide.com', port=443): Failed to establish a new connection: [Errno 101] Network is unreachable"))
- find_post_by_slug(best-banks-newcomers-canada): HTTPSConnectionPool(host='moneyabroadguide.com', port=443): Max retries exceeded with url: /wp-json/wp/v2/posts?slug=best-banks-newcomers-canada (Caused by NewConnectionError("HTTPSConnection(host='moneyabroadguide.com', port=443): Failed to establish a new connection: [Errno 101] Network is unreachable"))
- find_post_by_slug(best-newcomer-bank-accounts-in-canada-complete-guide-for-canada-immigrants-2026): HTTPSConnectionPool(host='moneyabroadguide.com', port=443): Max retries exceeded with url: /wp-json/wp/v2/posts?slug=best-newcomer-bank-accounts-in-canada-complete-guide-for-canada-immigrants-2026 (Caused by NewConnectionError("HTTPSConnection(host='moneyabroadguide.com', port=443): Failed to establish a new connection: [Errno 101] Network is unreachable"))
- find_post_by_slug(rbc-vs-scotiabank-vs-td-newcomers-canada-2026): HTTPSConnectionPool(host='moneyabroadguide.com', port=443): Max retries exceeded with url: /wp-json/wp/v2/posts?slug=rbc-vs-scotiabank-vs-td-newcomers-canada-2026 (Caused by NewConnectionError("HTTPSConnection(host='moneyabroadguide.com', port=443): Failed to establish a new connection: [Errno 101] Network is unreachable"))
- find_post_by_slug(best-banks-newcomers-canada-2026): HTTPSConnectionPool(host='moneyabroadguide.com', port=443): Max retries exceeded with url: /wp-json/wp/v2/posts?slug=best-banks-newcomers-canada-2026 (Caused by NewConnectionError("HTTPSConnection(host='moneyabroadguide.com', port=443): Failed to establish a new connection: [Errno 101] Network is unreachable"))
- find_post_by_slug(best-banks-newcomers-canada): HTTPSConnectionPool(host='moneyabroadguide.com', port=443): Max retries exceeded with url: /wp-json/wp/v2/posts?slug=best-banks-newcomers-canada (Caused by NewConnectionError("HTTPSConnection(host='moneyabroadguide.com', port=443): Failed to establish a new connection: [Errno 101] Network is unreachable"))
- find_post_by_slug(best-newcomer-bank-accounts-in-canada-complete-guide-for-canada-immigrants-2026): HTTPSConnectionPool(host='moneyabroadguide.com', port=443): Max retries exceeded with url: /wp-json/wp/v2/posts?slug=best-newcomer-bank-accounts-in-canada-complete-guide-for-canada-immigrants-2026 (Caused by NewConnectionError("HTTPSConnection(host='moneyabroadguide.com', port=443): Failed to establish a new connection: [Errno 101] Network is unreachable"))
- find_post_by_slug(rbc-vs-scotiabank-vs-td-newcomers-canada-2026): HTTPSConnectionPool(host='moneyabroadguide.com', port=443): Max retries exceeded with url: /wp-json/wp/v2/posts?slug=rbc-vs-scotiabank-vs-td-newcomers-canada-2026 (Caused by NewConnectionError("HTTPSConnection(host='moneyabroadguide.com', port=443): Failed to establish a new connection: [Errno 101] Network is unreachable"))
- find_post_by_slug(taxes-for-new-immigrants-to-the-usa-2026): HTTPSConnectionPool(host='moneyabroadguide.com', port=443): Max retries exceeded with url: /wp-json/wp/v2/posts?slug=taxes-for-new-immigrants-to-the-usa-2026 (Caused by NewConnectionError("HTTPSConnection(host='moneyabroadguide.com', port=443): Failed to establish a new connection: [Errno 101] Network is unreachable"))
- find_post_by_slug(how-to-build-credit-in-usa-without-ssn): HTTPSConnectionPool(host='moneyabroadguide.com', port=443): Max retries exceeded with url: /wp-json/wp/v2/posts?slug=how-to-build-credit-in-usa-without-ssn (Caused by NewConnectionError("HTTPSConnection(host='moneyabroadguide.com', port=443): Failed to establish a new connection: [Errno 101] Network is unreachable"))
- find_post_by_slug(open-bank-account-newcomer-usa-2026): HTTPSConnectionPool(host='moneyabroadguide.com', port=443): Max retries exceeded with url: /wp-json/wp/v2/posts?slug=open-bank-account-newcomer-usa-2026 (Caused by NewConnectionError("HTTPSConnection(host='moneyabroadguide.com', port=443): Failed to establish a new connection: [Errno 101] Network is unreachable"))
- find_post_by_slug(us-expat-tax-filing-guide-2026): HTTPSConnectionPool(host='moneyabroadguide.com', port=443): Max retries exceeded with url: /wp-json/wp/v2/posts?slug=us-expat-tax-filing-guide-2026 (Caused by NewConnectionError("HTTPSConnection(host='moneyabroadguide.com', port=443): Failed to establish a new connection: [Errno 101] Network is unreachable"))
- all_posts page 1: HTTPSConnectionPool(host='moneyabroadguide.com', port=443): Max retries exceeded with url: /wp-json/wp/v2/posts?per_page=50&page=1&status=publish (Caused by NewConnectionError("HTTPSConnection(host='moneyabroadguide.com', port=443): Failed to establish a new connection: [Errno 101] Network is unreachable"))

---
*Prochaine etape : lire ce rapport, puis lancer le Bloc 2 (sauvegardes + corrections) en session Claude Code supervisee — ce workflow ne corrige rien automatiquement.*