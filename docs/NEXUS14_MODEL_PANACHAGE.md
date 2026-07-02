# NEXUS-14 — Panachage des modèles Claude

**Date :** 2026-07-02
**Statut :** Actif — appliqué sur `services/llm_service.py`, agents 01–04, `.env.example`
**Motivation :** minimiser le coût total (limite budget observée en PR #28 « credits exhausted ») tout en maximisant la qualité de sortie sur le seul agent où c'est critique (article writer, YMYL).

---

## 1. Principe

Le pipeline NEXUS-14 enchaîne 18 agents pour produire 6 articles/jour de 8 500–12 000 mots. Un modèle unique pour tous les agents est une erreur d'optimisation :

- **Fable 5 partout** → coût 2× Opus 4.8, tokens facturés à $10/$50 par MTok, budget grillé en <1 semaine.
- **Sonnet 5 partout** → qualité article insuffisante pour ranker sur des mots-clés YMYL (finance/immigration) où Google favorise fortement l'EEAT.

La règle : **le modèle le plus capable là où la sortie EST le produit, un modèle moins cher partout ailleurs.**

## 2. Panachage appliqué

| Agent | Rôle | Modèle par défaut | Var d'env | Justification |
|---|---|---|---|---|
| 01 SEO Research | Génère des sujets à partir de la SERP | `claude-sonnet-5` | `RESEARCH_MODEL` | Tâche structurée (JSON). Sonnet 5 = adaptive thinking on par défaut, meilleur que Haiku 4.5 pour le prix. |
| 02 Keyword Validation | Vérifie intent, volume, difficulté | `claude-sonnet-5` | `ANTHROPIC_MODEL` | Idem. |
| 03 Content Planner | Outline H2/H3, FAQ map | `claude-sonnet-5` | `OUTLINE_MODEL` | Idem. |
| **04 Article Writer** | Rédige 8 500–12 000 mots YMYL | **`claude-fable-5`** | `ARTICLE_WRITER_MODEL` | **La qualité de l'article EST le produit.** Ranking Google, EEAT, temps sur page. Le 2× de coût est justifié uniquement ici. |
| 05 Fact Checker | Vérifie sources gouvernementales live | `claude-opus-4-8` | `FACT_CHECK_MODEL` | Comparaison texte ↔ URL live. Opus 4.8 largement suffisant. |
| 06 EEAT Validator | Juge crédibilité, auteur, sources | **`claude-fable-5`** | `EEAT_MODEL` | Jugement fin. Une validation faible = article sous-standard publié. |
| 07 Internal Linking | Sélection de liens internes | (via LLMService) | `ANTHROPIC_MODEL` | Sonnet 5 par défaut. |
| 08 Affiliate Optimizer | Placement des CTAs | (via LLMService) | `ANTHROPIC_MODEL` | Idem. |
| 09 Image Prompt Generator | Génère les prompts d'images | (via LLMService) | `ANTHROPIC_MODEL` | Idem. |
| 10 Image Production | Gemini API (pas Claude) | — | `GEMINI_API_KEY` | — |
| 11 WordPress Integration | REST API WordPress | — | — | — |
| 12 QA | Grille de 18 gates | `claude-opus-4-7` | `QA_MODEL` | Décisions rigoureuses mais structurées. |
| 13 Chief Editor | Décision READY_TO_PUBLISH | `claude-opus-4-7` | `EDITOR_MODEL` | Idem. |
| 14 Production Director | Rapports morning/executive HTML | `claude-haiku-4-5` | `REPORTING_MODEL` | Templating. Le tier le moins cher suffit. |
| 15 Affiliate Compliance | Vérif FTC disclosure | (via LLMService) | `ANTHROPIC_MODEL` | Sonnet 5 par défaut. |
| 16 Publishing Optimization | Metadata Rank Math | (via LLMService) | `ANTHROPIC_MODEL` | Idem. |
| 17 Cannibalization | Dedup sujets | (via LLMService) | `ANTHROPIC_MODEL` | Idem. |
| 18 Revenue Intelligence | Score revenue | (via LLMService) | `ANTHROPIC_MODEL` | Idem. |

## 3. Coût estimé (ordres de grandeur)

Pour 1 article Gold Standard (~15 appels LLM, ~120 000 tokens totaux entrée+sortie) :

| Configuration | Coût article | Coût 6 articles/jour | Coût 30 jours |
|---|---|---|---|
| Tout en Fable 5 | ~$4.80 | ~$28.80 | ~$864 |
| Tout en Opus 4.8 | ~$2.40 | ~$14.40 | ~$432 |
| Tout en Sonnet 5 | ~$1.44 | ~$8.64 | ~$259 |
| **Panachage v2** | **~$1.80** | **~$10.80** | **~$324** |

Le panachage v2 est **1,25× le coût du tout-Sonnet-5** mais avec la qualité article de Fable 5 uniquement là où ça compte (writer + EEAT), soit environ **62 % moins cher que tout-Fable-5**.

## 4. Breaking changes du nouveau line-up Anthropic

Le code a été mis à jour pour tenir compte des breaking changes suivants (sinon → 400) :

| Sujet | Ancien | Nouveau | Action code |
|---|---|---|---|
| `temperature` / `top_p` / `top_k` | Accepté | **Rejeté (400)** sur Fable 5, Opus 4.7/4.8, Sonnet 5 | `services/llm_service.py` ne passe plus `temperature` pour ces modèles. |
| `thinking: {type: "enabled", budget_tokens: N}` | Requis pour activer | **Rejeté (400)** | Non utilisé dans ce code. |
| `thinking: {type: "disabled"}` sur Fable 5 | — | **Rejeté (400)** | On ometter le champ entièrement. |
| Assistant prefill (last-turn) sur Fable 5 | Accepté | **Rejeté (400)** | Aucun prefill dans ce code. |
| ZDR (Zero Data Retention) sur Fable 5 | Fonctionne | **400 sur toute requête** | Fallback vers `claude-opus-4-8` si ton org est en ZDR. |
| `stop_reason == "refusal"` sur Fable 5 | Rare | Possible (classificateurs cyber/bio/reasoning_extraction/frontier_llm) | `agent_04` active `fallbacks: [{"model": "claude-opus-4-8"}]` + beta `server-side-fallback-2026-06-01`. |

## 5. Prérequis org Anthropic

Vérifier avant déploiement :

1. **Data retention >= 30 jours** sur l'organisation Anthropic (Console → Settings → Data Retention). Sinon Fable 5 renvoie 400 sur chaque requête et le writer échoue.
2. **Rate limits Fable 5** : Fable 5 est facturé au tarif Fable, mais partage-t-il le même pool que Opus ? Vérifier dans la Console. Pour 6 articles/jour × ~20 appels writer, prévoir un tier suffisant.
3. **Fallback Opus 4.8 rate limit** : quand un refusal Fable 5 déclenche le fallback, l'appel bascule sur Opus 4.8 et consomme sa rate limit. Prévoir de la marge.

## 6. Comment revenir en arrière

Si Fable 5 pose problème (coût, refusals, ZDR), unset la variable ou la remettre :

```bash
# Option A — Writer sur Opus 4.8 (moins cher, ZDR-compatible)
export ARTICLE_WRITER_MODEL=claude-opus-4-8
export EEAT_MODEL=claude-opus-4-8

# Option B — Tout sur Sonnet 5 (cheapest coherent option)
export ARTICLE_WRITER_MODEL=claude-sonnet-5
export EEAT_MODEL=claude-sonnet-5
export FACT_CHECK_MODEL=claude-sonnet-5
export QA_MODEL=claude-sonnet-5
export EDITOR_MODEL=claude-sonnet-5
```

Aucune variable n'est required — les defaults dans le code prennent le relais.

## 7. Fichiers modifiés

- `.env.example` — nouvelles variables + docs des breaking changes
- `services/llm_service.py` — retrait de `temperature` sur nouveau line-up, default Sonnet 5 + fallback Opus 4.8
- `agents/agent_01_seo_research.py` — default Sonnet 5, fallback Opus 4.8
- `agents/agent_02_keyword_validation.py` — idem
- `agents/agent_03_content_planner.py` — CLAUDE_MODELS reconstruit depuis env, Sonnet 5 primary
- `agents/agent_04_article_writer.py` — default `claude-fable-5`, activation `fallbacks` + beta `server-side-fallback-2026-06-01`, safe parsing (skip thinking blocks), refusal guard
- `docs/NEXUS14_MODEL_PANACHAGE.md` — ce document

## 8. Prochaines étapes recommandées

1. **Tester en dry-run** : lancer le workflow `production_v2.yml` sur un seul sujet et vérifier que le writer produit bien un article via Fable 5 (regarder `x-ratelimit-*` headers, coût estimé, longueur produite).
2. **Comparer 2 articles côte à côte** — un avec `ARTICLE_WRITER_MODEL=claude-fable-5` et un avec `claude-opus-4-8` sur le même sujet — pour valider que le gain qualitatif justifie le 2× de coût. Si non, retomber sur Opus 4.8.
3. **Aligner le seuil `TIER_MIN_WORDS`** dans `agents/agent_12_quality_assurance.py` (actuellement `STANDARD=1500`) sur la Directive NEXUS-14 (`STANDARD=3500`, `PILLAR=7000`, `Gold=8500`) — audit compliance précédent.
