# WORKFLOW.md — Audit éditorial article par article (MoneyAbroadGuide)

**But** : rendre chaque article publié conforme aux standards Google AdSense pour un site
YMYL (finance). Objectif concret : aucun chiffre inventé, aucune source fantôme, aucun
fait faux, aucun doublon, aucune cannibalisation, aucun lien mort.

Ce document est la **référence stable**. Il se lit avec `AUDIT-LOG.md` (le journal des
articles déjà traités et des décisions prises). **Lis les deux avant de commencer un article.**

Le site a été peuplé par un pipeline de génération automatique qui a semé des erreurs
partout : chiffres fabriqués, statistiques attribuées à des organismes sans lien réel,
titres charabia, faux témoignages nommés, images gabarit hors sujet, doublons, chaînes
de redirection. **Aucun article n'est présumé propre — même un article qu'on a nous-mêmes
enrichi, même un article "destination" de fusion.**

---

## PRINCIPE CENTRAL (à ne jamais violer)

> **On n'affirme un fait que s'il est vrai et sourçable. Sinon on le retire ou on le
> reformule en principe sans chiffre. Face à un chiffre invérifiable, on RETIRE — on
> n'invente jamais un remplaçant.**

Le marqueur `[À VÉRIFIER]` n'est pas une case à cocher qui absout : c'est un signal que
la recherche reste à faire. Un `[À VÉRIFIER]` ne doit jamais être publié tel quel. Soit
il est vérifié et remplacé par la vraie valeur sourcée, soit il est retiré/reformulé.

---

## LES 8 RÈGLES APPRISES (issues du prototype — ne pas les redécouvrir à la dure)

1. **Le scan est ITÉRATIF, jamais une passe unique.** Sur le prototype, il a fallu 5 passes
   successives pour atteindre le fond d'un seul article. Un article n'est déclaré propre
   que quand un scan complet revient VIDE — pas quand on a traité la première liste de
   trouvailles.

2. **Le re-balayage post-écriture attrape les oublis de la passe elle-même.** Après avoir
   écrit les corrections, re-scanne : on a déjà oublié des éléments dans la passe d'écriture
   qui n'ont été rattrapés que par le re-balayage.

3. **Une passe ciblée (section par section) RATE des choses.** Deux fois sur le prototype,
   une correction ciblée a manqué une section entière ou plusieurs passages. Toujours
   préférer un scan exhaustif du contenu complet à une correction de zones connues.

4. **Un article "destination" de fusion n'est PAS présumé propre.** Quand on fusionne un
   doublon dans un canonique, le canonique lui-même entre dans la file de scan. On a enrichi
   un article en vérifiant chaque ajout, mais son contenu préexistant n'avait jamais été
   audité — angle mort classique.

5. **Corriger un lien dans la navigation (menu/homepage) ne corrige PAS ses occurrences
   dans le corps des articles.** Ce sont deux couches distinctes. Un slug mort corrigé dans
   le menu peut traîner dans le corps de plusieurs articles. Les scanner séparément.

6. **Vérification de redirection = TOUJOURS en cache-busté (`no-store` / `redirect: manual`).**
   Le cache navigateur peut continuer à servir un ancien 301 et faire croire qu'une
   redirection tient encore alors qu'elle a été supprimée côté serveur. La vérité serveur
   ne se lit qu'en cache-busté.

7. **CodeMirror / éditeur de code ment.** Le message "File edited successfully" peut être
   faux : l'éditeur resynchronise son contenu (non modifié) par-dessus avant l'envoi. Toute
   écriture dans un éditeur de code passe par l'instance CodeMirror (`cm.setValue()` +
   `cm.save()`) ET est suivie d'une relecture À FROID (rechargement complet) pour confirmer
   la persistance. Jamais se fier au message de succès seul. Idem Gutenberg : relire le
   contenu stocké après rechargement.

8. **Ne jamais lever une redirection / publier un contenu avant qu'il soit 100 % propre.**
   Tant qu'une redirection masque un article, c'est un filet : on peut le nettoyer
   tranquillement. La lever avant que le balayage revienne vide, c'est exposer un article
   à moitié corrigé. Le critère "100 % propre" ne se négocie pas ("propre sauf ce qu'on
   décide d'ignorer" = interdit).

---

## PROCÉDURE PAR ARTICLE (ordre strict)

### Phase 0 — Préparation
- Lis `AUDIT-LOG.md` : cet article a-t-il déjà été touché ? Des décisions liées ont-elles
  été prises sur des articles du même thème ?
- Confirme qu'une sauvegarde DB récente existe (voir "Sauvegardes" plus bas) AVANT toute
  action destructive.

### Phase 1 — Scan exhaustif (LECTURE SEULE, itératif)
Scanne le contenu stocké complet (pas seulement les zones suspectes) pour TOUS les motifs
de la grille de décision ci-dessous. Produis la liste exhaustive : chaque trouvaille avec
sa phrase exacte, sa catégorie, et le traitement proposé. Re-scanne jusqu'à ce que la liste
se stabilise.

### Phase 2 — Recherche & décision
Pour chaque trouvaille, applique la grille. Les faits fiscaux/réglementaires demandent une
VÉRIFICATION contre source officielle (voir liste des sources). Prépare le plan complet.

### Phase 3 — Validation humaine (voir prompt permanent pour le rythme exact)
- **Les faits fiscaux/chiffrés remontent AVANT écriture**, avec leur source officielle, pour
  confirmation sur pièce. (C'est le seul endroit où la vérif humaine sur source est
  irremplaçable.)
- Le reste peut être présenté groupé.

### Phase 4 — Écriture
Écris les corrections validées. Relecture À FROID (rechargement) pour confirmer persistance
et rendu (pas de bloc/liste/figure orphelin).

### Phase 5 — Re-balayage final
Re-scanne l'article complet. Le balayage DOIT revenir vide (0 nom de banque parasite,
0 chiffre non sourcé, 0 stat datée, 0 organisme périmé, 0 figure hors sujet, 0 faux cas
nommé, 0 lien mort). S'il trouve encore quelque chose → retour Phase 2. On ne publie/ne
lève une redirection QUE sur balayage vide.

### Phase 6 — Journalisation
Mets à jour `AUDIT-LOG.md` (article, trouvailles, décisions, `[À VÉRIFIER]` résolus/restants)
et commit.

---

## GRILLE DE DÉCISION (la jurisprudence)

### A. Noms de banques / produits financiers nommés
- **Si cité pour illustrer une pratique GÉNÉRALE** (ex. "certaines banques vérifient le DLI")
  → **généraliser** ("some institutions", "some digital banks").
- **Si cité pour dupliquer une comparaison qui vit ailleurs** (tableaux, mini-revues, "top
  picks") → **supprimer** le bloc, remplacer par un renvoi vers l'article de comparaison
  dédié.
- **Si la phrase ne sert QUE à nommer une banque sans info** → **supprimer** entièrement.
- Un tableau/mini-revue de plusieurs banques avec taux = cannibalisation → suppression +
  renvoi. (Attention : ce type de bloc apparaît souvent PLUSIEURS fois dans un même article,
  à des endroits différents — le scan itératif est fait pour ça.)

### B. Chiffres (taux, %, montants, seuils, délais)
- **Chiffre daté d'une année révolue** ("as of 2024", "2024 limit") sur un article 2026
  → mettre à jour avec la valeur courante SOURCÉE, ou retirer. Jamais garder un chiffre
  périmé. **Exception** : si le chiffre est explicitement valable pour une plage incluant
  l'année courante (ex. limite TFSA "2024–2026"), le garder en corrigeant le libellé.
- **Taux bancaire / promotionnel non sourcé** (ex. "3.5%–5.5% APY") → généraliser ("les taux
  varient selon le fournisseur et les conditions de marché") + renvoi vers l'article de
  comparaison.
- **Délai chiffré non sourcé** ("30–60 jours", "24–48h", "6–24 mois") → reformuler en principe.
  Mais NE PAS rendre creux : là où le délai est utile au lecteur (ex. obtention du SIN),
  écrire "le délai varie, voir [source officielle]" + lien, plutôt qu'un vague "rapidement".
- **Comparaison illustrative chiffrée** ("sur 5000$, X génère Y") → OK si clairement présentée
  comme illustration ET si elle ne s'appuie pas sur un taux non sourcé qu'on retire par
  ailleurs. Sinon reformuler sans chiffre.

### C. Faits fiscaux / réglementaires (LE POINT SENSIBLE — vérifier, pas supprimer)
Ce sont des faits qui EXISTENT (contrairement aux taux bancaires inventés). Ne pas supprimer
aveuglément : VÉRIFIER contre source officielle.
- **Vérifié correct + courant** → garder + ajouter le lien officiel.
- **Vérifié périmé** → mettre à jour avec la valeur courante sourcée.
- **Vérifié FAUX** → corriger (ex. sur le prototype : "25% withholding sur les intérêts des
  non-résidents" était FAUX — les intérêts versés à un non-résident sans lien de dépendance
  sont généralement EXEMPTÉS ; le 25% s'applique aux dividendes/pensions/loyers).
- **Invérifiable / aucune source officielle par nature** (ex. politique interne d'une banque)
  → reformuler en principe sans chiffre ("varie selon l'institution, à confirmer auprès du
  prêteur").
- **Règle de cohérence** : afficher un chiffre SEULEMENT s'il est vrai pour l'année de
  l'article. Un chiffre correct mais daté de l'an dernier (ex. "basic personal amount 2025")
  sur un article 2026 → préférer le PRINCIPE sans chiffre ("voir l'ARC pour le seuil courant")
  plutôt que d'afficher une valeur qui paraîtra périmée.

### D. Statistiques attribuées à un organisme
- **Pas de lien direct vers la page officielle contenant EXACTEMENT le chiffre** → SUPPRESSION.
  Règle absolue depuis le début. "60% selon l'IRCC" sans le lien exact = supprimé ou reformulé
  en principe. (Sur le prototype, une stat "1 million d'étudiants" s'est révélée FAUSSE à la
  vérif IRCC — le vrai chiffre était différent et en baisse. D'où : vérifier ou retirer,
  jamais garder sur la foi de l'attribution.)

### E. Études de cas / témoignages nommés
- **Noms de personnes + histoires présentées comme réelles** ("Priya Sharma, infirmière...")
  → requalifier en **"Illustrative Scenario"** anonymisé, recentré sur la logistique utile,
  SANS nom, SANS banque nommée, SANS taux promo précis. Ajouter une mention explicite que
  c'est un scénario illustratif, pas un témoignage.
- S'applique aussi à la HOMEPAGE (sections "case studies" / "testimonials" en faux avis
  clients).

### F. Images gabarit mal assignées
- **Image dont l'alt/légende est hors sujet** (ex. infographie "taxes" sur un article épargne)
  → **retrait pur** du bloc `<figure>` (image + légende). Pas de recaption (une légende
  honnête ne rend pas l'image pertinente), pas de placeholder. Un vrai visuel pertinent
  pourra venir plus tard.
- **Attention** : ce type d'image gabarit est souvent plaqué en PLUSIEURS exemplaires dans
  un même article et à travers TOUT le site. Motifs à chercher dans alt/légende : "taxes
  options", "taxes checklist", "taxes process", et tout "[X] options/checklist/process"
  incohérent avec le sujet.

### G. Organismes / entités périmés ou incorrects
- Vérifier que les organismes cités existent encore et sont les bons. (Sur le prototype :
  "DICO" — Deposit Insurance Corporation of Ontario — a été dissous en 2019 et fusionné dans
  la FSRA. L'article citait un organisme mort. → corriger en FSRA.)
- Vérifier que les services tiers commerciaux nommés sont réellement pertinents pour le
  CANADA (sur le prototype : "Nova Credit" est un service B2B centré USA, bâti sur le FCRA,
  sans disponibilité canadienne confirmée → mentionné en principe sans le nommer).

### H. Doublons de structure interne
- Plusieurs bios auteur, plusieurs disclaimers, deux sections FAQ, deux H2 quasi identiques
  → dédupliquer (garder une bio, un disclaimer, une FAQ fusionnée et renumérotée).

### I. Résidus de pipeline
- "add mentions", "No affiliate opportunities detected", "Quick Answer", "TODO", texte non
  anglais, numérotation FAQ non séquentielle, titres charabia auto-générés ("Best How
  Newcomers Build...") → nettoyer / réécrire.

### J. Liens
- **Liens internes → tester en no-store.** 404 = à corriger. Préférer une **301 globale** du
  slug mort (neutralise toutes les occurrences d'un coup, corps d'article inclus) plutôt que
  d'éditer chaque article.
- **Doublons d'articles** → identifier le canonique (titre propre + meilleure structure
  E-E-A-T priment sur l'ancienneté), FUSIONNER le contenu unique de l'autre AVANT mise en
  corbeille, puis corbeille + 301. Vérifier qu'aucune chaîne de redirection à 2+ sauts ne
  se crée (re-pointer les anciennes règles directement vers le canonique final).
- **Liens vers sources officielles** : privilégier un lien direct vers la page qui contient
  le fait. (Note SEO mineure : `nofollow` sur une source d'autorité gouvernementale n'est
  pas idéal — à harmoniser lors d'une passe SEO ultérieure, non bloquant.)

---

## SOURCES OFFICIELLES DE RÉFÉRENCE (pour la vérification catégorie C/D/G)
- ARC / CRA : cra-arc.gc.ca et canada.ca (impôts, TFSA/FHSA, retenues non-résidents, T5,
  montant personnel de base)
- IRCC : canada.ca (statistiques immigration, permis d'études)
- Service Canada / EDSC : canada.ca (SIN / NAS, y compris NAS commençant par 9)
- FCAC / ACFC : canada.ca (dossiers et scores de crédit)
- CDIC : cdic.ca (assurance-dépôts fédérale, 100 000 $/catégorie)
- FSRA / FSRAO : fsrao.ca (credit unions Ontario, dépôts non enregistrés, 250 000 $)
- OSFI / BSIF : osfi-bsif.gc.ca
- Pour les taux bancaires / comparaisons de comptes : NE PAS chiffrer dans l'article,
  renvoyer vers l'article de comparaison dédié du site.

**Règle CAPTCHA / anti-robot** : si une source officielle est protégée par un CAPTCHA ou une
vérification anti-robot, NE PAS la contourner. Signaler que le point n'a pas pu être vérifié
et le traiter en principe sans chiffre (ou le remonter pour vérification humaine manuelle).

---

## SAUVEGARDES & SÉCURITÉ TECHNIQUE
- **Sauvegarde DB** avant toute action destructive (corbeille, réattribution). Via Duplicator
  (vérifier statut "completed" réel + fichier de taille non nulle — ne pas se fier au message)
  OU via hPanel Hostinger (mécanisme indépendant, filet de secours si Duplicator patine).
- **Corbeille, jamais suppression définitive.** Les articles en corbeille y restent ~30 jours.
- **301 vérifiées en no-store AVANT toute mise en corbeille** de la source.
- Plugins en place utiles : Redirection (John Godley) pour les 301 ; Yoast SEO (meta
  descriptions) ; Internal Link Juicer (liens auto par mots-clés — s'auto-guérit, n'injecte
  pas vers une cible en corbeille) ; Duplicator (sauvegardes).

---

## CE QU'ON NE FAIT JAMAIS
- Inventer/deviner un chiffre financier, taux, limite fiscale, statistique.
- Publier un `[À VÉRIFIER]` non résolu.
- Lever une redirection / publier avant balayage vide.
- Se fier à un message "succès" d'éditeur sans relecture à froid.
- Vérifier une redirection sans cache-bust.
- Contourner un CAPTCHA pour "trouver" une source.
- Présumer propre un article (même un canonique enrichi par nous).
