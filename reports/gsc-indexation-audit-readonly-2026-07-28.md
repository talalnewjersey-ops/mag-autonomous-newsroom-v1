# Audit d'indexation GSC — MoneyAbroadGuide.com (lecture seule)

**Date** : 2026-07-28
**Portée** : redirections, maillage interne, indexabilité, chevauchements éditoriaux, pages "Crawled – currently not indexed"
**Hors périmètre** : refonte visuelle homepage, design, header/footer, templates Elementor, plugin Fusion — non touchés, non analysés ici.
**Statut** : PHASE 1 (audit) + PHASE 2 (plan) terminées. Aucune modification effectuée. En attente de validation explicite.

---

## 1. Résumé exécutif

Le site a bénéficié le 27/07/2026 d'un chantier de correction de 125 redirections qui a résolu la majorité des problèmes remontés par Search Console. Ce qui reste ouvert, dans le périmètre de cette mission :

- **1 chaîne de redirection à 2 sauts** au lieu d'1 (`can-foreigners-open-us-bank-account/`), fonctionnelle mais non optimale.
- **4 pages de tags mortes** (404 confirmé) sans redirection, contrairement à 9 tags similaires déjà corrigés hier.
- **5 pages réelles, indexables, non indexées par Google** ("Crawled – currently not indexed") pour des raisons distinctes selon la page : maillage interne insuffisant, quasi-duplication de gabarit (budget planners), chevauchement éditorial (ITIN vs SSN), ou rôle architectural mal défini (financial-topics).

Aucun de ces problèmes n'est bloquant pour l'AdSense ni ne touche à la homepage. Toutes les corrections proposées sont réversibles et de faible risque technique.

---

## 2. Limites méthodologiques

- **Aucune donnée GSC (impressions/clics/requêtes) ni backlinks n'a pu être récupérée via l'API Ahrefs** — le compte Ahrefs connecté renvoie systématiquement `Insufficient plan` sur tous les endpoints payants (GSC, Site Explorer, Site Audit), y compris pour cette session. Seul l'endpoint public gratuit (Domain Rating) fonctionne. Cette limite était déjà documentée lors d'un audit précédent (26/07) — non résolue depuis. **Conséquence** : les comparaisons ITIN vs SSN (section 12) et les décisions de fusion/repositionnement sont basées sur l'analyse de contenu et de structure, pas sur des données réelles de trafic/clics. Recommandation : avant toute fusion définitive, croiser avec le rapport GSC "Performance" manuellement (Claude for Chrome) pour les deux URLs ITIN.
- **Aucun accès à un navigateur headless (Puppeteer/Playwright)** dans cet environnement. Toutes les pages ont été vérifiées via `curl` (HTML servi par le serveur). Étant donné qu'Astra + Elementor Pro génèrent du HTML côté serveur (pas une SPA JS), le contenu principal vu par `curl` est représentatif de ce que Googlebot reçoit — mais un éventuel écart de rendu JS pur (ex. un widget Elementor chargé dynamiquement) n'a pas pu être vérifié visuellement.
- **La carte de maillage interne n'est PAS exhaustive sur les 74 pages du site.** Deux tentatives de crawl systématique via boucle shell ont échoué (blocage de l'environnement d'exécution sur les constructions `while read < fichier`, indépendant du réseau — confirmé par test isolé). La carte présentée en section 4 est une **carte ciblée** construite à partir de vérifications individuelles robustes (accueil, 2 hubs pays, `/start-here/`, les 5 pages cibles, et leurs articles jumeaux directs) : **les chiffres de liens entrants sont des minimums confirmés, jamais une estimation présentée comme exhaustive.**
- Le nombre de mots par page inclut le HTML complet servi (nav, footer, sidebar compris), pas seulement le corps de l'article — les chiffres sont donc une **borne haute** du contenu réellement unique.

---

## 3. État technique de chaque URL

### A. Chaîne de redirection

| URL | Statut | Détail |
|---|---|---|
| `can-foreigners-open-us-bank-account/` | 301 | → `can-foreigners-open-a-bank-account-in-the-us/` |
| `can-foreigners-open-a-bank-account-in-the-us/` | 301 | → `best-banks-newcomers-usa-2026/` |
| `best-banks-newcomers-usa-2026/` | **200** | Destination finale, page vivante, canonical self |

**Chaîne actuelle confirmée : 2 sauts.** Objectif : redirection directe en 1 saut vers `best-banks-newcomers-usa-2026/`. Non créée — en attente de validation.

### B. Les 4 tags morts

| Ancienne URL | Statut actuel | Destination proposée | Justification | Confiance |
|---|---|---|---|---|
| `/tag/rent-apartment-canada/` | 404 confirmé | `/first-apartment-canada-newcomers-2026/` | Correspondance thématique directe (guide "premier appartement" pour nouveaux arrivants) | **Élevée** |
| `/tag/how-to-rent-canada-newcomer/` | 404 confirmé | `/first-apartment-canada-newcomers-2026/` | Même famille thématique que ci-dessus, même correspondance directe | **Élevée** |
| `/tag/private-landlord-canada/` | 404 confirmé | `/rent-without-credit-canada/` | Vérifié dans le contenu réel : "private landlord" apparaît 2× dans cet article (vs 1× dans first-apartment-canada-newcomers-2026) et "guarantor" y apparaît 4× — c'est l'article qui couvre le mieux les alternatives au bail standard | **Moyenne-élevée** |
| `/tag/us-source-income/` | 404 confirmé | `/taxes-for-new-immigrants-to-the-usa-2026/` | Vérifié : "source income" mentionné dans cet article (0 mention dans l'alias `nonresident-alien-taxes-usa-guide`, qui n'est lui-même qu'une redirection). Sujet traité mais pas en profondeur — angle fiscal spécifique "revenu de source américaine" mérite peut-être sa propre sous-section à terme | **Moyenne** |

Aucune de ces 4 redirections ne pointe vers la page d'accueil — toutes vers un contenu réellement pertinent et vérifié. Aucune n'a été créée.

### C. Les 5 pages "Crawled – currently not indexed"

| URL | HTTP | Canonical | Robots meta | X-Robots-Tag | Sitemap XML |
|---|---|---|---|---|---|
| `cost-of-living-usa-2026/` | 200 | self | `index, follow` | aucun | présent |
| `itin-vs-ssn-...-guide/` | 200 | self | `index, follow` | aucun | présent |
| `canada-budget-planner-2026/` | 200 | self | `index, follow` | aucun | présent |
| `usa-budget-planner-2026/` | 200 | self | `index, follow` | aucun | présent |
| `financial-topics/` | 200 | self | `index, follow` | aucun | présent |

Aucune des 5 pages n'a de directive technique bloquante (pas de noindex, pas de X-Robots-Tag, canonical propre, présente au sitemap). **La non-indexation est donc un problème de qualité/architecture perçue par Google, pas un problème technique.**

---

## 4. Carte du maillage interne (ciblée, minimums confirmés)

| Page cible | Profondeur de clic min. confirmée | Liens entrants confirmés (min.) | Pages sources confirmées | Lien depuis un hub ? | Lien depuis la nav principale ? |
|---|---|---|---|---|---|
| `cost-of-living-usa-2026/` | 2 | 1 | `cost-of-living-canada-2026` | Non | Non |
| `itin-vs-ssn-...-guide/` | 2 | 1 | `how-to-get-itin-number-usa-2026` | Non | Non |
| `canada-budget-planner-2026/` | 2 | 3 | `newcomers-to-canada`, `cost-of-living-canada-2026`, `cost-of-living-usa-2026`, `usa-budget-planner-2026` | **Oui** (`newcomers-to-canada`) | Non |
| `usa-budget-planner-2026/` | **3** | 2 | `cost-of-living-usa-2026`, `canada-budget-planner-2026` | **Non** — asymétrie confirmée vs la version Canada | Non |
| `financial-topics/` | 2 | 3 | `newcomers-to-the-usa`, `newcomers-to-canada`, `start-here` | **Oui** (3 sources) | Non |

**Constat clé** : `financial-topics` est la mieux connectée des 5 (liée par les 2 hubs pays + start-here) — sa non-indexation n'est donc pas un problème de maillage. À l'inverse, `usa-budget-planner-2026` est la moins bien connectée (profondeur 3, aucun lien hub) — c'est le déficit de maillage le plus net et le plus simple à corriger.

---

## 5. Analyse de duplication

| Paire | Similarité (Jaccard, mots >4 lettres) | Verdict |
|---|---|---|
| `cost-of-living-usa-2026` vs `cost-of-living-canada-2026` | 25,8% | Normal pour un couple pays-jumeau, pas un risque de duplication |
| `itin-vs-ssn-...-guide` vs `how-to-get-itin-number-usa-2026` | 39,75% | Chevauchement notable — voir section 12 |
| `canada-budget-planner-2026` vs `usa-budget-planner-2026` | **48,2%** | Le plus élevé des 5 — H2 quasi identiques mot pour mot ("Where Will You Live?", "Your Situation", "Fine-Tune Your Estimates") : signature de gabarit dupliqué avec pays interchangé |
| `financial-topics` vs `newcomers-to-the-usa` | 16,2% | Faible, pas de duplication directe |
| `financial-topics` vs `newcomers-to-canada` | 17,9% | Faible |
| `financial-topics` vs `start-here` | 31,1% | Modéré — chevauchement de rôle plus que de texte (voir section 13) |

---

## 6. Analyse de cannibalisation

**ITIN vs SSN vs How to Get an ITIN Number** — le seul cas net de cannibalisation de mots-clés parmi les 5 pages :
- `how-to-get-itin-number-usa-2026` cible l'intention "comment obtenir un ITIN" (procédure), et contient déjà une section 6 "ITIN vs SSN: Key Differences".
- `itin-vs-ssn-...-guide` cible l'intention "ITIN ou SSN, lequel me faut-il" (comparaison/décision) — mais empiète sur la section 6 de l'autre article.
- Les deux sont liées depuis des points d'entrée différents (la première depuis la nav principale, la seconde uniquement depuis l'article lui-même), ce qui crée une hiérarchie de fait déséquilibrée en faveur de la première.

Aucune autre paire des 5 pages ne présente de cannibalisation de mots-clés claire (les budget planners ciblent chacun un pays distinct, cost-of-living USA/Canada de même).

---

## 7. Analyse EEAT

| Page | Auteur affiché | Lien bio réel | Citations officielles | Date de mise à jour |
|---|---|---|---|---|
| `cost-of-living-usa-2026` | Talal Eddaouahiri (schema Person, jobTitle "Founder & Financial Writer") | Lien pointe vers `/author/talal-eddaouahiri/` (archive), **pas** vers `/about-talal-eddaouahiri/` (bio réelle) | 1 seule | Modifié 23/07/2026 |
| `itin-vs-ssn-...-guide` | Idem | Idem | **11** — le meilleur score des 5 | Modifié 27/07/2026 (retouché hier) |
| `canada-budget-planner-2026` | Idem, mais pas de byline visible détectée dans le corps | Idem | **0** — faiblesse EEAT nette pour un outil financier | Modifié 23/07/2026 |
| `usa-budget-planner-2026` | Idem | Idem | 1 seule | Modifié 23/07/2026 |
| `financial-topics` | Pas de byline (normal, page-index) | — | 0 (normal, page-index) | Modifié 16/07/2026 |

**Constat transversal** (touche les 5 pages, pas spécifique à une seule) : le lien auteur pointe systématiquement vers l'archive WordPress de l'auteur plutôt que vers sa page de biographie réelle (`/about-talal-eddaouahiri/`), qui contient les vraies preuves d'expertise. C'est une amélioration EEAT simple et transversale, hors périmètre strict de cette mission mais notée ici pour référence future.

---

## 8. Recommandations par page

### 8.1 Cost of Living USA

Vérifications demandées :
- Liée depuis le hub USA (`newcomers-to-the-usa`) ? **Non**, confirmé.
- Liée depuis `/start-here/` ? **Non**, confirmé.
- Liée depuis la homepage ? **Non**, confirmé (page absente de la nav principale actuelle).
- Liée depuis des articles USA importants ? **Oui** — depuis `cost-of-living-canada-2026` (comparatif Canada vs USA).
- Accessible en 2 clics maximum ? **Oui**, via `cost-of-living-canada-2026` (profondeur 2), mais pas via un chemin USA direct.
- Contenu distinct de la version Canada ? **Oui** — 74% des mots ne se recoupent pas (Jaccard 25,8%), structures différentes (villes US vs différences provinciales CA).

**5 à 10 liens internes à ajouter :**

| # | URL source | Section/paragraphe source | Texte d'ancre recommandé | URL cible | Raison éditoriale |
|---|---|---|---|---|---|
| 1 | `newcomers-to-the-usa/` | Section "Latest USA Guides" ou nouvelle carte dédiée | "see real monthly budgets by US city" | `cost-of-living-usa-2026/` | Le hub USA n'a aucun lien vers cet article, contrairement à son équivalent Canada |
| 2 | `start-here/` | Section "Your 4 Steps in the USA" | "check what it actually costs to live there first" | `cost-of-living-usa-2026/` | Point d'entrée principal, améliore la profondeur à 1 clic |
| 3 | `best-banks-newcomers-usa-2026/` | Paragraphe sur le choix d'un compte selon le budget | "once you know your monthly budget" | `cost-of-living-usa-2026/` | Lien contextuel naturel budget → banque |
| 4 | `how-to-build-credit-in-usa-without-ssn/` | Introduction ou section sur la gestion budgétaire | "managing your monthly expenses" | `cost-of-living-usa-2026/` | Le crédit se construit en fonction du budget disponible |
| 5 | `taxes-for-new-immigrants-to-the-usa-2026/` | Section sur le revenu net disponible après impôts | "your real take-home budget" | `cost-of-living-usa-2026/` | Lien fiscalité → coût de la vie, angle naturel |
| 6 | `usa-budget-planner-2026/` (réciproque) | Introduction du simulateur | "read our full city-by-city cost breakdown" | `cost-of-living-usa-2026/` | Renforce le maillage bidirectionnel déjà existant dans l'autre sens |
| 7 | `best-itin-friendly-bank-accounts-usa/` | Section budget/frais bancaires | "compare that to typical monthly costs" | `cost-of-living-usa-2026/` | Lien contextuel budget ↔ frais bancaires |

Ancres volontairement variées (aucune répétition exacte), toutes descriptives et naturelles dans leur contexte de phrase.

### 8.2 ITIN vs SSN — voir section 12 (analyse dédiée demandée)

### 8.3 Budget Planners — voir section 11 (plan éditorial dédié demandé)

### 8.4 Financial Topics — voir section 13 (décision dédiée demandée)

---

## 9. Redirections proposées (récapitulatif, non créées)

| # | Ancienne URL | Nouvelle destination directe | Sauts actuels | Sauts après correction |
|---|---|---|---|---|
| 1 | `can-foreigners-open-us-bank-account/` | `best-banks-newcomers-usa-2026/` | 2 | 1 |
| 2 | `tag/rent-apartment-canada/` | `first-apartment-canada-newcomers-2026/` | — (404) | 1 (nouveau) |
| 3 | `tag/how-to-rent-canada-newcomer/` | `first-apartment-canada-newcomers-2026/` | — (404) | 1 (nouveau) |
| 4 | `tag/private-landlord-canada/` | `rent-without-credit-canada/` | — (404) | 1 (nouveau) |
| 5 | `tag/us-source-income/` | `taxes-for-new-immigrants-to-the-usa-2026/` | — (404) | 1 (nouveau) |

---

## 10. Liens internes proposés (récapitulatif)

Voir tableau détaillé section 8.1 (7 liens pour Cost of Living USA) et section 11 (liens spécifiques aux budget planners). Total : **7 liens** pour Cost of Living USA + **1 lien prioritaire** (`newcomers-to-the-usa` → `usa-budget-planner-2026`, symétrie avec le hub Canada) + liens contextuels proposés dans le plan éditorial ITIN (section 12).

---

## 11. Plan éditorial pour les Budget Planners

### Séparer le nécessaire de l'évitable

**Similarité techniquement nécessaire au fonctionnement du calculateur** (à conserver telle quelle) :
- Structure du simulateur : "Where Will You Live?", "Your Situation", "Fine-Tune Your Estimates" — c'est un widget interactif, sa mécanique doit être cohérente entre les deux pays pour la maintenabilité.
- Format des résultats chiffrés (tableau de sortie du calculateur).
- Disclaimer légal standard.

**Similarité éditoriale évitable** (à différencier) :
- Introduction et sections narratives autour du calculateur (actuellement trop proches en structure).
- Absence quasi totale de sources officielles côté Canada (0 citation).
- FAQ génériques non spécifiques à un pays.

### USA Budget Planner — nouvelle intention éditoriale

**Intention** : "Combien coûte réellement la vie aux USA selon l'État et la ville, avec les spécificités fiscales et administratives américaines."

**Structure H2/H3 proposée** :
- H2 Housing — loyers par État (pas seulement par ville), différences drastiques (ex. Californie vs Texas)
- H2 Utilities & Transportation — coût de la voiture quasi-obligatoire hors grandes métropoles
- H2 Healthcare — poste le plus spécifique aux USA (assurance privée, deductibles) — actuellement sous-traité
- H2 Taxes — fédéral + État (certains États sans income tax : Texas, Floride) — angle absent aujourd'hui
- H2 Credit Building — lien avec le coût du crédit (taux, dépôts de garantie liés au score)
- H3 State-level cost differences (tableau comparatif)
- FAQ propre USA (ex. "Do I need a car in the US?", "How much is health insurance really?")

**Sections à conserver** : le simulateur lui-même, la structure de résultats.
**Sections à réécrire** : introduction, section coût de la vie par ville (élargir à l'échelle État), FAQ.
**Exemples à ajouter** : 3-4 profils-types (étudiant à Boston, famille à Houston, professionnel à Seattle) avec vrais chiffres.
**Sources officielles à citer** : Census Bureau (revenu médian par État), Bureau of Labor Statistics (CPI régional), IRS (barèmes fiscaux), HUD (loyers moyens "Fair Market Rent"), healthcare.gov (primes d'assurance).

### Canada Budget Planner — nouvelle intention éditoriale

**Intention** : "Combien coûte réellement la vie au Canada selon la province, avec les spécificités d'installation (santé publique, délais de carence, TPS/TVH)."

**Structure H2/H3 proposée** :
- H2 Housing — écarts provinciaux (Ontario/BC vs Provinces atlantiques)
- H2 Telecom — un poste notoirement plus cher qu'aux USA, angle différenciant fort
- H2 Public Transportation — role plus important qu'aux USA dans les grandes villes canadiennes
- H2 Healthcare Coverage — délai de carence provincial (angle déjà traité dans `cost-of-living-canada-2026`, à réutiliser ici sans dupliquer mot pour mot)
- H2 Taxes — fédéral + provincial, TPS/TVH selon province
- H2 Newcomer Settlement Costs — dépôts de garantie, meubles, ce qui est spécifique à une première installation
- FAQ propre Canada (ex. "How long is the health care waiting period in my province?")

**Sections à conserver** : le simulateur, structure de résultats.
**Sections à réécrire** : introduction, ajouter la dimension provinciale (actuellement plus faible que la version USA en H3, 5 contre 14).
**Exemples à ajouter** : 3-4 profils-types par province (Toronto, Vancouver, Montréal, Halifax).
**Sources officielles à citer** : Statistique Canada (IPC provincial), Gouvernement du Canada (immigration/installation), Agence du revenu du Canada (barèmes), SCHL/CMHC (loyers moyens par ville).

**Liens internes à ajouter** (les deux pages) : lien réciproque renforcé, lien depuis `cost-of-living-{pays}-2026` déjà présent à conserver, lien depuis le hub USA vers `usa-budget-planner-2026` (actuellement manquant, priorité 1 du plan de maillage).

---

## 12. Décision recommandée pour ITIN vs SSN

| Critère | Option A — Conserver et différencier | Option B — Fusionner dans l'article ITIN principal | Option C — Repositionner sur intention plus précise |
|---|---|---|---|
| Avantages | Garde 2 URLs indexables si bien différenciées ; pas de perte de contenu unique (asylum seekers, DACA, Regulation E — déjà vérifié riche par ailleurs sur des articles voisins) | Élimine la cannibalisation directement ; concentre l'autorité (11 citations officielles) sur une seule URL déjà bien liée en nav | Réduit le chevauchement sans perdre l'URL ; capture une longue traîne distincte |
| Risques | Sans différenciation réelle, la cannibalisation persiste et aucune des deux ne progresse | Perte de l'URL actuelle (nécessite redirection) ; risque de diluer l'intention "comparaison" dans un article "procédure" | Demande un vrai travail de repositionnement, résultat incertain sans données de requêtes (limite Ahrefs, section 2) |
| Travail requis | Moyen — réécrire l'intro et la section comparative pour clarifier "pourquoi cet article existe en plus de l'autre" | Faible — fusionner la section unique de contenu (asylum/DACA/Regulation E) dans l'article principal, puis rediriger | Élevé — trouver un angle vraiment distinct (ex. "ITIN vs SSN pour hypothèque", "pour étudiants F1/J1") et réécrire en conséquence |
| Impact SEO estimé | Incertain sans données de clics réelles | Probable amélioration de l'autorité de la page principale, perte de l'URL secondaire | Potentiel gain sur une requête de niche, mais spéculatif |
| Besoin de redirection | Non | **Oui**, 301 vers `how-to-get-itin-number-usa-2026/` | Non (juste renommage/réécriture éventuels) |
| Destination canonique recommandée si fusion | — | `how-to-get-itin-number-usa-2026/` (déjà en nav, meilleure autorité perçue) | — |
| Impact sur liens internes existants | Aucun changement nécessaire | Le lien interne actuel (`how-to-get-itin-number-usa-2026` → `itin-vs-ssn`) devient interne à l'article après fusion, pas de lien cassé | Le lien existant reste valide, ancre à ajuster pour refléter le nouvel angle |

**Recommandation finale** : **Option B (fusion)**, sous réserve de préserver tout le contenu réellement unique identifié (asylum seekers, DACA, Regulation E, mortgages ITIN, transition ITIN→SSN) en l'intégrant dans `how-to-get-itin-number-usa-2026/` plutôt qu'en le supprimant. C'est l'option qui résout la cannibalisation avec le moins d'incertitude, sans données de clics disponibles pour arbitrer plus finement (limite documentée en section 2). Si tu obtiens les données GSC réelles par ailleurs (Claude for Chrome) et que `itin-vs-ssn` reçoit déjà un volume de clics propre non négligeable, l'Option C redevient préférable — à réévaluer avant exécution du Lot 4.

---

## 13. Décision recommandée pour Financial Topics

Vérifications demandées :
- **Contenu original** : faible — 2434 mots répartis en 6 sections de type annuaire, ratio texte-original/liens parmi les plus bas des 5 pages (66 liens sortants pour 2434 mots).
- **Utilité utilisateur** : réelle en tant que plan de site thématique, mais redondante avec l'expérience déjà offerte par les hubs pays et `start-here`.
- **Duplication avec homepage/Start Here/hubs** : pas de duplication textuelle forte (16-31% Jaccard), mais **duplication de rôle** — 3 pages "point d'entrée généraliste" coexistent (`start-here`, `financial-topics`, + les 2 hubs pays qui remplissent une fonction proche).
- **Volume de liens internes** : élevé en entrant (liée par les 2 hubs + start-here, la mieux connectée des 5) et en sortant (66).
- **Profondeur de navigation** : 2 clics, meilleure des 5.
- **Capacité à cibler une requête réelle** : faible — le titre actuel ("Guides - Educational personal finance blog...", >150 caractères) ressemble à une meta description collée dans le title, pas à une page qui cible une requête précise.
- **Risque de thin content** : réel, du fait du faible ratio contenu/liens.
- **Rôle dans l'architecture** : structurant (elle organise la découverte transversale des thèmes), mais pas actuellement différenciée d'un simple plan de site.

**Recommandation stratégique : Option B — page de navigation utile, non prioritaire dans l'index.**

Justification : la page est bien intégrée à l'architecture (meilleur maillage des 5) et sert un vrai rôle de navigation transversale, mais son contenu actuel ne justifie pas une indexation séparée tant qu'il reste au niveau d'un simple répertoire de liens. Deux voies possibles, à trancher séparément de cette mission :
1. **Statu quo assumé** : la laisser telle quelle, accepter qu'elle ne soit pas indexée (elle continue de remplir son rôle de navigation interne sans peser sur l'EEAT ni la qualité perçue du site).
2. **Enrichissement futur** (hors périmètre immédiat) : ajouter un paragraphe d'introduction substantiel et distinct par section (pas juste des liens), et retravailler le title (actuellement inadapté, à raccourcir à ~60 caractères ciblant une requête du type "personal finance guides for immigrants USA Canada").

Aucune modification (noindex, redirection) ne doit être faite dans l'immédiat — conforme à la consigne.

---

## 14. Plan d'action priorisé

| Action | URL concernée | Impact SEO | Impact utilisateur | Effort | Risque | Priorité |
|---|---|---|---|---|---|---|
| Raccourcir la chaîne de redirection à 1 saut | `can-foreigners-open-us-bank-account/` | Faible | Faible | 5 à 15 minutes | Faible | P2 |
| Créer les 4 redirections de tags | 4 URLs `tag/...` | Moyen | Moyen | 15 à 45 minutes | Faible | P1 |
| Ajouter lien hub USA → Cost of Living USA | `newcomers-to-the-usa/` | Élevé | Moyen | 5 à 15 minutes | Faible | **P0** |
| Ajouter lien hub USA → USA Budget Planner | `newcomers-to-the-usa/` | Élevé | Moyen | 5 à 15 minutes | Faible | **P0** |
| Ajouter les liens contextuels restants (Cost of Living USA) | Divers articles USA | Moyen | Moyen | 15 à 45 minutes | Faible | P1 |
| Différencier les 2 Budget Planners (réécriture ciblée + sources) | `canada-budget-planner-2026`, `usa-budget-planner-2026` | Très élevé | Élevé | 2 à 4 heures | Moyen | P1 |
| Fusionner ITIN vs SSN dans l'article principal | `itin-vs-ssn-...guide` → `how-to-get-itin-number-usa-2026` | Élevé | Moyen | 1 à 2 heures | Moyen | P2 |
| Décision Financial Topics (statu quo ou enrichissement) | `financial-topics/` | Faible à moyen | Faible | Selon option choisie | Faible | P3 |

---

## Plan d'exécution proposé, par lots

### LOT 1 — Correctifs techniques à faible risque
- **Fichiers concernés** : configuration des redirections (plugin Redirection, ou équivalent WordPress — pas de fichier de code applicatif).
- **URLs concernées** : `can-foreigners-open-us-bank-account/` (raccourcir) + les 4 tags morts (créer).
- **Changements envisagés** : 5 règles de redirection 301, aucune modification de contenu.
- **Sauvegardes nécessaires** : export de la liste actuelle des redirections avant modification (le plugin Redirection permet un export JSON/CSV natif).
- **Tests à effectuer** : statut HTTP de chaque URL corrigée (1 saut, code 200 final), absence de boucle.
- **Risques** : très faible — redirections additives, aucune suppression de règle existante.
- **Retour arrière** : suppression de la règle de redirection créée, ou ré-import de l'export de sauvegarde.

### LOT 2 — Maillage interne
- **Fichiers concernés** : contenu des articles/pages listées (édition via l'éditeur WordPress/Elementor, pas de fichier de thème).
- **URLs concernées** : `newcomers-to-the-usa/`, `start-here/`, `best-banks-newcomers-usa-2026/`, `how-to-build-credit-in-usa-without-ssn/`, `taxes-for-new-immigrants-to-the-usa-2026/`, `usa-budget-planner-2026/`, `best-itin-friendly-bank-accounts-usa/`.
- **Changements envisagés** : ajout de 7-8 liens contextuels (ancres proposées section 8.1), aucune suppression de texte existant.
- **Sauvegardes nécessaires** : révision WordPress native (chaque page a un historique de révisions) — vérifier qu'elle est activée avant modification.
- **Tests à effectuer** : chaque lien ajouté renvoie 200, pas de lien cassé, rendu visuel de la section modifiée (desktop + mobile).
- **Risques** : faible — ajout de liens uniquement, pas de suppression.
- **Retour arrière** : restauration de la révision WordPress précédente de la page modifiée.

### LOT 3 — Différenciation des Budget Planners
- **Fichiers concernés** : contenu des 2 pages (éditeur WordPress/Elementor).
- **URLs concernées** : `canada-budget-planner-2026/`, `usa-budget-planner-2026/`.
- **Changements envisagés** : réécriture des sections narratives (pas le simulateur lui-même), ajout de sources officielles, FAQ propres à chaque pays, exemples chiffrés (voir section 11).
- **Sauvegardes nécessaires** : révision WordPress + export du contenu actuel en Markdown/texte avant réécriture (traçabilité éditoriale, cohérent avec la convention "un fix vérifié à la fois" déjà en usage sur ce projet).
- **Tests à effectuer** : le simulateur fonctionne toujours après édition (aucune modification du widget lui-même), rendu desktop/mobile, absence d'erreur PHP/Elementor.
- **Risques** : moyen — c'est la réécriture de contenu la plus substantielle du lot, risque de casser accidentellement le shortcode/widget du calculateur si l'édition touche la zone du widget.
- **Retour arrière** : restauration de la révision WordPress précédente.

### LOT 4 — Résolution du chevauchement ITIN
- **Fichiers concernés** : contenu de `how-to-get-itin-number-usa-2026/` (fusion), suppression/redirection de `itin-vs-ssn-...-guide/`.
- **URLs concernées** : les deux URLs ITIN.
- **Changements envisagés** : intégrer le contenu unique (asylum seekers, DACA, Regulation E, mortgages ITIN, transition ITIN→SSN) dans l'article principal, puis créer une redirection 301 de l'URL fusionnée vers l'article principal.
- **Sauvegardes nécessaires** : export complet du contenu de `itin-vs-ssn-...-guide` avant toute suppression/redirection (pour ne rien perdre du contenu unique identifié).
- **Tests à effectuer** : la redirection ne boucle pas, le contenu fusionné est bien présent et cohérent dans l'article principal, aucun lien interne existant ne pointe vers une URL morte après la redirection.
- **Risques** : moyen — c'est le changement le plus structurant (fusion + suppression d'URL), et sans données de clics réelles (limite section 2) la décision reste basée sur l'analyse de contenu, pas sur la performance mesurée.
- **Retour arrière** : republier `itin-vs-ssn-...-guide` depuis la sauvegarde, retirer la redirection.

### LOT 5 — Décision sur Financial Topics
- **Fichiers concernés** : aucun changement structurel prévu dans l'immédiat (statu quo recommandé).
- **URLs concernées** : `financial-topics/`.
- **Changements envisagés** : aucun dans l'immédiat, sauf si tu choisis l'enrichissement (auquel cas : ajout de paragraphes d'introduction par section + réécriture du title).
- **Sauvegardes nécessaires** : révision WordPress si enrichissement choisi.
- **Tests à effectuer** : si enrichissement, vérifier que le title reste sous ~60 caractères et que le rendu des 6 sections reste intact.
- **Risques** : faible.
- **Retour arrière** : restauration de révision si enrichissement effectué.

---

*Rapport généré en lecture seule. Aucune modification WordPress, base de données, redirection, canonical, robots, cache ou sitemap n'a été effectuée.*
