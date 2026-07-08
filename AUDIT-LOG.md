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
