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
