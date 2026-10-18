# Word Count Reconciliation — Canonical Source of Truth

**Status:** DRAFT recommendation (Priority 4). Refs Issue #4. Do not merge / do not deploy.

## 1. Problem

Three configuration sources disagree on per-tier word counts. This causes
the Article Writer (Agent 04) and the quality gates to target different
lengths depending on which file a component reads.

### Observed values (as of this analysis)

| Source | Version / Date | PILLAR (min/target/max) | STANDARD (min/target/max) | OPPORTUNITY (min/target/max) |
|---|---|---|---|---|
| `config/article_strategy.json` | v3.0.0 / 2026-06-12 | 7000 / 9000 / 12000 | 3500 / 5500 / 7000 | *(tier absent)* |
| `config/nexus14_v2_config.yaml` | v3.1.0 / 2026-06-14 | 4500 / 5000 / 5000 | 4000 / 4500 / 4500 | 3500 / 4000 / 4000 |
| `quality_gates` (inside the YAML) | v3.1.0 | min 4500 (override) | min 4000 (default) | min 3500 (override) |
| Agent 04 `tiers` (inside the YAML) | v3.1.0 | 4500 / – / 5000 | 4000 / – / 4500 | 3500 / – / 4000 |

### Key findings
- `nexus14_v2_config.yaml` (v3.1.0) is the **newest** file and is **internally consistent**: its content tiers, `quality_gates`, Agent 04 `tiers`, image tiers, and `max_words_absolute: 5000` all agree.
- `article_strategy.json` is the **older** v3.0.0 file. It still encodes the legacy long-form strategy (PILLAR up to 12000) and **does not define an OPPORTUNITY tier** at all. It is the sole outlier.
- The YAML values already match the requested target ranges.

## 2. Recommendation — Canonical Source of Truth

**Adopt `config/nexus14_v2_config.yaml` (v3.1.x) as the single canonical source of truth for word counts and tier thresholds.** Reasons:

1. It is the newest version (3.1.0 supersedes 3.0.0).
2. It is internally consistent across content tiers, quality gates, Agent 04, and images.
3. It already defines all three tiers (PILLAR / STANDARD / OPPORTUNITY).
4. Its values match the requested target ranges (see below).

`article_strategy.json` should be **reduced to classification logic only** (which signals map a topic to PILLAR/STANDARD/OPPORTUNITY) and should **reference**, not duplicate, the canonical word counts — or, as an interim step, be updated to mirror the YAML exactly so no component reads stale numbers.

### Requested target ranges (confirmed match)

| Tier | Requested | Canonical YAML | Match |
|---|---|---|---|
| PILLAR | 4500–5000 | min 4500 / max 5000 | yes |
| STANDARD | 4000–4500 | min 4000 / max 4500 | yes |
| OPPORTUNITY | 3500–4000 | min 3500 / max 4000 | yes |

## 3. Proposed change in this PR

Update `config/article_strategy.json` so its `requirements.word_count_*` values align with the canonical YAML and add the missing OPPORTUNITY tier. No code is changed; this only removes the stale numbers so every reader converges on the same targets.

## 4. Tradeoffs (documented before implementation)

- **Shorter PILLAR (12000 → 5000 max).** Pro: lower cost per article, faster production, matches "search intent > length" philosophy and `max_words_absolute: 5000`. Con: for a few highly competitive head terms, 5000 words may be less comprehensive than top-ranking 6000–8000-word competitors; topical authority for those specific terms may rely more on internal-linking depth and cluster coverage than single-article length. **Mitigation:** monitor rankings for the most competitive PILLAR terms; the cap is a default, and a documented exception process can raise the max for a named short-list of head terms if data shows length is the gap.
- **Higher STANDARD floor (3500 → 4000 min).** Pro: more thorough mid-competition articles, better EEAT. Con: marginally higher cost per STANDARD article.
- **Adding OPPORTUNITY tier to the JSON.** Pro: removes the silent gap where the JSON had no tier for low-difficulty/low-revenue topics; aligns the JSON with the agents that already emit OPPORTUNITY.
- **Single source of truth.** Pro: eliminates drift and ambiguous behavior. Con: every component must read the canonical file; any component still hard-reading the JSON must be pointed at aligned values (this PR keeps the JSON aligned precisely to avoid breakage).

## 5. Out of scope / not changed
- No quality-gate thresholds are lowered. EEAT (≥90), SEO (≥90), originality, sources, and FAQ minimums are unchanged.
- `max_articles_per_day` stays at 6 (a ceiling, never a quota — see Priority 5).
- This PR is **warning/recommendation + config alignment only**; no deployment.
