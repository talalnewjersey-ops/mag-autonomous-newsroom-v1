# Rapport final — Corrections d'indexation GSC (2026-07-28)

Exécution du plan validé le 2026-07-28 (LOT 1, LOT 2 restreint, LOT 3), suite à
`reports/gsc-indexation-audit-readonly-2026-07-28.md`. LOT 4 (ITIN vs SSN) et
LOT 5 (Financial Topics) sont restés strictement non exécutés, conformément à
l'interdiction explicite.

## Résumé

| Lot | Statut | Détail |
|---|---|---|
| LOT 1 — Redirections | ✅ **Exécuté et vérifié** | 3 redirections créées + 1 chaîne raccourcie. `tag/us-source-income` laissée en 404 comme demandé. |
| LOT 2 — Maillage interne | ⛔ **Non exécuté — bloqué techniquement** | La page cible est pilotée par Elementor ; aucun outil sûr et testé n'existe pour l'éditer sans risque. Rien n'a été tenté sur la production. |
| LOT 3 — Budget Planners | ✅ **Exécuté et vérifié** | Sources officielles étendues + 1 nouvelle FAQ par pays, sur les 2 pages. Calculateur intact. |
| LOT 4 — ITIN vs SSN | ⛔ Non touché (interdit) | Conforme à la consigne. |
| LOT 5 — Financial Topics | ⛔ Non touché (interdit) | Conforme à la consigne. |

---

## LOT 1 — Redirections

### Sauvegarde / état préalable

Opération strictement additive (le script `create_redirects_batch.py` ne modifie ni ne supprime jamais une redirection existante) — aucun export complet des 128 redirections n'était nécessaire au sens strict. L'état avant/après a été vérifié par requête directe à l'API du plugin Redirection avant et après chaque écriture (voir détail ci-dessous).

### Redirections créées

| Source | Cible | Sauts avant | Sauts après | Vérifié |
|---|---|---|---|---|
| `/tag/rent-apartment-canada/` | `/first-apartment-canada-newcomers-2026/` | — (404) | 1 | ✅ 301 confirmé en direct |
| `/tag/how-to-rent-canada-newcomer/` | `/first-apartment-canada-newcomers-2026/` | — (404) | 1 | ✅ 301 confirmé en direct |
| `/tag/private-landlord-canada/` | `/rent-without-credit-canada/` | — (404) | 1 | ✅ 301 confirmé en direct |

### Redirection mise à jour (pas créée — elle existait déjà)

| Source | Ancienne cible | Nouvelle cible | Sauts avant | Sauts après |
|---|---|---|---|---|
| `/can-foreigners-open-us-bank-account/` | `/can-foreigners-open-a-bank-account-in-the-us/` (redirect id=4) | `/best-banks-newcomers-usa-2026/` | 2 | **1**, vérifié |

**Anomalie rencontrée et corrigée en cours de route** : `create_redirects_batch.py` a ignoré (`SKIP`) cette URL car une redirection y existait déjà — mais elle pointait vers le maillon intermédiaire, pas la destination finale. Ce script ne sait que créer ou ignorer, jamais mettre à jour. Deux nouveaux outils ont été écrits pour combler ce manque (mêmes garanties de sécurité que le reste du repo — vérification de l'état exact avant écriture, refus si non conforme) :
- `scripts/list_wp_redirects.py` + `.github/workflows/list-redirects.yml` (lecture seule)
- `scripts/update_wp_redirect_target.py` + `.github/workflows/update-redirect-target.yml` (écriture, avec garde stricte sur la cible actuelle attendue)

### Explicitement exclue

`/tag/us-source-income/` — **laissée en 404**, aucune redirection créée, conformément à l'instruction (correspondance d'intention <80% pour les deux candidats évalués).

### Fichiers modifiés (repo)

- `audit/pending_redirects/2026-07-28-gsc-audit-lot1.json` (nouveau)
- `scripts/list_wp_redirects.py` (nouveau)
- `.github/workflows/list-redirects.yml` (nouveau)
- `scripts/update_wp_redirect_target.py` (nouveau)
- `.github/workflows/update-redirect-target.yml` (nouveau)

---

## LOT 2 — Maillage interne : blocage technique, rien exécuté

### Ce qui a été découvert

Avant toute écriture, sauvegarde de la page `newcomers-to-the-usa/` (id WordPress 1364) effectuée et committée : `backups/page-1364-newcomers-to-the-usa-pre-lot2-2026-07-28.json`.

Cette sauvegarde a révélé que la page est **pilotée par Elementor** (`_elementor_edit_mode: "builder"`, `_elementor_data` présent, 104 567 caractères de structure JSON). L'outil existant dans le repo pour éditer une page (`update_wp_page_content.py`) modifie le champ `post_content` — mais quand Elementor est en mode "builder", **le rendu réel de la page vient de `_elementor_data`, pas de `post_content`**. Modifier `post_content` ici n'aurait eu **aucun effet visible** sur la page en ligne : un "fix" silencieusement inefficace, indétectable sans revérifier manuellement.

Aucun outil de ce repo ne sait éditer `_elementor_data` (structure JSON imbriquée de widgets) de façon sûre et testée. Plutôt que d'improviser une modification non testée sur cette structure en production, j'ai arrêté le LOT 2 et ne l'ai pas exécuté.

### Les 3 modifications qui restent à faire (non exécutées)

1. Corriger le `href` de la carte "💵 Cost of Living" dans la grille "Resource Center" (pointe actuellement vers `taxes-for-new-immigrants-to-the-usa-2026/`, devrait pointer vers `cost-of-living-usa-2026/`).
2. Lier le texte existant "the true cost of living in your city" (section "Common Mistakes to Avoid") vers `cost-of-living-usa-2026/`.
3. Lier le mot existant "budget" (section "Practical Tips", phrase "Start your budget before spending patterns set in...") vers `usa-budget-planner-2026/`.

### Options pour débloquer

- **Option A (recommandée, la plus rapide)** : tu fais ces 3 modifications toi-même dans l'éditeur visuel Elementor — chacune prend quelques secondes (changer un lien de bouton, sélectionner du texte et ajouter un lien). Aucun risque, aucun outil à construire.
- **Option B** : je construis et teste un nouvel outil dédié à l'édition ciblée de `_elementor_data` (recherche du widget par son contenu texte, remplacement chirurgical, mêmes garanties de sécurité que le reste du repo) — plus long, et je demanderais une validation explicite séparée avant de l'exécuter sur cette page en production, étant donné la sensibilité plus élevée de ce type d'édition.
- **Option C** : laisser le LOT 2 de côté pour l'instant.

---

## LOT 3 — Budget Planners

### USA Budget Planner (`usa-budget-planner-2026/`, post id 1624)

**Sources officielles** — passées de 1 à 6 :
- Consumer Financial Protection Bureau (déjà présente)
- U.S. Census Bureau — American Community Survey *(nouveau)*
- Bureau of Labor Statistics — Consumer Price Index *(nouveau)*
- IRS — Federal Income Tax Rates and Brackets *(nouveau)*
- HUD — Fair Market Rents by Metro Area *(nouveau)*
- Healthcare.gov — Marketplace Plans and Pricing *(nouveau)*

**Nouvelle FAQ ajoutée** : "Which US states have no state income tax, and does that affect my monthly budget?" (Alaska, Floride, Nevada, New Hampshire, Dakota du Sud, Tennessee, Texas, Washington, Wyoming — avec la nuance sur la taxe de vente/propriété compensatoire).

### Canada Budget Planner (`canada-budget-planner-2026/`, post id 1625)

**Sources officielles** — passées de 1 à 5 :
- Gouvernement du Canada — Budget Planner (déjà présente)
- Statistique Canada — Indice des prix à la consommation par province *(nouveau)*
- Gouvernement du Canada — Budgétiser sa première année *(nouveau)*
- Agence du revenu du Canada — Taux d'imposition fédéraux *(nouveau)*
- SCHL/CMHC — Rapports sur le marché locatif par ville *(nouveau)*

**Nouvelle FAQ ajoutée** : "Does the GST/HST rate change my monthly budget depending on the province?" (Ontario/Atlantique 13-15% HST, Alberta/territoires 5% GST seul, Québec/CB GST + taxe provinciale séparée).

### Ce qui n'a délibérément PAS été touché

- Le simulateur interactif complet (sections "Where Will You Live?", "Your Situation", "Fine-Tune Your Estimates") — intact, vérifié présent après modification.
- Le JavaScript de calcul (`updateCalculator`, logique des boutons de ville) — intact, vérifié présent (5 occurrences des fonctions de calcul retrouvées).
- Les résultats chiffrés et leur logique.
- Le schéma JSON-LD `FAQPage` existant — **anomalie pré-existante notée mais non corrigée** : ce schéma contenait déjà, avant toute intervention, un jeu de questions totalement différent de la FAQ visible affichée sur la page (découvert en préparant ce lot). Je n'ai pas touché ce schéma pour ne pas élargir le périmètre autorisé ; mes 2 nouvelles FAQ visibles n'y ont donc pas été ajoutées. À signaler pour un futur chantier séparé si tu veux corriger cette désynchronisation plus large.

### Fichiers modifiés (repo)

- `audit/pending_fixes/2026-07-28-lot3-usa-official-resources.json`
- `audit/pending_fixes/2026-07-28-lot3-usa-new-faq.json`
- `audit/pending_fixes/2026-07-28-lot3-canada-official-resources.json`
- `audit/pending_fixes/2026-07-28-lot3-canada-new-faq.json`

---

## URLs WordPress modifiées

| URL | Type de modification |
|---|---|
| `/can-foreigners-open-us-bank-account/` | Redirection mise à jour (cible directe) |
| `/tag/rent-apartment-canada/` | Redirection créée |
| `/tag/how-to-rent-canada-newcomer/` | Redirection créée |
| `/tag/private-landlord-canada/` | Redirection créée |
| `/usa-budget-planner-2026/` | Contenu modifié (post 1624) |
| `/canada-budget-planner-2026/` | Contenu modifié (post 1625) |

**Non modifiées** : `/tag/us-source-income/` (exclue volontairement), `/newcomers-to-the-usa/` (LOT 2 bloqué), pages ITIN et `/financial-topics/` (LOT 4/5 interdits).

---

## Tests réalisés et résultats

| Test | Résultat |
|---|---|
| Statut HTTP des 3 nouvelles redirections | ✅ 301, 1 saut chacune, confirmé par requête directe (`Location:` header) |
| Statut HTTP de la redirection mise à jour | ✅ 301, 1 saut, cible = `/best-banks-newcomers-usa-2026/` |
| Statut HTTP des 3 pages de destination finale | ✅ 200 chacune (`best-banks-newcomers-usa-2026`, `first-apartment-canada-newcomers-2026`, `rent-without-credit-canada`) |
| `/tag/us-source-income/` toujours 404 | ✅ Confirmé, aucune redirection créée |
| Absence de boucle de redirection | ✅ Chaque redirection testée résout en 1 saut vers une page 200 |
| Statut HTTP des 2 budget planners après édition | ✅ 200 chacun |
| Nouveau contenu présent en direct (sources + FAQ) | ✅ Confirmé par grep sur le HTML live — 5/5 sources USA, 4/4 sources Canada, 2 nouvelles FAQ (titres H3 bien rendus par le plugin Table of Contents) |
| Calculateur/JS intact après édition | ✅ Confirmé présent, structure et fonctions JS retrouvées inchangées |
| Canonical après édition | ✅ Toujours self-référent sur les 2 pages |
| Absence d'erreur PHP visible | ✅ Aucune occurrence de "Fatal error"/"Parse error"/"Warning" dans le HTML |
| GA4/GTM toujours présent | ✅ Confirmé sur les 2 pages |
| Cache LiteSpeed | ✅ Contenu déjà à jour dans les deux cas testés (un HIT avec le nouveau contenu, un MISS) — **aucune purge nécessaire** |
| Rendu desktop/mobile (visuel) | ⚠️ **Non testé** — aucun outil de capture d'écran/navigateur disponible dans cet environnement ; seule la vérification HTML/HTTP a été possible. Recommandation : un contrôle visuel rapide de ta part sur les 2 pages Budget Planner est prudent avant de considérer le LOT 3 totalement clos. |
| Régression Elementor/Yoast | ✅ Non applicable pour LOT 1/3 (aucune page Elementor touchée) ; sujet central du blocage LOT 2 (voir ci-dessus) |
| Fil d'Ariane | Non présent sur les pages concernées (non applicable) |

---

## Anomalies restantes

1. **LOT 2 entièrement en attente** — voir options ci-dessus.
2. **Désynchronisation pré-existante du schéma FAQPage** sur les 2 budget planners (schéma structuré ≠ FAQ visible) — pas causée par cette session, pas corrigée non plus (hors périmètre du lot autorisé).
3. **Deux échecs réseau transitoires** pendant l'exécution (`Errno 101: Network is unreachable`, déjà documentés comme récurrents sur ce repo, ~1 run sur 4) — aucun impact, les relances ont réussi immédiatement, aucune écriture partielle n'a eu lieu lors des échecs (l'erreur intervenait avant l'appel d'écriture).
4. **Rendu visuel non vérifié** (pas d'outil de capture disponible) — recommandé de vérifier visuellement les 2 pages Budget Planner.

---

## Actions manuelles à effectuer dans Google Search Console

Aucune n'a été effectuée par moi (conforme à la consigne permanente : je ne clique jamais sur "Validate Fix" moi-même). Recommandations :
- Une fois le LOT 2 réglé (par toi ou par un futur chantier), envisager une nouvelle demande de validation sur le rapport "Page with redirect" et "Not found (404)" via Claude for Chrome, comme fait précédemment.
- Surveiller dans les prochaines semaines si `usa-budget-planner-2026`, `canada-budget-planner-2026`, `cost-of-living-usa-2026`, `itin-vs-ssn-...-guide` et `financial-topics` sortent du statut "Crawled – currently not indexed" — aucune garantie d'indexation n'est possible de ma part, Google reste seul décisionnaire.
- Ne pas demander d'indexation manuelle en masse.

---

*Rapport généré après exécution des lots explicitement validés. LOT 2 non exécuté par prudence technique justifiée ci-dessus. LOT 4 et LOT 5 non touchés, conformément à l'interdiction explicite.*
