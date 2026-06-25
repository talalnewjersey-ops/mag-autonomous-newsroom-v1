# NEXUS-14 V4 Enterprise — Implementation Guide

> Branch: `feature/nexus14-v4-enterprise` · Status: implementation-ready, NOT merged, NOT deployed.
> Describes the V4 redesign delivered on this branch and the steps an engineer must
> complete (CI, staging, migration) before merging to `main`.
>
> See also: `docs/NEXUS14_V4_MERGE_CHECKLIST.md` for the full migration + production
> deployment checklist and the known-technical-debt log.

## 1. Why V4

V4 eliminates four classes of defect at the source:

1. **Duplicate JSON-LD** — Yoast becomes the single schema authority. Agent 11 no
longer emits JSON-LD, no longer writes Rank Math meta, and a body-schema guard
blocks publication if any `application/ld+json` appears in the post body.
2. **AI footprint** — Originality Engine (Agent 19) blocks templated/duplicated sections,
and the Writer V4 layer regenerates only the flagged sections free of banned patterns.
3. **Cannibalization** — Agent 17 is a blocking, embedding-based semantic engine.
4. **Inaccurate YMYL** — YMYL Validator (Agent 20) binds regulated figures to an
official-source registry and records effective + verification dates.

The **Quality Gate V4** is the authoritative publication decision: it independently
recomputes every critical signal instead of trusting upstream agent reports.

## 2. Components delivered on this branch

New services: `services/schema_fields.py`, `services/embeddings_service.py`,
`services/content_similarity.py`, `services/eeat_enrichment.py`,
`services/writer_variation.py` (Writer V4 variation/regeneration; SSOT banned patterns).

Agents:
- `agents/agent_11_wordpress_integration.py` — REFACTORED (Yoast-only, FAQ blocks, body-schema guard, Rank Math removed).
- `agents/agent_17_cannibalization.py` — REWRITTEN (semantic, blocking by default).
- `agents/agent_19_originality.py` — NEW (originality engine).
- `agents/agent_20_ymyl_validator.py` — NEW (YMYL validator).
- `agents/agent_22_performance.py` — NEW interface (Lighthouse/CWV; blocks on missing measurement).
- `agents/agent_23_competitor.py` — NEW interface (information gain; blocks on missing data).
- `agents/agent_04_writer_v4.py` — NEW (Writer V4 regeneration loop: draft -> originality -> variation -> verify; wraps the existing Agent 04 generator).

Scripts: `scripts/quality_gate_v4.py` (authoritative gate), `scripts/migrate_schema.py` (audit/dry-run/commit/rollback).

Config: `config/cannibalization.yaml`, `config/ymyl_sources.yaml`.

Tests: `tests/test_v4_pipeline.py` (written; run in CI).

CI: `.github/workflows/v4-tests.yml` runs the suite on push + PR across Python 3.10–3.12.

## 3. New configuration / environment variables

| Variable | Default | Purpose |
|---|---|---|
| `EMBEDDINGS_PROVIDER` | `hashing` | embedding backend: hashing / openai / voyage |
| `OPENAI_API_KEY` | (unset) | required only if provider=openai |
| `VOYAGE_API_KEY` | (unset) | required only if provider=voyage |
| `AGENT17_OBSERVE_ONLY` | `false` | V4 blocks by default; set true ONLY in staging |

The default hashing backend is deterministic and needs no network, so the pipeline
and tests run with zero new external dependencies or cost.

## 4. Feature flags

- `AGENT17_OBSERVE_ONLY=true` — cannibalization in measure-only mode (staging).
- Schema migration gated behind explicit `--commit --yes`; default is `--audit`.
- Rank Math deactivation is a WordPress admin action (NOT automated by this branch).

## 5. CI commands (still need to be executed)

```bash
pip install pytest pyyaml
# Repo root must be importable; hashing backend keeps tests offline + deterministic.
PYTHONPATH=. EMBEDDINGS_PROVIDER=hashing pytest tests/test_v4_pipeline.py -v
python -m agents.agent_19_originality --input draft.md --corpus-dir output/published_corpus
python -m agents.agent_17_cannibalization --topic "TFSA for newcomers" --keywords "tfsa,newcomers" --slug tfsa-newcomers
python -m agents.agent_20_ymyl_validator --input draft.md
python scripts/quality_gate_v4.py --article draft.md --rendered rendered.html --meta meta.json --corpus-dir output/published_corpus
python scripts/migrate_schema.py --audit
python scripts/migrate_schema.py --dry-run --limit 50
python scripts/migrate_schema.py --commit --yes --limit 25
python scripts/migrate_schema.py --rollback --yes
```

## 6. Migration & rollback (staging only)

1. `--audit`; review `output/migration/schema_migration_report.json`.
2. `--dry-run`; confirm per-post diffs.
3. `--commit --yes --limit N` in small batches; each post snapshotted to
`backups/schema_migration/<id>.json` BEFORE write.
4. Validate with Google Rich Results Test (exactly one schema graph).
5. `--rollback --yes` restores from snapshots if needed.
6. Deactivate Rank Math in WordPress admin (manual) once Yoast output confirmed.

## 7. Staging validation checklist (before merge to main)

- [ ] `pytest tests/test_v4_pipeline.py` passes in CI.
- [ ] Every new module imports cleanly.
- [ ] Agent 11 draft has zero body JSON-LD.
- [ ] Rich Results Test shows exactly one schema graph on a migrated sample.
- [ ] Agent 17 blocks a duplicated topic (non-zero exit).
- [ ] Agent 19 flags a templated intro for regeneration.
- [ ] Writer V4 loop regenerates flagged sections free of banned openers.
- [ ] Agent 20 fails an article with an incorrect TFSA/IRS figure.
- [ ] Quality Gate V4 returns BLOCKED when any required check fails.
- [ ] Agent 22 / 23 report PENDING until real measurement/data supplied.
- [ ] Schema migration audited + dry-run reviewed; rollback tested on staging.

## 8. Known risks / assumptions

- Runtime-dependent gates (Agent 22 Lighthouse, Agent 23 SERP) are interfaces;
they intentionally BLOCK (PENDING) until CI supplies real data.
- Default hashing embeddings are lexical, not semantic; set a real provider for
production semantic accuracy.
- Writer V4 section regeneration calls the Anthropic API; the loop CONTROL logic is
tested offline, but real regeneration runs only where `ANTHROPIC_API_KEY` is set.
- YMYL registry values must be updated yearly when CRA/IRS publish new figures.
- Schema migration mutates live post content; run staging-first with snapshots.
- Rank Math deactivation and plugin/permission changes are manual admin actions.
- See `NEXUS14_V4_MERGE_CHECKLIST.md §8` for outstanding code-consistency debt.

## 9. Merge readiness

| Gate | State |
|---|---|
| Code review | READY |
| CI (tests) | READY to run — NOT yet executed |
| Staging validation | PENDING (section 7) |
| Production | NOT ready — requires staging sign-off + migration + Rank Math deactivation |

Do not merge or deploy until sections 6-7 are complete and CI is green.
