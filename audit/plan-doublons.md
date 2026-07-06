# Plan ÉTAPE 2 — Doublons d'articles (PLANIFICATION SEULE, lecture seule)

**Statut : AUCUNE action exécutée. Ce document est un plan à valider groupe par groupe. Rien n'est supprimé, redirigé, ou fusionné.**

Exécution probable : par l'utilisateur dans wp-admin, pas via l'API — ce document sert à décider QUOI faire, pas à le faire.

## Méthode et limites (honnêteté avant les chiffres)

Données collectées via `scripts/scan_duplicate_inventory.py` (lecture seule) : pour chacun des 54 articles publiés — nombre de mots, liens internes ENTRANTS (combien d'autres articles du site pointent vers lui) et SORTANTS, date de publication, catégories.

**Ce que je n'ai PAS** : données Google Search Console / Analytics (trafic réel, positionnement réel, pages indexées). Les critères ci-dessous sont des **proxies objectifs mesurés sur le site lui-même**, pas une confirmation de trafic réel. Le nombre de liens entrants internes est le signal le plus fiable dont je dispose (un article que le reste du site cite déjà a plus de poids SEO interne accumulé) — mais ce n'est pas une garantie de meilleur classement Google.

**Ce que je n'ai PAS non plus vérifié** : une comparaison fine du CONTENU pour repérer un paragraphe unique dans un doublon qui n'existerait pas dans le canonique proposé. Je n'ai que les métadonnées (nombre de mots, liens). Avant toute suppression réelle, chaque doublon retenu pour suppression doit être relu intégralement (pas juste comparé par le nombre de mots) — signalé explicitement groupe par groupe ci-dessous.

---

## GROUPE 1 — "Build Credit in Canada from Zero" (doublons de slug confirmés, `-2`/`-4`)

| ID | Slug | Mots | Liens entrants | Liens sortants | Date | Catégorie |
|---|---|---|---|---|---|---|
| 48351 | `.../-2` | 6672 | 0 | 8 | 2026-06-29 | **Newcomers to the USA** ⚠️ mal catégorisé |
| 48398 | `.../-4` | 5895 | 0 | 1 | 2026-06-30 | Newcomers to Canada (correct) |

**Point d'attention majeur** : ni "-1" (slug sans suffixe) ni "-3" n'apparaissent parmi les 54 articles PUBLIÉS — WordPress ne saute jamais un numéro de suffixe sans raison, donc un original et/ou un "-3" existent probablement en corbeille ou brouillon, invisibles à mon scan (qui ne regarde que `status=publish`). **À vérifier dans wp-admin avant toute décision finale** — il pourrait exister une version encore plus ancienne/différente.

**Canonique proposé : 48398 (`-4`)** — critère : catégorisation correcte (Canada), malgré moins de mots.
**Alternative à considérer : 48351 (`-2`)** — plus de mots (6672 vs 5895), mais catégorie fausse (à corriger de toute façon si gardé).
**Aucun signal de liens entrants pour départager** (0 vs 0 — aucun autre article du site ne cite ni l'un ni l'autre actuellement).

- **48351 est l'article "Canada mal catégorisé USA" que tu avais en tête** (probablement) — confirmé objectivement : titre "...Build Credit In Canada..." classé "Newcomers to the USA".
- Suppression proposée : 48351 **OU** 48398 (selon ton choix du canonique) → redirection 301 vers l'autre.
- **Contenu unique non vérifié** — à relire intégralement avant suppression.

---

## GROUPE 2 — "Meilleures banques / comptes bancaires pour nouveaux arrivants au Canada" (cluster de 4, pas un simple doublon de slug)

| ID | Slug | Mots | Liens entrants | Liens sortants | Date | Catégorie |
|---|---|---|---|---|---|---|
| **1620** | `best-banks-newcomers-canada-2026` | 6237 | **27** | 20 | 2026-03-05 (le plus ancien) | Newcomers to Canada |
| 47377 | `best-bank-accounts-newcomers-canada-2026` | 8978 (le plus complet) | 3 | 3 | 2026-06-22 | Newcomers to Canada |
| 48135 | `best-banks-for-canadian-newcomers-international-students...` | 5627 | 0 | 1 | 2026-06-27 | Newcomers to Canada |
| 48343 | `best-bank-account-for-newcomers-to-canada...` | 6681 | 1 | 9 | 2026-06-29 | **Newcomers to the USA** ⚠️ mal catégorisé |

**Canonique proposé : 1620** — critère : **27 liens internes entrants, de très loin le signal le plus fort de tout l'inventaire** (le 2e plus haut score de tout le site est 19). C'est l'article que le reste du site cite déjà massivement comme référence — un signal de poids SEO interne difficile à ignorer, même si ce n'est pas le plus long.

**Nuance importante à trancher par toi, pas par moi** : 48135 cible spécifiquement les "international students" — c'est peut-être une intention de recherche réellement différente ("banques pour étudiants internationaux" vs "banques pour nouveaux arrivants" en général), pas un pur doublon. À confirmer avant de le mettre dans le même panier.

- **48343 est le 2e candidat "Canada mal catégorisé USA"** — confirmé objectivement.
- Doublons candidats à supprimer : 47377, 48343, et 48135 (si confirmé même intention) → 301 vers 1620.
- **Contenu unique non vérifié** sur les 3 — à relire avant suppression, en particulier 47377 qui est le PLUS LONG (8978 mots) et pourrait contenir des informations absentes de 1620.

---

## GROUPE 3 — "Comptes d'épargne à intérêt élevé (HISA) pour nouveaux arrivants au Canada"

| ID | Slug | Mots | Liens entrants | Liens sortants | Date | Catégorie |
|---|---|---|---|---|---|---|
| 48384 | `best-high-interest-savings-accounts-for-international-students-in-canada-complete-guide-for-canada-i` ⚠️ **slug tronqué** | 5929 | 0 | 0 | 2026-06-30 | Newcomers to Canada |
| 47851 | `high-interest-savings-newcomers-canada-2026` | 4240 | 0 | 1 | 2026-06-23 | Newcomers to Canada |

**Le slug tronqué que tu avais repéré** : confirmé, `...complete-guide-for-canada-i` — coupé en plein mot (le titre complet dit "...Complete Guide for Canada – International Students Immigrants (2026)", donc le slug voulait probablement continuer en "...canada-immigrants" ou similaire, tronqué par la limite de longueur de WordPress). Un problème d'URL cassée indépendamment même de la question du doublon.

**Canonique proposé : 47851** — critère : slug propre (pas cassé), malgré moins de mots. Le slug tronqué de 48384 est en lui-même un problème SEO/UX à corriger, qu'il soit ou non retenu.
**Aucun signal de liens entrants pour départager** (0 vs 0).

Articles liés mais **PROBABLEMENT PAS des doublons** (portée différente, à ne pas mélanger sans confirmation) :
- 1643 `best-high-yield-savings-accounts-2026` — couvre USA **ET** Canada, mot-clé "high-yield" (pas "high-interest"), 7 liens entrants — probablement un article distinct à portée plus large.
- 46669 `best-high-yield-savings-accounts-newcomers-usa` — USA uniquement, marché différent.

- Doublon candidat à supprimer : 48384 → 301 vers 47851.
- **Contenu unique non vérifié** — à relire avant suppression.

---

## GROUPES SUPPLÉMENTAIRES TROUVÉS (pas dans ta liste initiale — signalés pour être complet, à toi de décider s'ils entrent dans cette étape)

### GROUPE 4 — "Coût de la vie au Canada" (doublon probable, même marché, même sujet)

| ID | Slug | Mots | Liens entrants | Liens sortants | Date |
|---|---|---|---|---|---|
| 7164 | `cost-of-living-canada-2026` | 6584 | 8 | 12 | 2026-03-25 |
| 47087 | `cost-of-living-in-canada-for-new-immigrants-2026-guide` | 3947 | 0 | 3 | 2026-06-18 |

**Canonique proposé : 7164** — critère : 8 liens entrants vs 0, plus ancien (plus de temps pour être indexé). Doublon candidat : 47087 → 301 vers 7164.

### GROUPE 5 — "Construire son crédit aux USA" (doublon probable, même marché, même sujet)

| ID | Slug | Mots | Liens entrants | Liens sortants | Date |
|---|---|---|---|---|---|
| 1477 | `how-to-build-your-credit-score-in-the-usa` | 3636 | **19** | 10 | 2026-02-17 (le plus ancien) |
| 47152 | `how-to-build-credit-in-usa-without-ssn` | 6809 | 10 | 6 | 2026-06-22 |

**Nuance** : 47152 a un angle légèrement différent ("without SSN" — sans numéro de sécurité sociale), peut-être une intention de recherche distincte, pas un pur doublon. À confirmer.
**Canonique proposé si doublon confirmé : 1477** — critère : 19 liens entrants (2e plus haut score du site), plus ancien.

### Page à examiner séparément (ni doublon net, ni claire à classer)
- 48236 `how-to-build-credit-score-as-a-new-immigrant-in-the-usa-or-canada-2026` — titre à la casse étrange ("How To Build..."), **0 lien entrant, 0 lien sortant** (page orpheline, isolée du reste du site), couvre USA **et** Canada à la fois — chevauche potentiellement les Groupes 1 ET 5. À examiner à part, pas encore rattaché à un groupe précis.

---

## Récapitulatif — rien exécuté, en attente de ta validation groupe par groupe

| Groupe | Canonique proposé | Doublons candidats | Confiance |
|---|---|---|---|
| 1. Build Credit Canada | 48398 (à confirmer vs 48351) | 48351 ou 48398 | Moyenne — 0 lien entrant des deux côtés, "-1"/"-3" manquants à vérifier |
| 2. Banques Canada (cluster de 4) | 1620 | 47377, 48343, (48135 ?) | Haute pour 1620 (27 liens entrants) — nuance sur 48135 |
| 3. HISA Canada | 47851 | 48384 | Moyenne — slug cassé de 48384 est le signal le plus clair |
| 4. Coût de la vie Canada | 7164 | 47087 | Haute (8 liens entrants) |
| 5. Crédit USA | 1477 | 47152 (si confirmé même intention) | Moyenne — angle "without SSN" à confirmer |

**Prochaine étape** : tu valides groupe par groupe (ou tu ajustes/rejettes). Pour chaque groupe validé, avant toute suppression réelle : relecture complète du contenu du doublon (pas juste les métadonnées) pour repérer du contenu unique à récupérer, exécution dans wp-admin par toi (redirection 301 + suppression), pas via l'API.
