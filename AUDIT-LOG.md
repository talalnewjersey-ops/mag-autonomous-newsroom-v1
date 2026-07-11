# AUDIT-LOG.md — Journal des articles traités

Ce fichier est la **mémoire** du chantier. Claude Code le lit au démarrage de chaque session
et le met à jour après chaque article (Phase 6). Il donne la continuité que le terminal n'a
pas nativement.

Format par article : ID, slug, statut, date de traitement, trouvailles principales, décisions,
`[À VÉRIFIER]` résolus/restants.

---

## DÉCISIONS DE JURISPRUDENCE (valables pour TOUS les articles)

Ces décisions ont déjà été tranchées sur le prototype. Ne pas les re-débattre — les appliquer.

- **Withholding tax non-résident** : les intérêts ordinaires versés à un non-résident sans
  lien de dépendance sont GÉNÉRALEMENT EXEMPTÉS de retenue (Partie XIII). Le 25 % s'applique
  aux dividendes/pensions/loyers, PAS aux intérêts d'épargne ordinaires. Source : canada.ca
  "Non-residents of Canada". → Si un article affirme "25% sur les intérêts", c'est FAUX.
- **TFSA / limite de cotisation** : 7 000 $ est valable pour 2024–2026 (table ARC). Garder le
  chiffre, libeller "2024–2026 limit" (pas "2024 limit").
- **Basic personal amount** : aucun montant 2026 publié à ce jour ; la valeur ARC disponible
  est celle de 2025. → Traiter en PRINCIPE sans chiffre ("voir l'ARC pour le seuil courant"),
  ne pas afficher un montant 2025 sur un article 2026.
- **T5 slip** : seuil de 50 $ vérifié correct (ARC). Garder + lien.
- **CDIC** : 100 000 $ par catégorie/institution, vérifié correct. Garder + lien cdic.ca.
- **FSRA (Ontario)** : 250 000 $ pour dépôts non enregistrés des credit unions ontariennes,
  vérifié correct. Garder + lien fsrao.ca.
- **DICO** : dissous en 2019, fusionné dans la FSRA. Tout "DICO" dans un article = erreur à
  corriger en FSRA.
- **Éligibilité TFSA/FHSA des résidents temporaires / étudiants** : dépend du statut de
  RÉSIDENT FISCAL (déterminé individuellement, pas du type de permis). Ne JAMAIS affirmer
  catégoriquement qu'un étudiant "qualifie" ou que "les droits s'accumulent depuis 18 ans".
  Formuler en principe prudent + renvoi ARC/conseiller.
- **NAS commençant par 9** : les résidents temporaires reçoivent un NAS commençant par 9, avec
  date d'expiration liée au document d'immigration, à mettre à jour auprès de Service Canada.
  Vérifié, sourçable (EDSC canada.ca). Peut être écrit.
- **Nova Credit** : service B2B centré USA (FCRA), disponibilité canadienne non confirmée.
  → Ne pas nommer ; mentionner en principe ("certains services traduisent l'historique de
  crédit international...") si pertinent.
- **Âge de majorité (contrat de crédit)** : provincial, 18 dans la plupart, 19 dans certaines.
  → Écrire en principe sans lister nommément les provinces.
- **Images gabarit "taxes"** : jeu d'images fiscales (alt/légende "taxes options/checklist/
  process") plaqué sur des articles non fiscaux à travers TOUT le site. Retrait pur partout.
- **Tableau pondération score "35/30/15/10/10 %"** : suspect (probablement FICO US, pas
  forcément valide pour Equifax/TransUnion CANADA). À VÉRIFIER contre les bureaux canadiens
  partout où il apparaît. Repéré dans 47510, probablement ailleurs. NON ENCORE TRANCHÉ.

### Slugs morts déjà traités par 301 globale (ne pas re-signaler comme 404)
- `/build-credit-canada-newcomer/` → 301 vers 47510 (règle #81)
- `/permanent-residency-canada-how-to-apply/` → redirige vers /moving-to-canada-checklist-2026/
- Les 5 autres slugs Fusion (`healthcare-newcomers-canada-guide`, `itin-number-usa-immigrants`,
  `wise-vs-remitly-vs-ofx`, `cheapest-send-money-canada-abroad`, `banking-newcomers-canada`)
  → confirmés absents du corps des articles ; déjà gérés côté menu/homepage.

### Redirections dangereuses supprimées (ne pas recréer)
- Anciennes règles à `permission`/boucle retirées. Ne jamais recréer une règle dont la source
  = le propre slug d'un article publié actif (crée une boucle).

---

## ARTICLES TRAITÉS

### ✅ 47510 — building-credit-canada-newcomers-2026 (CANONIQUE crédit Canada)
- **Statut** : enrichi, live. **PARTIELLEMENT traité.**
- Reçu par fusion depuis 48351 : sections "Eligibility by Immigration Status" (NAS-9 sourcé
  EDSC, âge de majorité en principe, reporting bureaux reformulé + source FCAC, politiques
  bancaires en principe) et "Authorized User Arrangements". Puis 3 intégrations
  supplémentaires : cosignataire (principe, prudence), prêt auto (concept sans chiffre),
  Nova Credit (principe sans le nommer).
- **⚠️ RESTE À FAIRE (Bloc 5)** : le CONTENU PRÉEXISTANT de 47510 n'a JAMAIS été scanné
  intégralement. En particulier le tableau de pondération "35/30/15/10/10 %" à vérifier
  contre les bureaux canadiens. 47510 doit repasser un scan exhaustif complet comme les
  autres. **NE PAS le considérer comme propre.**

### ✅ 48384 — high-interest-savings-international-students-canada (niche étudiants)
- **Statut** : recentré, live (redirection #77 levée). **TRAITÉ (5 passes de scan).**
- Retiré : bloc banques complet (×2 sections + Quick Answer + FAQ + "Top Accounts Compared"),
  3 images gabarit "taxes", stats World Bank/Ratehub non sourcées, taux non sourcés, délais
  non sourcés, "25% withholding" faux corrigé, DICO→FSRA, exemples nommés Priya/Carlos
  anonymisés en Scenarios 1 & 2, stat "1M étudiants" (fausse à la vérif IRCC) retirée.
- Conservé + sourcé : T5 50$, TFSA 7000$ (2024–2026), CDIC 100k$, FSRA 250k$, NAS-9.
- Crosslink bidirectionnel avec 47851 en place.
- Longueur : 46 222 → 32 037 caractères.

### ✅ 48351 — build-credit...-2026-2 (DOUBLON de 47510)
- **Statut** : en CORBEILLE. **TRAITÉ / clos.**
- Contenu unique fusionné dans 47510 (voir ci-dessus). Confirmé vidé de tout contenu unique
  après re-scan.
- 301 créée : 48351 → 47510 (règle #80), vérifiée no-store, un seul saut.
- #71 (variante -4) re-pointée directement vers 47510 (évite chaîne à 2 sauts).
- ILJ vérifié : aucun lien vivant vers 48351 (auto-guérison).

---

## À TRAITER (file d'attente)
- **47510** — RE-SCAN COMPLET du contenu préexistant (priorité : tableau 35/30/15/10/10 %).
- **47851** — high-interest-savings-newcomers-canada (grand public) : crosslink ajouté, mais
  contenu non scanné intégralement.
- **1643** — savings combiné USA+Canada (le plus ancien) : chevauchement probable avec 46669
  (USA) et 47851 (Canada) qui l'ont splitté. Décider : garder / fusionner / rediriger.
- **48236** — build credit score newcomer USA/Canada : contenait le lien mort déjà neutralisé.
- **Tous les autres articles publiés** (~44) non encore audités.

## NOTES TRANSVERSALES (à traiter en passes dédiées, pas article par article)
- **Yoast** : bannière "Finish your first-time configuration" — vérifier ce que couvre
  réellement la config avant d'auditer les meta descriptions (Bloc 2).
- **Extraits (post_excerpt)** : plusieurs contiennent "No affiliate opportunities detected",
  "add mentions", "Quick Answer", "⚠️ Disclaimer" — visibles sur les pages catégories (Bloc 2).
- **Thème** : footers empilés (retirer Astra + "Powered by Astra"), menu rendu 2× (plugin
  "Astra Header Fix" inactif préparé mais jamais activé — lire son code avant), lien eBook
  /?page_id=46505, "Privacy & Cookie Policy" → #, grammaire newsletter (Bloc 3).
- **Images gabarit "taxes"** : balayage systématique sur tout le site.

---

## ÉTAT MOTEUR DE PRODUCTION (infra NEXUS-14, distinct du contenu ci-dessus)

### 2026-07-10 — Session : résolution du blocage WordPress + validation Sprint 9 ET Sprint 10

- **Cause racine du blocage identifiée** : ce n'était PAS (ou plus) le WAF Hostinger hCDN
  suspecté précédemment. Le secret GitHub Actions `WORDPRESS_APP_PASSWORD` était périmé
  (rotation manuelle du 2026-07-01 qui a introduit une valeur invalide). Confirmé par
  `wp_diagnostic.yml` × 3 runs identiques : `401 rest_not_logged_in` / `rest_cannot_create`
  avec réponse JSON propre de WordPress (pas de page de challenge HTML), preuve que la
  requête passait le WAF mais échouait sur l'auth elle-même.
- **Fix appliqué** : les 3 secrets `WORDPRESS_APP_PASSWORD`, `WORDPRESS_USERNAME`,
  `WORDPRESS_URL` resynchronisés depuis le `.env` local valide (celui qui authentifie
  correctement en local via `scripts/list_wp_drafts.py`). Noms de secrets confirmés
  cohérents avec ce qu'attendent `wp_diagnostic.yml` et `control_publish_invariant.yml`.
- **Vérification post-fix** : `wp_diagnostic.yml` → `200/200/201`, plus aucune erreur.
- **Sprint 9 (invariant de publication) re-prouvé en réel** via
  `control_publish_invariant.yml` (run `29128544472`) :
  - ANGLE 1 PROVEN — un draft QA-FAILED (post WP réel `post_id=48616`) reste
    `status=candidate`, jamais publié après reconcile.
  - ANGLE 2 PROVEN — un second reconcile sur ce même draft ne le promeut jamais
    (`status=candidate post_id=None`).
  - Le draft `[QA-FAILED]` `post_id=48616` reste sur WordPress pour inspection.
- **Bug distinct découvert puis résolu** via `control_qa_hallucination.yml`
  (run initial `29128628639`, sans rapport avec WordPress — ce workflow ne touche pas
  ses secrets) :
  - ASSERTION 1 PROVEN dès le départ — article avec 6 stats non sourcées →
    `hallucination_penalty=40`, `status=FAIL` (90-40=50 < 85). Détection OK.
  - ASSERTION 2 ÉCHOUÉE initialement — `unsourced_stat_count=5` au lieu de 0 sur un
    article où chaque stat était suivie d'un lien `.gov` générique.
  - **Diagnostic (TEMPS 1)** : PAS un bug de détection — `tests/test_sprint10_anti_
    hallucination.py` prouvait déjà que le chemin "vraie verticale" fonctionne. Cause
    réelle : le workflow appelait `agent_05_fact_checker` sans `--market`/`--category`,
    donc `resolve_gate_vertical("", "")` retombait sur `"us_default"`, qui n'a AUCUNE
    entrée dans `agents/_vertical_facts.py` — `covering_fact()` ne peut alors jamais
    matcher la moindre stat, quelle que soit la qualité du sourcing (LEVIER C : un lien
    `.gov` générique à côté d'un chiffre non engravé reste volontairement non couvert,
    voir incident réel run `28731153809`).
  - **Fix (TEMPS 2, PR #65, mergée `b5c8f21`)** : `run_case()` route maintenant vers
    `us_credit` (`--market USA --category credit`) ; le fixture "good" reconstruit à
    partir de 5 vrais faits `STABLE` engravés (`agents/_vertical_facts.py`), valeur +
    `source_url` exacts. Ajout d'un `logger.warning` dans `agent_05_fact_checker.py`
    (`warn_if_us_default`) quand la verticale résolue est `us_default`, pour que ce cas
    ne soit plus jamais silencieux en production. 4 nouveaux tests unitaires.
  - **Re-vérifié en CI réelle sur la branche de la PR avant merge** (run `29129636783`) :
    ASSERTION 1 PROVEN (`unsourced=6, status=FAIL, penalty=40`) ET ASSERTION 2 PROVEN
    (`unsourced=0, status=PASS, penalty=0`) — **Sprint 10 (anti-hallucination) prouvé
    en réel**, en plus du Sprint 9 (invariant de publication) déjà prouvé plus haut.
  - **Scan de production associé** : les 26 topics `candidate` de `data/topic_registry.json`
    ont été vérifiés contre `resolve_gate_vertical` — **aucun ne tombe sur `us_default`**
    actuellement (10 `canada_newcomer`, 4 `us_credit`, 3 `us_transfers`, 2 chacun
    `us_auto`/`us_banking`/`us_housing`, 1 chacun `us_health`/`us_mortgage`/`us_students`).
    Risque latent identifié pour le futur : la catégorie brute `"assurance"` (sans
    suffixe `auto`/`sante`) n'est PAS une clé de `CATEGORY_TO_VERTICAL` — inoffensif
    aujourd'hui car son seul porteur (`ca-health-mutuelle-new-immigrants`) est marché
    Canada, mais un futur topic US avec cette catégorie tomberait sur `us_default`
    (désormais visible via le warning ci-dessus au lieu d'être silencieux).
- **Crons** : **toujours désactivés**. Sprint 9 ET Sprint 10 sont maintenant prouvés en
  réel (WordPress + anti-hallucination) — la réactivation reste une décision à prendre
  ensemble, pas encore faite à ce stade de la session.

### 2026-07-10/11 — Session (suite) : redémarrage étagé — marker leak, diagnostic QA, score réel 84.0 → 95.5

Méthode demandée par l'utilisateur : ÉTAPE 1 (fix rapide si simple) → ÉTAPE 2 (1 run de
production réel, 1 article, mode draft) → ÉTAPE 3 (réactivation crons SI l'article est propre).

- **ÉTAPE 1 — PR #66 (mergée `0d6decb`)** : fix `test_no_internal_marker_leak.py` (2/8 tests
  en échec, fichier non suivi jusque-là). `agent_04_article_writer.py` construisait la ligne
  de fin avec `**Tier**: OPPORTUNITY | NEXUS-14 V5.0` — marqueurs internes fuités dans le HTML
  publié. Fix en une ligne : `f"> **Last Updated**: {_updated}"` seul. 8/8 tests passent.
- **ÉTAPE 2 — run de production réel, 1 article, mode draft** (`production_v2.yml` run
  `29129933048`, `mode=batch_1 max_articles=1`) : GATE C a créé un vrai draft WordPress
  (`post_id=48624`, sujet "car insurance for foreign drivers and international students" —
  même sujet que le fix #64) mais **GATE QA a bloqué** (`overall_score=84.0 < 85`, titre
  auto-tagué `[QA-FAILED]`, jamais publié — comportement correct de l'invariant Sprint 9).
  - Image vérifiée visuellement (téléchargée + inspectée) : on-topic, confirme le fix #64 en
    conditions réelles.
  - Contenu réel scanné via l'API WP : **zéro marqueur interne** (Tier/NEXUS-14/version) —
    confirme le fix #66 en conditions réelles.
  - Score QA (84.0) sous la barre de 95 fixée par l'utilisateur → **crons non réactivés**,
    diagnostic du score QA lancé à la place.
- **Diagnostic du score QA (`overall = seo×0.4 + eeat×0.4 + content×0.2`)** — décomposé
  critère par critère sur le draft réel 48624, en distinguant à chaque fois : bug de scoreur
  (case 2, fixable) vs décision structurelle/éditoriale (case 3) :
  - `trust_score` plafonné à 90/100 au lieu de 100 : `has_update_date` lu par `_audit_eeat`
    mais **jamais écrit nulle part** dans tout `agent_12_quality_assurance.py` — bug pur.
  - `question_count` FAQ toujours à 0 malgré 10 vraies questions : le lookahead de fin de
    section `(?=## |$)` matchait à l'intérieur même d'un titre `### ` (H3) — `"##"` est une
    sous-chaîne de `"###"`. Bug pur, aucun impact sur le score (jamais branché sur un gate),
    mais rapport QA faux.
  - `content_check.score` plafonné à 60/100 : les seuils `>=5000`/`>=7000` mots étaient fixes,
    alors que `agent_04` plafonne CHAQUE tier à ≤4200w (PILLAR) ou ≤4000w (STANDARD/
    OPPORTUNITY/GOLD) — ces 40 points étaient mathématiquement impossibles pour tout article
    produit par ce pipeline, exactement le même bug déjà corrigé côté score SEO le
    2026-07-06 (`_TIER_TARGET_WORDS`) mais jamais répliqué ici. Bug de cohérence, fixable.
  - `experience_score` plafonné à 30/100 : les études de cas (principal vecteur de signaux
    "Experience") ont été **volontairement supprimées sur tout le site** au Sprint 8
    (anti-fabrication — personas/chiffres inventés, vrai risque YMYL/AdSense),
    `case_studies=""` inconditionnel. Décision structurelle, PAS un bug — nécessite un
    arbitrage produit, pas un fix de code.
- **PR #67 (mergée `73af639`)** : fix `has_update_date` + regex FAQ + `content_check`
  tier-relatif (réutilise `_TIER_TARGET_WORDS`/`_WORD_COUNT_TOLERANCE` déjà utilisés par le
  score SEO). Re-scoré le draft 48624 EN RÉEL (contexte CLI répliqué exactement depuis les
  fichiers réels du run : `article_metadata.json`, `article_outline.json`,
  `wordpress_report.json`), sans régénération : **84.0 → 93.0**.
- **Levier "b" — PR #68 (mergée `cf3c089`)** : (1) `experience_patterns` reconnaît un
  vocabulaire de vécu déjà VRAI et déjà présent dans la bio auteur déterministe
  (`_AUTHOR_BIO_MD`) — "firsthand experience", "built his own ... from scratch" — bio
  elle-même non modifiée, seulement reconnue. (2) Nouveau paragraphe déterministe liant les
  pages méthodologie déjà publiées du site (`fact-checking-process`, `how-we-test`) — URL
  récupérée EN DIRECT via `agents/_real_internal_links.py::fetch_methodology_links()` (même
  contrat fail-soft/jamais-de-lien-en-dur que `fetch_real_posts`, POINT 4 2026-07-05).
  Re-scoré en réel : **93.0 → 94.0**.
  - ⚠️ Latence notée : le fetch live des pages méthodologie a pris 9.0-9.3s lors des tests,
    proche du timeout par défaut de 10s (même constat que la latence Hostinger observée sur
    `wp_diagnostic.yml`). Fail-soft (jamais de crash, jamais de lien inventé), mais le lien
    pourrait être absent sur une fraction non négligeable des runs réels. Non bloquant,
    signalé pour une session future.
- **Levier "a" — PR #70 (mergée `42d4395`)** : réintroduction des études de cas sous forme
  stricte "Illustrative Scenarios" (format déjà validé en réel sur l'article 48384 pendant
  l'audit de contenu) — **décision Sprint 8 MAINTENUE, pas inversée**. Garde-fou anti-
  fabrication gravé dans le code (`agents/_scenario_guard.py`, nouveau) :
  - rejette tout scénario contenant un **prénom inventé** (liste diversifiée volontairement —
    l'incident réel utilisait "Priya"/"Carlos", une liste anglo-only l'aurait raté) ;
  - rejette tout scénario contenant un **chiffre non couvert** — réutilise EXACTEMENT le
    prédicat LEVIER C d'agent_05 (`agents/_fact_coverage.py::classify_claims`), pas un
    mécanisme parallèle ;
  - test verrou explicite (`test_the_exact_reported_violation_shape_is_rejected`) : un
    scénario façon "Sarah saved $3,240" DOIT être rejeté — si ce test passe un jour avec
    `is_clean=True`, la décision Sprint 8 a régressé silencieusement. Démontré en direct
    (hors pytest) avant le merge : `is_clean=False`, `reasons=["invented name(s): ['Sarah']",
    "1 uncovered numeric claim(s)"]`, bloc publié = `''`.
  - **Découverte en testant, pas devinée** : une première version verbeuse (2 scénarios,
    ~150 mots) a fait RÉGRESSER le score — l'article 48624 était déjà à 4304/4000 mots
    (+7.6%) sur son tier OPPORTUNITY, et l'ajout dépassait la tolérance ±10% du levier "b"
    (coût : 15 pts SEO + 40 pts content_check, perte nette malgré le gain EEAT). Corrigé :
    1 seul scénario court (40-70 mots, `max_tokens=200`), verrouillé par
    `test_scenario_call_is_short_deliberately_capped`.
  - Aucun changement de scoreur nécessaire : `experience_patterns` matchait déjà
    `scenario`/`case stud(y|ies)` avant ce lot.
  - Re-scoré en réel (contexte CLI répliqué, guard réel, sans régénération) : **94.0 → 95.5**
    — **franchit la barre des 95** fixée par l'utilisateur.
- **Trajectoire complète du score QA sur le draft témoin 48624** : 84.0 (run réel initial) →
  93.0 (PR #67) → 94.0 (PR #68, levier b) → **95.5 (PR #70, levier a)**.
- **PR #69** : ouverte comme PR empilée sur la branche de #68, auto-fermée par GitHub quand
  cette branche a été supprimée au merge de #68 (comportement normal de GitHub, aucune perte
  — la branche `feat/lever-a-illustrative-scenarios` était intacte). Rouverte proprement
  contre `main` sous le numéro **#70**, CI verte, mergée.
- **Crons** : **toujours désactivés**. Le score QA du draft témoin dépasse maintenant la
  barre des 95 (avec le levier "a" honnête, sans réactiver la fabrication) — la décision de
  réactivation reste à prendre ensemble, pas encore actée à la fin de cette session. Prochaine
  étape logique : relancer un run de production réel (ÉTAPE 2 refaite) pour confirmer que le
  gain se reproduit sur un article fraîchement généré (pas seulement re-scoré), avant
  réactivation.

### 2026-07-11 — Session (suite) : PR #71 à #79, 5 runs témoins, seuil aligné sur 95, mode draft-only réel

**PR #64 à #79 — une ligne chacune (statut réel vérifié via `gh pr view`, pas supposé) :**
- **#64** (`07e08cc`, mergée) — images off-topic : sujet réel injecté, code LLM mort retiré.
- **#65** (`b5c8f21`, mergée) — `control_qa_hallucination.yml` routé vers une vraie verticale + warning sur `us_default`.
- **#66** (`0d6decb`, mergée) — fuite de marqueur interne `Tier/NEXUS-14 V5.0` dans le HTML publié, corrigée.
- **#67** (`73af639`, mergée) — `has_update_date` câblé + regex FAQ + `content_check` tier-relatif (84.0→93.0 sur 48624).
- **#68** (`cf3c089`, mergée) — levier "b" : signaux EEAT honnêtes déjà vrais (bio + liens méthodologie) reconnus (93.0→94.0).
- **#69** (CLOSED, jamais mergée) — PR empilée sur la branche de #68, auto-fermée par GitHub à la suppression de cette branche (aucune perte, contenu identique rouvert proprement sous #70).
- **#70** (`42d4395`, mergée) — levier "a" : Illustrative Scenarios, garde-fou anti-fabrication `_scenario_guard.py` (94.0→95.5).
- **#71** (`1383139`, mergée) — dédoublonnage du H2 de scénario écho + budget de mots resserré (finding réel, draft 48632).
- **#72** (`bbc446f`, mergée) — le mécanisme de retry ne pousse plus systématiquement la longueur à la hausse (ratchet à sens unique corrigé).
- **#73** (`a3cddc6`, mergée) — `production_v2.yml` réduit sous la limite GitHub de 21000 caractères d'expression `run:`.
- **#74** (`b5839ed`, mergée) — `word_count` recalculé frais depuis le contenu final chez agent_12, ne fait plus confiance aux métadonnées périmées.
- **#75** (`a198c69`, mergée) — seuil réel de GATE QA aligné sur 95/100 (`PUBLICATION_QUALITY_GATE`), conforme à `NEXUS14-PRIORITY.md` (était 85, codé en dur).
- **#76** (`0d752c6`, mergée) — mode `draft_only` réel sur `production_v2.yml` (`workflow_dispatch`, défaut `true`) : aucun run manuel ne peut plus promouvoir un topic en `published`.
- **#77** (`6271253`, mergée) — corps de la réponse HTTP loggé en cas d'erreur Claude côté agent_04 (observabilité, le bug 400 lui-même reste non résolu — voir plus bas).
- **#78** (`1d3ed8a`, mergée) — outillage `scripts/delete_wp_post.py` + workflow dédié (trash par défaut, garde-fou fat-finger) pour nettoyer les drafts témoins orphelins.
- **#79** (`a84152c`, mergée) — GATE LENGTH : plafond symétrique au floor-only actuel d'agent_04, même tolérance ±10% qu'agent_12, dans la même boucle de retry que G-Substance/G3/A/B.

**5 runs témoins et leurs verdicts** (topic = `us-car-insurance-foreign-drivers-students` sauf mention contraire) :
- **Run 1** (`29129933048`, 2026-07-10 23:25, 1 article, ancien seuil 85) → draft WP **48624**, `overall_score=84.0` → **GATE QA FAIL**. Re-scoré ensuite sans régénération au fil de #67/#68/#70 : 84.0→93.0→94.0→**95.5** (démontre le gain du scoreur, pas encore reproduit sur une génération fraîche à ce stade).
- **Run 2** — tentative antérieure référencée dans l'investigation Sprint 9 comme échouée avant WordPress (gate de contenu G-Substance/G3/A/B non franchi, donc aucun draft WP créé). Détails non re-vérifiés dans cette session — pas de score ni d'artefact à citer.
- **Run 3** → draft WP **48632** (2026-07-11 01:15, tagué `[QA-FAILED]` par `mark_qa_failed.py`, donc `overall_score` sous le seuil alors en vigueur = 85). A directement motivé le fix #71 (H2 de scénario écho dupliqué + budget de mots).
- **Run 4** (`29137518698`, 2026-07-11 03:17, ancien seuil 85) → draft WP **48640**, `overall_score=90.5` → **GATE QA PASS** (85 franchi), topic promu `published` dans le registre. Décision éditoriale ultérieure (barre utilisateur = 95, ce run était censé être draft-only) : dépublié, topic remis `candidate`, `post_id`/`published_at` effacés (commit `5d1799f`). Invariant Sprint 9 vérifié tenu (aucune violation — le code a fait exactement ce que son seuil de l'époque autorisait).
- **Run 5** (`29141394156`, 2026-07-11 05:33-05:52, 3 articles, `draft_only=true` — premier run sous le nouveau régime #75/#76) → **0/3 produits**, aucune promotion, registre inchangé (26 candidate + 2 published) :
  - Article 1 (même topic que 48640) : **GATE C FAIL**, dédoublonnage par titre normalisé contre le brouillon orphelin 48640 encore présent sur WordPress.
  - Article 2 (`us-send-money-to-india`) : draft WP **48652** créé (resté draft), `overall_score=82.5` (SEO 85, EEAT 91.2, Content 60) → **GATE QA FAIL**. Cause du Content=60 : 5232 mots vs cible tier 4000 (+30.8%), dépassement en génération de BASE, pas en retry.
  - Article 3 (`us-best-credit-cards-no-ssn`, PILLAR) : **agent_04 a planté deux fois** (`HTTP Error 400: Bad Request`, attempt 0 et 1) avant même d'atteindre WordPress.

**Bug agent_04 HTTP 400 — non résolu, désormais observable** : cause racine inconnue. Piste "outline-fallback → prompt malformé" investiguée (agent_03 était tombé en fallback pour ce même article juste avant) puis écartée faute de mécanisme de code reliant les deux — aucun appel `_call_claude` du chemin PILLAR ne lit les champs d'outline (`h3`/`data`) qui diffèrent entre un outline réel et le fallback. Fix livré (#77) : le corps de la réponse HTTP est maintenant lu et logué (tronqué à 2000 caractères) au lieu d'être perdu — la PROCHAINE occurrence sera diagnosticable directement dans les logs, celle-ci ne l'a pas été.

**Nettoyage drafts témoins orphelins** : `agent_11`'s dedup (`_duplicate_of`) bloque un topic dès qu'un post WP existant — draft ou publié, n'importe quel statut — matche son titre normalisé exactement. Audit complet (`list-drafts.yml`) : 4 drafts trouvés (48624, 48632, 48640, 48652), dont 3 déjà auto-neutralisés par le tag `[QA-FAILED]` de `mark_qa_failed.py` (le préfixe casse le match de titre — 48624, 48632, 48652 ne bloquent PAS leur topic). Seul **48640** (jamais taggé, seul run à avoir réellement passé QA sous l'ancien seuil) bloquait réellement son topic. **Supprimé** (`delete-wp-post.yml`, `force=false` → corbeille, récupérable) le 2026-07-11 06:13 ; confirmé `actual_status=trash` par relecture directe post-suppression. 48624/48632/48652 laissés en l'état (inoffensifs, tag QA-FAILED déjà présent).

**GATE LENGTH (#79)** : plafond symétrique ajouté à la boucle de retry existante (`target_words × 1.10`, même tolérance qu'agent_12) — un dépassement comme celui de l'article 2 du run 5 obtient désormais une chance de retry avec feedback ciblé avant d'atteindre GATE QA (non-retriable). Cas limite signalé, non traité : un dépassement bien plus large pourrait nécessiter un retry raccourcissant de plus de 20 %, ce qui déclencherait le garde-fou anti-régression de `structure_completeness_gate.py` — pas élargi préventivement.

- **Crons** : **toujours désactivés**. Seuil de publication réel maintenant aligné sur 95 (#75), mode draft-only réel disponible (#76), plafond de longueur symétrique en place (#79), bug 400 observable mais non résolu (#77 logging seulement).
- **Prochaine étape** : **run témoin 6, `draft_only=true`**, pour confirmer que l'ensemble (#74-#79) tient sur une génération fraîche. Si le run 6 est propre : diff de `production_v2.yml` pour passer l'input `draft_only` à `false` par défaut (réactivation effective des crons), à montrer avant merge — pas encore fait.

### 2026-07-11 — Session (suite) : run témoin 6 (échec crédits API), run témoin 6 bis (échec GATE LENGTH), root cause du retry identifié

- **Run témoin 6** (`29146699688`, 08:49-08:51, 3 articles, `draft_only=true`) → **0/3, échec en ~3min**. Cause : compte Anthropic API à sec (`HTTP 400: Your credit balance is too low`). Agent 02 a un fallback algorithmique (non-bloquant), Agent 03 (content planner) n'en a aucun → échec fatal identique sur les 3 articles, avant même Agent 04. Aucun rapport avec le code #71-#79. Crédits rechargés par l'utilisateur.
- **Run témoin 6 bis** (`29147164447`, 09:05-09:32, ~27min, 3 articles, `draft_only=true`) → **0/3, échec à GATE LENGTH (#79)**, première vraie mise à l'épreuve du plafond + retry raccourcissant :
  - Article 1 (car insurance, OPPORTUNITY, cible 4000w/plafond 4400w) : 4709w → retry → 4487w (-222w, encore +87 au-dessus).
  - Article 2 (send money USA→India, STANDARD, cible 4000w/plafond 4400w) : 5492w → retry → **5593w (+101w, PIRE)**.
  - Article 3 (credit cards no SSN, PILLAR, cible 4200w/plafond 4620w) : 6641w → retry → **6692w (+51w, PIRE)**.
  - **Le gate lui-même fonctionne parfaitement** : 3/3 dépassements détectés et bloqués, zéro article surdimensionné n'a atteint WordPress. **Le retry raccourcissant ne raccourcit pas.**
- **Root cause identifiée en lisant `agents/agent_04_article_writer.py`** (pas supposée, vérifiée ligne par ligne) : `retry_feedback` (via `_facts_and_rules`, construit ligne 779) n'est injecté QUE dans les appels comparison table (894), scénario illustratif (939), Expert Recommendation (949), FAQ (956/959) et Conclusion/Disclaimer (967) — **jamais dans l'intro (783-787) ni dans la boucle des sections de corps (791-863)**, qui portent la majorité du volume de mots (jusqu'à 5 sections × 400-750w). Ces sections de corps utilisent un `sec_target` FIXE (`600 if PILLAR else 500 if STANDARD else 400`, +150w de marge) identique à l'attempt 0 et à l'attempt 1 — aucune conscience du dépassement, aucune instruction de coupe. Une seule voie d'ajustement de longueur existe dans toute la fonction : l'expansion plancher (`if word_count < min_words: ...add more words`, ligne 976) — **aucun mécanisme symétrique de contraction au plafond**. Conséquence mécanique : sur retry, les sections de corps sont régénérées indépendamment avec les mêmes cibles qu'avant, donc le total oscille de ±1-4% par bruit stochastique du LLM plutôt que de baisser — exactement le pattern observé (1 article légèrement amélioré, 2 aggravés).
- **Fix nécessaire (non fait à ce stade)** : injecter `retry_feedback`/`_facts_and_rules` (ou une instruction de coupe dédiée) dans l'intro et la boucle de sections de corps, et rendre `sec_target` réactif à l'attempt (réduire proportionnellement au dépassement mesuré par le rapport GATE LENGTH de la tentative précédente) plutôt qu'une constante par tier.
- **Scénarios illustratifs (#70)** : présents et conformes dans les 3 brouillons malgré l'échec (1 scénario court 25-40 mots par article, rôle générique, zéro prénom inventé, disclaimer immédiat) — le garde-fou anti-fabrication tient. Anomalie mineure cosmétique repérée : `article_metadata.json` affiche `case_study_count: 0` dans les 3 cas alors que le scénario est bien présent dans le texte (champ non renommé après #70, aucun impact fonctionnel).
- **Marqueurs internes (#66)** : toujours 0 occurrence `NEXUS-14`/`V5.0` dans les 3 brouillons ; ligne `> **Last Updated**: July 2026` propre. Tient.
- **Non atteignable ce run** (pipeline mort avant) : score QA pilier par pilier (jamais atteint agent_12), image on-topic (jamais atteint la phase image), excerpt (jamais généré).
- **Crons** : **toujours désactivés**. Le plafond de longueur (#79) protège correctement mais son retry associé ne fonctionne pas encore — un nouveau fix ciblé sur `agent_04_article_writer.py` est nécessaire avant un run témoin 7.

### 2026-07-11 — Session (suite) : PR #80 (retry raccourcissant), run témoin 7, PR #81 (calibrage à la source + micro-trim), diagnostic 403

- **PR #80** (mergée, squash `94c2727`) : fix du root cause identifié ci-dessus. `_parse_length_overage()` extrait le vrai dépassement du rapport GATE LENGTH ; le `sec_target` des sections de corps est réduit proportionnellement (plancher 280w/section) ; `retry_feedback` atteint désormais l'intro et chaque section de corps. Test bout-en-bout ajouté (`tests/test_length_retry_convergence.py`, API mockée, câblage réel) — le trou identifié dans les tests de #79 (tester le retry isolément, sans le câblage réel) n'est pas répété.
- **Run témoin 7** (`29149027820`, 10:14-10:37, 3 articles, `draft_only=true`, sur `main` post-#80) → **0/3, encore bloqué à GATE LENGTH**, mais **le fix #80 fonctionne réellement en conditions réelles** :
  - Article 1 (OPPORTUNITY) : 4401w (+1w) → retry → 4976w (+576w, PIRE) — dépassement quasi nul (+1w) → coupe proportionnelle quasi nulle (1w/section) → le résultat est dominé par le bruit naturel du LLM, pas par le mécanisme.
  - Article 2 (STANDARD) : 5572w (+1172w) → retry → **4997w (+597w, -575w réel)** — nette amélioration, mais coupe plafonnée au plancher (280w/section, capacité 880w < 1172w requis) → insuffisant pour converger.
  - Article 3 (PILLAR) : 6422w (+1802w) → retry → **5266w (+646w, -1156w réel)** — nette amélioration, même limite de plancher (capacité 1600w < 1802w requis).
  - Comparé à run 6 bis (avant #80) où les articles 2 et 3 avaient EMPIRÉ (+101w, +51w), ils s'améliorent maintenant substantiellement (-575w, -1156w) — preuve empirique que #80 fonctionne, mais un plafond seul (retry après coup) ne suffit pas quand le dépassement de départ est trop grand.
  - Nouveau : `WP REST API 403 Forbidden` sur `/wp-json/wp/v2/posts` et `/pages` (GET public, pas d'auth) sur les 3 articles → 0 lien interne réel inséré (seul le lien fixe de la bio auteur reste) — voir diagnostic ci-dessous.
- **Diagnostic du taux de dépassement par tier** (demandé par l'utilisateur : calibrer à la SOURCE plutôt que couper plus fort), données réelles runs 5/6bis/7, cible vs mots réellement produits en tentative 0 :
  - **OPPORTUNITY** (cible 4000) : 4709 (+17,7 %), 4401 (+10,0 %) → moy. **+13,9 %**
  - **STANDARD** (cible 4000) : 5232 (+30,8 %, run 5), 5492 (+37,3 %), 5572 (+39,3 %) → moy. **+35,8 %**
  - **PILLAR** (cible 4200) : 6641 (+58,1 %), 6422 (+52,9 %) → moy. **+55,5 %**
- **PR #81** (branche `fix/calibrate-body-section-targets-at-source`) : calibrage à la source + micro-trim, la coupe élargie de #80 devient le filet de dernier recours :
  - **Calibrage tentative 0** : `sec_target_base` recalibré par tier à partir des données ci-dessus — coupe = min(besoin réel calculé, MOITIÉ de la marge jusqu'au plancher de 280w) — jamais la totalité, pour laisser une vraie marge de manœuvre au retry si la tentative 0 dépasse quand même. OPPORTUNITY 400→**348** (coupe 52w, non plafonnée, le besoin réel était sous la moitié de marge) ; STANDARD 500→**390** (coupe 110w, plafonnée à la moitié de marge — le besoin réel de 258w dépassait) ; PILLAR 600→**440** (coupe 160w, plafonnée à la moitié de marge — besoin réel 383w). Constantes nommées (`OPPORTUNITY_SEC_TARGET_BASE`, etc.) avec dérivation commentée dans le code.
  - **Résultat attendu** : OPPORTUNITY devrait passer GATE LENGTH SANS retry (le cas nominal visé par l'utilisateur) ; STANDARD/PILLAR restent susceptibles d'avoir encore besoin d'un retry (le plafonnage à la moitié de marge est un choix délibéré, documenté, pas une garantie de convergence totale) — à valider par un run témoin 8.
  - **Micro-trim** (`scripts/micro_trim.py`, nouveau) : pour un dépassement ≤2 % du plafond (le cas de l'article 1 du run 7, +1w), coupe mécanique déterministe (suppression de la dernière phrase de la plus longue section de corps éligible, jamais FAQ/comparison/expert/scenario/disclaimer/bio) au lieu de gaspiller un retry complet à coût API plein. Câblé en Phase 4.441, non-bloquant, avant GATE LENGTH.
  - **Tests** : `tests/test_body_section_calibration.py` (6 tests, constantes + câblage tentative 0 + preuve qu'OPPORTUNITY passe sans retry), `tests/test_micro_trim.py` (9 tests, dont un garde-fou sur la limite GitHub de 21000 caractères — le nouvel appel a réduit la marge du bloc `run:` du Batch Loop à ~650 caractères), `tests/test_length_retry_convergence.py` mis à jour pour référencer les nouvelles constantes dynamiquement (plus de littéraux figés qui auraient pu dériver silencieusement, comme signalé par l'utilisateur sur #79). Suite complète : 584 tests passent.
- **Diagnostic 403 WordPress** (agent de recherche dédié, code non modifié) :
  - Le code actuel (`agents/_real_internal_links.py`) ne capture NI les en-têtes NI le corps de la réponse sur une `HTTPError` — seul `str(e)` ("HTTP Error 403: Forbidden") est loggé. Confirmé absent des logs du run 7 : aucun `cf-ray`/`x-hcdn-request-id` nulle part.
  - `wp_diag.py` (utilisé par `wp_diagnostic.yml`) capture déjà en-têtes + corps ; son dernier run (`29128486450`, 2026-07-10) confirme le header exact à chercher : `x-hcdn-request-id` (Hostinger CDN), mais ce run-là était un 200, pas un 403 — donc pas de request-id disponible pour CE 403 spécifique.
  - **Nouveau** : AUDIT-LOG ne mentionnait aucun 403 avant cette session — le 401 du 2026-07-10 (mot de passe app expiré) est un problème DIFFÉRENT, déjà résolu, confirmé par un corps JSON WordPress propre (pas de page de challenge HTML). Impossible de confirmer WAF-vs-autre sans capturer le corps/en-têtes de CE 403.
  - **Fix minimal identifié, non implémenté** (diagnostic seulement, sur demande explicite) : dans `agents/_real_internal_links.py`, capturer `e.headers.get('x-hcdn-request-id')`/`cf-ray`/`server` + `e.read()[:500]` avant de logger, pour rendre la PROCHAINE occurrence diagnosticable (même principe que le fix #77 sur les erreurs HTTP d'agent_04).
  - **Impact si non résolu** : chaque article futur n'aura qu'1 lien interne (celui de la bio auteur) au lieu de 3-8 — plafonne silencieusement les scores SEO/EEAT de tous les prochains runs, gate ou pas gate de longueur.
- **PR #81** (mergée, squash `4424323`) : calibrage à la source livré tel que décrit ci-dessus.
- **PR express — observabilité 403** (`agents/_real_internal_links.py`) : le fix minimal identifié ci-dessus, implémenté avant le run témoin 8 (sinon une récidive du 403 aurait de nouveau été undiagnosticable, gaspillant le run). Nouvelle fonction `_describe_http_error(e)` : capture `x-hcdn-request-id`/`cf-ray`/`server` + un extrait borné (500 car.) du corps de réponse sur toute `HTTPError`, fallback silencieux vers `str(e)` pour tout autre type d'erreur (timeout, DNS, ...) — comportement inchangé dans ce cas. Câblée dans `fetch_real_posts()` (les 2 branches d'erreur) et `fetch_methodology_links()`. 10 nouveaux tests dans `tests/test_real_internal_links.py` (extraction des headers, absence propre quand aucun header n'est présent, troncature du corps, non-crash si le corps est déjà consommé, et bout-en-bout via `caplog` que le request-id atteint bien le log). Suite complète : 584 tests passent, 1 skip.
- **Crons** : **toujours désactivés**. Calibrage (#81) et observabilité 403 tous deux mergés — run témoin 8 prêt à être lancé.

### 2026-07-11 — Session (suite) : run témoin 8 — calibrage + micro-trim prouvés, un article passe TOUS les gates de contenu, 403 confirmé WAF

- **Run témoin 8** (`29154971226`, 13:48-14:08, ~20min, 3 articles, `draft_only=true`, sur `main` post-#81+#82) → **0/3 produits**, mais **jalon** : c'est la première fois cette session qu'un article franchit GATE LENGTH, G-Substance, G3, GATE A ET GATE B.
  - **Article 1 (OPPORTUNITY)** : tentative 0 = 4449w (calibrage seul insuffisant, encore +49w/1,1% au-dessus du plafond 4400w) → **MICRO-TRIM déclenché** (2 phrases supprimées) → 4391w → **GATE LENGTH PASS SANS RETRY**. Puis G-Substance PASS, G3 PASS (max cosine 0,716<0,80), GATE A `PASS_WITH_WARNINGS` (4 claims, 0 vérifiées formellement mais heuristique OK, 3 URLs cassées dont 2 `.gov` bot-bloquées), **GATE B EEAT PASS = 98,3/100** (Experience 100, Expertise 100, Authority 93,3, Trust 100) — score réel jamais vu aussi haut cette session. Mort ensuite à **GATE C** : `no post_id returned from WordPress` — les 5 images (réellement générées, non-placeholder) et la création du post ont toutes échoué en 403.
  - **Article 2 (STANDARD)** : tentative 0 = 5231w (+831/18,9 % — trop grand pour micro-trim) → retry → 4894w (+494/11,2 %, encore trop grand) → **GATE LENGTH FAIL, retry épuisé**. Comparé à la moyenne pré-calibrage (5432w), la tentative 0 seule est déjà **~200w meilleure** — le calibrage aide réellement, insuffisant seul pour ce tier.
  - **Article 3 (PILLAR)** : tentative 0 = 5962w (+1342/29,0 % — trop grand pour micro-trim) → retry → 5139w (+519/11,2 %, encore trop grand) → **GATE LENGTH FAIL, retry épuisé**. Comparé à la moyenne pré-calibrage (6532w), la tentative 0 seule est **~570w meilleure** — amélioration substantielle, toujours insuffisante seule.
  - **Micro-trim** : déclenché uniquement sur l'article 1 (seul dépassement ≤2 %) ; correctement abstenu sur les 4 autres occasions (18,9 %, 11,2 %, 29,0 %, 11,2 % — tous logués avec la raison précise, jamais un no-op silencieux).
- **403 WordPress — confirmé côté edge Hostinger (hcdn), pas un problème applicatif WordPress** [voir mise à jour ci-dessous : PAS un blocage WAF statique] : le fix d'observabilité (#82) a capturé le corps de la réponse pour la première fois — c'est une **vraie page HTML de challenge/attente** (`<meta http-equiv="refresh" content="30">`, `<meta name="robots" content="noindex,nofollow">`), PAS une erreur JSON WordPress propre (`rest_forbidden` etc.). Preuve supplémentaire : le fact-checker (GATE A) a tenté de vérifier `https://moneyabroadguide.com` (la homepage nue, pas un endpoint REST) et a reçu 403 aussi — le blocage touche TOUT le trafic HTTPS vers le site depuis l'IP du runner GitHub Actions, lecture ET écriture (images + création de post WordPress ont aussi 403). Request-IDs Hostinger capturés (échantillon, tous au format `<hash>-phx-edge{6,8,9}`, plusieurs edge nodes distincts) : `05c57c75f4a26b646124059f9df7b998-phx-edge9`, `8c54e9e6d7a522b0334a69b2783e93d7-phx-edge6`, `e0965c93578d28b583e48d1297a0d678-phx-edge9`, `fa387a1d26485be81d1ca5e92e38e596-phx-edge6`, `4f9b8c62239c1ec3d64aedefb675509c-phx-edge8`, `8a080066b3fe803ab7d3268f9e269da0-phx-edge6`, `a7b56b963cfc0880e6b34c29660f1b42-phx-edge6`, `9696af53020405aa3ec984b65245ea24-phx-edge9`, `40beea016123bf722b3d8d9dc223438f-phx-edge9`, `301f2279dc08d987bcbfd877a9c55ede-phx-edge9`. Suffisant pour ouvrir un ticket Hostinger avec preuves concrètes (corps HTML + request-ids + horodatages + confirmation que même la homepage nue est bloquée).
- **Vérifications habituelles** : marqueurs internes 0/3 (tient), scénarios illustratifs conformes sur les 3 (rôle générique, zéro prénom inventé), image vedette de l'article 1 inspectée visuellement — on-topic confirmé (professionnelle de bureau examinant un formulaire "Car Insurance for International Drivers"), jamais uploadée sur WP (403) mais générée localement, non-placeholder.
- **Crons** : **toujours désactivés**. Prochaine étape suggérée : ticket Hostinger (WAF confirmé) + éventuelle 2e passe de calibrage (FAQ/comparison/expert) pour STANDARD/PILLAR si le 403 se résout et qu'on veut pousser plus loin la convergence sans retry.

### 2026-07-11 — Session (suite) : hypothèse WAF statique INVALIDÉE — 403 intermittent, probablement lié au volume/pattern de requêtes

Découverte hPanel de l'utilisateur : CDN Security Level déjà sur "Essentially off", aucune IP bloquée manuellement — l'hypothèse d'un blocage WAF statique/permanent ne tient donc plus telle quelle. Vérifications menées pour trancher WAF vs plugin WordPress vs autre :

- **GET local (machine de l'utilisateur) sur `/wp-json/wp/v2/posts` sans authentification** : `200 OK`, JSON propre, headers réels (`platform: hostinger`, `panel: hpanel`, `server: hcdn`, `x-hcdn-request-id`).
- **Diagnostic léger déclenché EN DIRECT depuis un vrai runner GitHub Actions** (`wp_diagnostic.yml`, run `29156687294`, 2026-07-11 14:45-14:46 UTC) : **les 3 appels réussissent** — GET `/wp-json/` sans auth (200), GET `/wp-json/wp/v2/users/me` avec auth (200), POST `/wp-json/wp/v2/posts` création de draft avec auth (**201**, post `48659` créé puis supprimé proprement par le script). **Depuis la même classe d'infrastructure qui échouait dans les runs 7 et 8, tout fonctionne à l'instant T.**
- **Contraste clé** : diagnostic léger = 3 requêtes en ~20s → 100 % succès. Runs de production = ~15-20+ requêtes étalées sur ~20 minutes → quasi 100 % d'échec. Les mêmes edge nodes Hostinger (phx-edge6/8/9) servent le succès du diagnostic ET les échecs des runs de production — donc ce n'est ni un edge node défaillant, ni un blocage IP statique (la même classe de source réussit maintenant).
- **Namespaces REST enregistrés** (révélés par le diagnostic) : `oembed/1.0`, `code-snippets/v1`, `litespeed/v1`, `litespeed/v3`, `redirection/v1` — **aucun namespace de plugin de sécurité** (`wordfence/v1`, `ithemes-security/v1`, etc.) n'apparaît. Combiné aux headers `hcdn`/`hostinger`/`hpanel` présents sur CHAQUE réponse (succès et échecs), ceci pointe vers un blocage côté **edge Hostinger (hCDN)**, pas un plugin WordPress au niveau origine.
- **Nouvelle hypothèse, plus précise** : probablement un mécanisme automatique de rate-limiting / détection d'abus basé sur le VOLUME ou le PATTERN de requêtes (pas un rate au sens "trop rapide" — les requêtes de production sont elles-mêmes espacées de secondes à minutes à cause du temps de génération LLM, pas de rafale brute) sur une fenêtre glissante plus longue, indépendant du réglage "CDN Security Level" (qui ne semble couvrir qu'une couche WAF distincte, configurable). Cette couche ne serait donc PAS désactivable depuis hPanel via ce réglage précis.
- **Dossier ticket créé** : `docs/hostinger-403-ticket.md`, entièrement révisé pour refléter cette nouvelle hypothèse (pas "bloquez notre IP", mais "quel mécanisme automatique explique un lot complet bloqué alors qu'un test léger simultané passe ?"). Contient : tableau comparatif diagnostic-léger vs run-complet, liste des request-ids, endpoints lecture+écriture, namespaces REST, limites connues (IP du runner non loggée, request-id manquant côté écriture agent_10/11).
- **Crons** : **toujours désactivés**. Le ticket Hostinger est prêt à envoyer avec cette hypothèse révisée. Si Hostinger confirme un mécanisme de rate-limiting, la solution pourrait être aussi simple qu'espacer davantage les appels API du pipeline ou qu'un ajustement côté Hostinger — à voir selon leur réponse.

### 2026-07-11 — Session (suite) : implémentation du retry + espacement sur le 403-challenge, avant run témoin 9

Observation de l'utilisateur : le corps du 403 contient `<meta http-equiv="refresh" content="30">` — la page de challenge elle-même dit de réessayer après 30s. Implémenté en PR express :

- **Module partagé `agents/_wp_challenge.py`** (nouveau) : `is_challenge_403(status, body)` — détecte UNIQUEMENT la signature exacte du challenge Hostinger (403 + meta-refresh 30s dans le corps) ; un 403 dur (JSON `rest_forbidden` propre, ou le 403 non-lié d'un AUTRE site) retourne `False` et n'est JAMAIS retenté. `RETRY_DELAYS_SECONDS = (35, 70, 140)` (3 retries, backoff croissant, 4 tentatives au total). `INTER_CALL_SPACING_SECONDS = 2.5` (espacement préventif avant CHAQUE appel WordPress). Deux wrappers génériques (`call_with_challenge_retry` sync, `call_with_challenge_retry_async` async) réutilisables par n'importe quel client HTTP.
- **Câblé sur les 4 chemins WordPress demandés, plus 2 supplémentaires trouvés en auditant le code** :
  1. `agents/_real_internal_links.py` (lecture agent_04, urllib) — `fetch_real_posts`, `fetch_methodology_links`.
  2. `agents/agent_17_cannibalization.py` (lecture, requests) — `fetch_wordpress_articles`.
  3. `services/wordpress_service.py` (écriture agent_11, aiohttp — le CLIENT CENTRAL : create_post, update_post, upload_image, update_media, set_post_author, set_post_meta, get_categories, get_post, find_posts — 10 méthodes, un seul point d'intégration `_request_with_challenge_retry`).
  4. `agents/agent_10_image_production.py` (upload média, chemin séparé de wordpress_service.py, aiohttp) — `_upload_to_wordpress`. Bug corrigé au passage : le corps n'était tronqué qu'à 200 caractères AVANT de chercher la signature — la balise meta-refresh du vrai challenge Hostinger commence vers le caractère 234, donc jamais détectable avec l'ancienne troncature.
  5. `agents/agent_11_wordpress_integration.py` (`_resolve_category_ids`, aiohttp, chemin séparé de wordpress_service.py).
  6. `agents/agent_05_fact_checker.py` (GATE A, fact-check des URLs) — **scopé au domaine propre uniquement** (`_INTERNAL_HOST` de `agents/_sources.py`) : une source externe (.gov) qui renvoie son PROPRE 403 (déjà géré comme `bot_blocked`, cf. `tests/test_sprint2_quality.py`) n'est JAMAIS retentée — seul un 403 sur moneyabroadguide.com lui-même (observé dans le run 8, homepage nue vérifiée par le fact-checker) déclenche le retry.
- **Bug trouvé en cours de route** : `HTTPError.read()` (urllib) est un flux à usage unique — lire le corps pour la détection de signature videait ensuite `_describe_http_error()` (fix #82) de son propre `body=...`. Corrigé en mettant le corps en cache sur l'exception (`e._wp_challenge_body`) pour que les deux logiques coexistent sans se marcher dessus.
- **Tests** : `tests/test_wp_challenge.py` (14, logique pure du module partagé), plus les tests spécifiques à chaque intégration (`test_real_internal_links.py` +10, `test_agent17_challenge_retry.py` +4, `test_wordpress_service_challenge_retry.py` +9, `test_agent05_challenge_retry.py` +5) — chacun couvre : le challenge retente et réussit, le 403 dur ne retente JAMAIS, l'épuisement des 3 retries échoue proprement, l'espacement s'applique même sur un succès direct. Suite complète : 607 tests passent.
- **Impact durée chiffré** (demandé) : ~48 appels WordPress au total sur un run 3 articles (16/article : 2 agent_17 + 2 agent_04 + 1 agent_05 pire cas + 5 uploads image agent_10 + 6 agent_11). Surcoût FIXE (espacement, toujours) : 48 × 2,5s = **+2 min**, sur CHAQUE run. Scénario réaliste (chaque appel prend le challenge UNE fois, résolu au 1er retry) : 48 × 35s = **+28 min**. Scénario théorique maximal (chaque appel épuise ses 3 retries, ne se résout JAMAIS — équivaut à une panne WordPress totale) : 48 × 245s = **+196 min (~3h17)**, ce qui dépasserait le `timeout-minutes: 120` du job `production_v2.yml` — cas pathologique signalé, pas un mode de fonctionnement normal attendu.
- **Crons** : **toujours désactivés**. Prêt pour un run témoin 9 pour valider le comportement réel du retry/espacement en conditions de production.

### 2026-07-11 — Session (suite) : run témoin 9 — JALON : un article traverse tout le pipeline jusqu'à GATE QA, avec vrais liens internes et images live

- **Run témoin 9** (`29158089485`, 15:32-16:02, ~30min, 3 articles, `draft_only=true`, sur `main` post-#83, lancé alors que le PC de l'utilisateur s'est déconnecté en cours de route — confirmé : le run tourne sur l'infra GitHub Actions, indépendant de la machine locale) → **0/3 produits**, mais **première fois cette session qu'un article atteint GATE QA (agent_12) avec un score réel**, ET premières vraies images/liens internes en conditions réelles.
  - **Article 1 (OPPORTUNITY)** : GATE LENGTH tentative 0 = 4547w (+147w/3,3 % — trop grand pour le micro-trim à 2 %) → retry → 4235w **PASS**. G-Substance/G3/GATE A (`PASS_WITH_WARNINGS`)/**GATE B EEAT 98,3/100 PASS** tous franchis. **GATE C PASS** : post WordPress réel créé (`post_id=48670`), **5/5 images uploadées avec succès** (0 erreur), image vedette confirmée on-topic. **GATE QA (agent_12) atteint pour la première fois** : SEO 100/100, EEAT **81,2/100** (Experience 50, Expertise 100, Authority 75, Trust 100), Content 100/100, **overall = 92,5/100** — sous le seuil de 95 → GATE QA FAIL, tagué `[QA-FAILED]`. `internal_link_count=3` (réel, pas juste le lien de la bio).
  - **Article 2 (STANDARD)** : GATE LENGTH tentative 0 = 5081w (+681/15,5 %) → retry → 4645w (+245/5,6 %, encore au-dessus) → **FAIL, retry épuisé**.
  - **Article 3 (PILLAR)** : GATE LENGTH tentative 0 = 5976w (+1356/29,4 %) → retry → 5462w (+842/18,2 %) → **FAIL, retry épuisé**.
  - **0/3 en tentative 0 cette fois** (différent du run 8 où 1/3 passait directement) — mais article 1 est passé au retry classique, à seulement 3,3 % au-dessus du plafond initial.
- **403-challenge : ZÉRO occurrence sur tout le run** — un seul incident WordPress au total, un timeout réseau banal (`The read operation timed out`, sans rapport avec le 403). La théorie du refresh-30s n'a donc pas pu être vérifiée en conditions réelles cette fois (rien à retenter) — mais lecture ET écriture WordPress ont fonctionné de bout en bout sans un seul blocage, une première cette session. Impossible de trancher si l'espacement préventif (#83) a empêché le déclenchement ou si le phénomène est simplement intermittent et ne s'est pas manifesté.
- **Anomalie repérée** : `meta_description` du rapport WordPress affiche `"Guide to  for expats."` — mot-clé manquant, double espace. Bug de template (probablement une variable non interpolée), jamais repéré avant puisqu'aucun article n'avait atteint ce stade cette session. Non traité, à investiguer.
- **Incohérence EEAT découverte** : GATE B (agent_06_eeat_validator) donne 98,3/100 pour l'article 1 ; GATE QA (agent_12_quality_assurance), quelques minutes plus tard, calcule 81,2/100 pour le MÊME article — un écart de 17 points sur le même score nominal ("EEAT"), deux implémentations différentes. Investigation lancée en session suivante (voir ci-dessous).
- **Crons** : **toujours désactivés**. Prochaine priorité : réconcilier les deux implémentations EEAT (agent_06 vs agent_12) avant de continuer les runs témoins — un article qui franchit enfin QA rend l'écart visible et bloquant pour la première fois.
