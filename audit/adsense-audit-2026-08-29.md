# Rapport d'audit AdSense — 2026-08-29

**Evaluation automatique : PRESQUE PRET**

> Rapport genere automatiquement en LECTURE SEULE via l'API REST WordPress. Aucune modification n'a ete effectuee sur le site. Validation humaine requise avant toute correction (Bloc 2 / Bloc 3).

## Resume — P0: 0 | P1: 1 | P2: 1

### P0 — Urgent
- Aucun

### P1 — A traiter
- us-expat-tax-filing-guide-2026 (NEXUS-14 — a verifier)

### P2 — A surveiller
- us-expat-tax-filing-guide-2026 (contenu faible : 190 mots)

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
  "post_id": 47409,
  "status": "publish",
  "modified": "2026-08-29T11:06:58",
  "word_count": 7525,
  "h1_count": 0,
  "h2_count": 14,
  "h3_count": 39,
  "table_count": 3,
  "link_count": 100,
  "suspicious_phrases_found": [],
  "internal_leak_markers": []
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
      "post_id": 1620,
      "status": "publish",
      "title": "Best Banks for New Immigrants &#038; Newcomers to Canada 2026: Top Picks",
      "word_count": 2942,
      "h2_count": 13,
      "table_count": 2
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
      "post_id": 47765,
      "status": "publish",
      "title": "RBC vs Scotiabank vs TD for Newcomers Canada 2026: Which Big Bank Wins?",
      "word_count": 2256,
      "h2_count": 10,
      "table_count": 1
    }
  ],
  "similarities": [
    {
      "pair": [
        "best-banks-newcomers-canada-2026",
        "rbc-vs-scotiabank-vs-td-newcomers-canada-2026"
      ],
      "jaccard_similarity": 0.264
    }
  ]
}
```

## Detail Phase 4 — Pages prioritaires NEXUS-14
```json
[
  {
    "slug": "taxes-for-new-immigrants-to-the-usa-2026",
    "post_id": 47692,
    "word_count": 2697,
    "h1_count": 0,
    "suspicious_phrases_found": [],
    "internal_leak_markers": [],
    "severity": "P2"
  },
  {
    "slug": "how-to-build-credit-in-usa-without-ssn",
    "post_id": 47152,
    "word_count": 6879,
    "h1_count": 0,
    "suspicious_phrases_found": [],
    "internal_leak_markers": [],
    "severity": "P2"
  },
  {
    "slug": "open-bank-account-newcomer-usa-2026",
    "post_id": 46779,
    "word_count": 5751,
    "h1_count": 0,
    "suspicious_phrases_found": [],
    "internal_leak_markers": [],
    "severity": "P2"
  },
  {
    "slug": "us-expat-tax-filing-guide-2026",
    "post_id": 46817,
    "word_count": 190,
    "h1_count": 0,
    "suspicious_phrases_found": [],
    "internal_leak_markers": [],
    "severity": "P1"
  }
]
```

## Detail Phase 5 — Audit global (59 posts scannes)
```json
{
  "total_posts_scanned": 59,
  "weak_pages": [
    {
      "slug": "us-expat-tax-filing-guide-2026",
      "post_id": 46817,
      "word_count": 190,
      "h2_count": 4
    }
  ],
  "internal_leak_pages": [],
  "suspicious_claim_pages": []
}
```

---
*Prochaine etape : lire ce rapport, puis lancer le Bloc 2 (sauvegardes + corrections) en session Claude Code supervisee — ce workflow ne corrige rien automatiquement.*