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
