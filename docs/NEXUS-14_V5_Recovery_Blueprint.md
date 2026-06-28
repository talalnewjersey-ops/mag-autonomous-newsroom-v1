# NEXUS-14 Enterprise V5 — Recovery Blueprint

> Document d'ingénierie. Plan de correction exécutable fondé sur le rapport forensique (10 RCA). Priorité d'arbitrage : QUALITÉ > COÛT > DÉBIT.
> Statut : approuvé. Implémentation par sprints, un sprint à la fois.

## DÉFINITION "PUBLICATION-READY" (critères binaires machine-vérifiables)

- PR-01 Pipeline unique et documenté (un workflow planifié, un script d'entrée).
- PR-02 Portes 12/13 capables de bloquer (exit non-zéro propagé).
- PR-03 Rédaction par Claude Sonnet (Haiku interdit pour la rédaction).
- PR-04 Revue éditoriale par un PASS Sonnet DISTINCT, sur l'article entier.
- PR-05 EEAT jugé réellement (pas par comptage de mots-clés regex).
- PR-06 Anti-répétition inter-sections vérifié.
- PR-07 Pas de fuite de frontmatter YAML dans le rendu.
- PR-08 Fact-check réel via search_service (heuristique interdite si recherche dispo).
- PR-09 Images générées et bloquantes (pas best-effort).
- PR-10 Supervision humaine obligatoire avant publication (status=draft, jamais d'auto-publish).
- PR-11 Sujets diversifiés (registry persistant, refus si similarité > seuil).
- PR-12 Conformité Wise + AdSense/YMYL bloquante.

## PARTIE 1 — TRIAGE DES COMPOSANTS

| Composant | Fichier | Décision | Preuve | Action | Risque si rien |
|---|---|---|---|---|---|
| Workflow agents | .github/workflows/production_v2.yml | MODIFY | FIX 4 "3 gates only", 12/13 en \|\| true | unifier, rendre 12/13 bloquants | double pipeline |
| Script monolithique | scripts/produce_article.py | REMOVE (du chemin) | v8.2, Agent 24 self-review | retirer des workflows planifiés | bifurcation |
| Gate prod | scripts/production_gate.py | MODIFY | "3-GATE MINIMUM" | étendre aux portes réelles | qualité non contrôlée |
| QA | agents/agent_12_quality_assurance.py | MODIFY | overall_pass = passes_words ; sys.exit(0) | exit(1) conditionnel | ne bloque jamais |
| Chief Editor | agents/agent_13_chief_editor.py | MODIFY | if passes_words -> READY_TO_PUBLISH ; sys.exit(0) | exit(1) conditionnel | publie au compte de mots |
| Writer | agents/agent_04_article_writer.py | MODIFY | model=claude-haiku-4-5 ; sections isolées ; header YAML | Sonnet + prompt unifié | qualité faible |
| Fact checker | agents/agent_05_fact_checker.py | MODIFY | _heuristic_verify() | recherche réelle | fact-check factice |
| EEAT validator | agents/agent_06_eeat_validator.py | REWRITE | EEAT_SIGNALS regex | jugement Sonnet | théâtre EEAT |
| SEO/topics | agents/agent_01_seo_research.py | REWRITE | BUILTIN_TOPIC_DATABASE hardcodé | moteur registry 3-axes | sujets répétés |
| Orchestrateur | orchestrator/orchestrator.py | REMOVE | jamais importé | archiver/supprimer | code mort |
| Gate 18 | scripts/v2_quality_gate.py | REMOVE | jamais appelé | supprimer | confusion |
| Images | agents/agent_10_image_production.py | MODIFY | provider gemini | rendre bloquant | images manquantes |
| WordPress | agents/agent_11_wordpress_integration.py | MODIFY | MD->HTML, fuite YAML | nettoyer + draft only | publication crue |

## PARTIE 2 — CORRECTIFS PRIORITAIRES PAR RCA

- RCA-001 Pipeline réel != documenté (3 gates). Décision : unifier sur un seul workflow planifié.
- RCA-002 EEAT/scoring = théâtre de mots-clés. Décision : remplacer regex par jugement Sonnet + search réel.
- RCA-003 Downgrade Haiku. Décision : agent_04 model=claude-sonnet (Sonnet courant).
- RCA-004 Écriture par sections isolées -> répétition. Décision : revue sur l'article entier + porte anti-répétition.
- RCA-005 Agents 12/13 ne peuvent pas bloquer (sys.exit(0)). Décision : exit(1) conditionnel + retrait \|\| true.
- RCA-006 Self-review Agent 24 invalide. Décision : reviewer distinct (Agent 19 Sonnet).
- RCA-007 Fuite frontmatter YAML. Décision : MD sans frontmatter, métadonnées en meta.json.
- RCA-008 Double pipeline. Décision : neutraliser produce_article.py des workflows planifiés.
- RCA-009 Gate v2_quality_gate.py jamais appelé. Décision : supprimer.
- RCA-010 Orchestrateur mort. Décision : supprimer/archiver.

## PARTIE 3 — PIPELINE CIBLE UNIFIÉ

Un seul workflow planifié (production_v5.yml à terme ; production_v2.yml durci en transition), un seul script d'entrée. produce_article.py et orchestrator.py hors du chemin planifié. Séquence : SEO/topics -> validation -> plan -> rédaction Sonnet -> fact-check réel -> EEAT Sonnet -> liens/affiliation -> images bloquantes -> conversion HTML sans YAML -> revue Sonnet distincte (article entier) -> QA bloquant -> Chief Editor bloquant -> quality_gate_v5 -> revue humaine (draft -> publish). Aucune publication 100% automatique.

## PARTIE 4 — PORTES QUALITÉ RÉELLES

Principe : une porte ne mesure JAMAIS une chaîne que le writer a reçu l'ordre d'insérer.
- G1 Structure (H1 unique, >=3 H2, pas de YAML résiduel).
- G2 Longueur réelle : STANDARD >= 1500, PILLAR >= 3000 (deux tiers).
- G3 Anti-répétition (similarité inter-sections).
- G4 Fact-check réel via search_service.
- G5 EEAT réel jugé par Sonnet (remplace regex).
- G6 ADN éditorial jugé par Agent 19.
- G7 Images (>=1, alt non vide).
- G8 Affiliation Wise.
- G9 AdSense/YMYL.

## PARTIE 5 — ARCHITECTURE DES PROMPTS

Source unique system_prompt_writer ; format intermédiaire Markdown SANS frontmatter ; métadonnées en meta.json ; writer n'émet jamais de HTML ; versioning prompt + prompt_hash loggé ; reviewer (Agent 19) a son propre prompt distinct.

## PARTIE 6 — SPÉCIFICATION ÉDITORIALE MESURABLE

Voix d'expertise 1re personne, ton direct, rythme varié, paragraphes <=4 phrases, storytelling d'ouverture, >=1 cas chiffré réel, tableaux comparatifs, arbres de décision, encarts avertissement, réponse à la question dans les 100 premiers mots, 2-4 liens internes pertinents, un seul CTA Wise divulgué.

## PARTIE 7 — STRATÉGIE ÉDITORIALE & MOTEUR DE SUJETS

7.0 UTILITÉ > MONÉTISATION > VOLUME. 7.1 BUILTIN_TOPIC_DATABASE hardcodé -> répétition. 7.2 Registry persistant data/topic_registry.json, refus si sim>0.80, matrice de catégories (>=3/jour), pondération 3 axes (0.5 utilité + 0.3 fraîcheur + 0.2 wise). 7.3 Axe news via search_service, bloqué par G4.

## PARTIE 8 — STACK TECHNIQUE IMPOSÉE

1. Rédaction = Claude Sonnet (Haiku interdit). 2. Revue = PASS Sonnet distinct sur article entier (Agent 19). 3. Images = Gemini, bloquant. 4. Supervision humaine obligatoire avant publication (status=draft). Arbitrage : QUALITÉ > COÛT > DÉBIT.

## PARTIE 9 — CADENCE DE PRODUCTION

Cible 6 excellents x 2/jour = 12/jour MAX (plafond, pas obligation). Mieux 4 excellents que 6 médiocres. On ne désactive jamais une porte pour atteindre le quota.

## PARTIE 10 — PORTE WISE (G8, bloquante)

Pertinence cross-border, originalité, divulgation, exactitude (chiffres datés vérifiés), pas de promesse trompeuse.

## PARTIE 11 — PORTE ADSENSE/YMYL (G9, bloquante)

Originalité (test "so what"), E-E-A-T réel, pas de conseil garanti, pages légales, anti scale-abuse, humanisation.

## ROADMAP EN SPRINTS

- Sprint 1 — Arrêter l'hémorragie : pipeline unique + portes 12/13 bloquantes + retrait produce_article.py du chemin planifié.
- Sprint 2 — Qualité rédaction : Sonnet writer + anti-répétition + prompt unifié.
- Sprint 3 — Revue éditoriale Sonnet distincte (Agent 19).
- Sprint 4 — Fact-check & EEAT réels.
- Sprint 5 — Moteur de sujets registry.
- Sprint 6 — Images bloquantes + revue humaine.
- Sprint 7 — Nettoyage code mort.

## CONTRÔLE FINAL

Pipeline unique OUI ; portes 12/13 bloquent OUI ; EEAT jugé réellement OUI ; rédaction Sonnet OUI ; revue humaine avant publication OUI ; sujets diversifiés OUI.

## PARTIE 12 — RAPPORT D'ACTIVITÉ

Diagnostic consolidé (10 RCA), définition publication-ready, triage, correctifs, pipeline unifié, portes réelles, prompts, ADN éditorial, moteur de sujets, stack imposée, cadence, portes Wise/AdSense, roadmap 7 sprints. Implémentation effective restante par sprint. À vérifier dans le repo lors de l'implémentation : internals agent_10 (Gemini), signature search_service, présence dossiers prompts/ et data/, callers réels de produce_article.py.
