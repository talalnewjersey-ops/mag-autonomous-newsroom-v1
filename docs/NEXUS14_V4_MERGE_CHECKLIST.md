# NEXUS-14 V4 — Migration & Production Deployment Checklist

Branch: `feature/nexus14-v4-enterprise`
Scope: pre-merge readiness for the V4 publishing-pipeline redesign.
Status legend: [ ] not started  ·  [~] ready to run (not executed)  ·  [x] done

> This document is authoritative for *how to ship* V4. It does not assert that
> any runtime step has been executed. Commands below still need to be run by a
> human / CI. No merge or deploy has been performed.

---

## 1. Branch / Code Review readiness

- [x] All P1–P6 core components implemented (schema SSOT, cannibalization,
      originality, YMYL, Quality Gate V4, regression tests).
- [x] Writer V4 variation + regeneration loop implemented
      (`services/writer_variation.py`, `agents/agent_04_writer_v4.py`).
- [x] Cross-module imports verified by reading every module; the Quality Gate
      imports resolve against agent_17 / agent_19 / agent_20 / services.
- [x] Regression tests cover schema, originality, cannibalization, YMYL, gate,
      migration, writer-variation, performance, competitor, EEAT.
- [x] CI workflow added (`.github/workflows/v4-tests.yml`).
- [ ] Open a Pull Request from `feature/nexus14-v4-enterprise` into `main` and
      request review. (Performed by a human — Claude does not open/merge PRs.)

## 2. Continuous Integration (run, do not assume)

- [~] CI runs `pytest tests/test_v4_pipeline.py -v` on push + PR (3 Python
      versions). Tests are WRITTEN but have NOT been executed here.
- [~] Smoke-import step imports all V4 modules.
- [ ] Confirm the Actions run is green before merge. If red, fix before merge.

Local equivalent:

```
pip install pytest pyyaml
PYTHONPATH=. EMBEDDINGS_PROVIDER=hashing pytest tests/test_v4_pipeline.py -v
```

## 3. Schema migration (existing WordPress posts)

`scripts/migrate_schema.py` is conservative: audit by default, snapshot before
every write, `--yes` required for mutation, full rollback supported.

- [ ] Backup: confirm a recent full DB/content backup exists independently.
- [~] Audit (read-only):

```
python scripts/migrate_schema.py --audit --output output/migration/audit.json
```

- [~] Dry-run the diff on a small batch:

```
python scripts/migrate_schema.py --dry-run --limit 25
```

- [ ] Commit a small batch with snapshots, smallest-traffic first:

```
python scripts/migrate_schema.py --commit --yes --limit 25 \
  --snapshot-dir backups/schema_migration
```

- [ ] Verify migrated posts render exactly one schema graph (Google Rich Results
      Test / Yoast) and contain zero body `application/ld+json`.
- [ ] Roll back immediately if any regression:

```
python scripts/migrate_schema.py --rollback --yes --snapshot-dir backups/schema_migration
```

- [ ] Scale up batch size only after a clean verified batch.

## 4. Rank Math → Yoast cutover (manual admin actions)

- [ ] Confirm Yoast SEO is installed, active, and configured as the schema source.
- [ ] Deactivate Rank Math schema output (admin action — NOT automatable here).
- [ ] Confirm no plugin emits a second Article/FAQPage graph.
- [ ] Spot-check 5 representative posts for a single, valid @graph.

## 5. Runtime gates (must be measured, never faked)

- [ ] Provide a real Lighthouse JSON to Agent 22 so performance is PASS/FAIL,
      not PENDING:

```
npx lighthouse <staging-url> --output=json --output-path=lh.json \
  --only-categories=seo,performance,accessibility,best-practices
python agents/agent_22_performance.py --lighthouse-json lh.json
```

- [ ] Provide a real competitor corpus (SERPAPI) to Agent 23:

```
python agents/agent_23_competitor.py --input draft.md --competitors competitors.json
```

- [ ] Run the authoritative Quality Gate; publication requires exit 0:

```
python scripts/quality_gate_v4.py --article draft.md --rendered draft.html \
  --meta meta.json --performance-report output/agent_22/performance_report.json \
  --competitor-report output/agent_23/competitor_report.json
```

## 6. Staging validation

- [ ] Produce 1 article end-to-end on staging through the V4 pipeline.
- [ ] Confirm Quality Gate V4 independently recomputes and BLOCKS on any failure.
- [ ] Confirm Agent 17 blocks duplicates by default (`AGENT17_OBSERVE_ONLY` unset).
- [ ] Confirm exactly one schema graph; zero body JSON-LD; valid FAQ via Yoast.
- [ ] Confirm originality loop differentiates flagged sections (no banned openers).

## 7. Production deployment

- [ ] Merge only after: CI green + staging article passes the gate + migration
      verified on a sample. (Merge performed by a human.)
- [ ] Set env: `EMBEDDINGS_PROVIDER` (`hashing` default, or `openai`/`voyage` with key).
- [ ] Keep `AGENT17_OBSERVE_ONLY` unset/false in production (blocking ON).
- [ ] Run schema migration in production in small, snapshotted batches.
- [ ] Monitor Search Console for schema errors for 48h post-migration.
- [ ] Keep `backups/schema_migration` snapshots until verified stable.

## 8. Known technical debt (carry into follow-up PRs)

- `agents/agent_11_wordpress_integration.py`: in `_load_article_data` the
  frontmatter regexes use `s*` instead of `\\s*`, so the in-agent title/keyword
  extraction fallback silently no-ops (the `main()` path uses the correct `\\s*`
  and the outline provides a title fallback, so impact is limited). Fix to
  `\\s*`. Not changed here to avoid a risky full-file rewrite of a working
  integration agent.
- `agent_11` report payloads still emit `"version": "3.0"` while the class is
  documented as v4.0. Align to `4.0` for consistency.
- EEAT element sets differ: `eeat_enrichment.REQUIRED_ELEMENTS` (8 elements)
  is a superset of `quality_gate_v4.THRESHOLDS["eeat_required_elements"]` (6).
  Reconcile the two lists (or document the gate as a deliberate subset).
- Agent 22 (performance) and Agent 23 (competitor) are honest interfaces:
  they emit PENDING/passed=false until real Lighthouse/SERP data is supplied.
  Implement the CI integration points before relying on these gates.
