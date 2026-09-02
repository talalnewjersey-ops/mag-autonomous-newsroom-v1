# Rapport d'audit AdSense — 2026-09-02

**Evaluation automatique : PRESQUE PRET**

> Rapport genere automatiquement en LECTURE SEULE via l'API REST WordPress. Aucune modification n'a ete effectuee sur le site. Validation humaine requise avant toute correction (Bloc 2 / Bloc 3).

## Resume — P0: 0 | P1: 4 | P2: 0

### P0 — Urgent
- Aucun

### P1 — A traiter
- taxes-for-new-immigrants-to-the-usa-2026 (NEXUS-14 — a verifier)
- how-to-build-credit-in-usa-without-ssn (NEXUS-14 — a verifier)
- open-bank-account-newcomer-usa-2026 (NEXUS-14 — a verifier)
- us-expat-tax-filing-guide-2026 (NEXUS-14 — a verifier)

### P2 — A surveiller
- Aucun

## Detail Phase 0 — Site
```json
{
  "site_name": "Money Abroad Guide",
  "site_url": "https://moneyabroadguide.com",
  "description": "Educational personal finance blog for expats in the USA and Canada. Learn banking, taxes, credit, budgeting, and smart money management.",
  "note": "Liste des plugins actifs non accessible via REST API standard. A verifier manuellement (wp-admin > Plugins) si necessaire."
}
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
  "http_status": 200,
  "still_broken": false,
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
- find_post_by_slug(best-banks-newcomers-usa-2026): 404 Client Error: Not Found for url: https://moneyabroadguide.com/wp-json/wp/v2/posts?slug=best-banks-newcomers-usa-2026
- phase2 search: 404 Client Error: Not Found for url: https://moneyabroadguide.com/wp-json/wp/v2/posts?search=best-us-banks-for-foreigners-2026-guide&per_page=50
- find_post_by_slug(best-banks-newcomers-canada-2026): 404 Client Error: Not Found for url: https://moneyabroadguide.com/wp-json/wp/v2/posts?slug=best-banks-newcomers-canada-2026
- find_post_by_slug(best-banks-newcomers-canada): 404 Client Error: Not Found for url: https://moneyabroadguide.com/wp-json/wp/v2/posts?slug=best-banks-newcomers-canada
- find_post_by_slug(best-newcomer-bank-accounts-in-canada-complete-guide-for-canada-immigrants-2026): 404 Client Error: Not Found for url: https://moneyabroadguide.com/wp-json/wp/v2/posts?slug=best-newcomer-bank-accounts-in-canada-complete-guide-for-canada-immigrants-2026
- find_post_by_slug(rbc-vs-scotiabank-vs-td-newcomers-canada-2026): 404 Client Error: Not Found for url: https://moneyabroadguide.com/wp-json/wp/v2/posts?slug=rbc-vs-scotiabank-vs-td-newcomers-canada-2026
- find_post_by_slug(best-banks-newcomers-canada-2026): 404 Client Error: Not Found for url: https://moneyabroadguide.com/wp-json/wp/v2/posts?slug=best-banks-newcomers-canada-2026
- find_post_by_slug(best-banks-newcomers-canada): 404 Client Error: Not Found for url: https://moneyabroadguide.com/wp-json/wp/v2/posts?slug=best-banks-newcomers-canada
- find_post_by_slug(best-newcomer-bank-accounts-in-canada-complete-guide-for-canada-immigrants-2026): 404 Client Error: Not Found for url: https://moneyabroadguide.com/wp-json/wp/v2/posts?slug=best-newcomer-bank-accounts-in-canada-complete-guide-for-canada-immigrants-2026
- find_post_by_slug(rbc-vs-scotiabank-vs-td-newcomers-canada-2026): 404 Client Error: Not Found for url: https://moneyabroadguide.com/wp-json/wp/v2/posts?slug=rbc-vs-scotiabank-vs-td-newcomers-canada-2026
- find_post_by_slug(taxes-for-new-immigrants-to-the-usa-2026): 404 Client Error: Not Found for url: https://moneyabroadguide.com/wp-json/wp/v2/posts?slug=taxes-for-new-immigrants-to-the-usa-2026
- find_post_by_slug(how-to-build-credit-in-usa-without-ssn): 404 Client Error: Not Found for url: https://moneyabroadguide.com/wp-json/wp/v2/posts?slug=how-to-build-credit-in-usa-without-ssn
- find_post_by_slug(open-bank-account-newcomer-usa-2026): 404 Client Error: Not Found for url: https://moneyabroadguide.com/wp-json/wp/v2/posts?slug=open-bank-account-newcomer-usa-2026
- find_post_by_slug(us-expat-tax-filing-guide-2026): 404 Client Error: Not Found for url: https://moneyabroadguide.com/wp-json/wp/v2/posts?slug=us-expat-tax-filing-guide-2026
- all_posts page 1: 404 Client Error: Not Found for url: https://moneyabroadguide.com/wp-json/wp/v2/posts?per_page=50&page=1&status=publish

---
*Prochaine etape : lire ce rapport, puis lancer le Bloc 2 (sauvegardes + corrections) en session Claude Code supervisee — ce workflow ne corrige rien automatiquement.*