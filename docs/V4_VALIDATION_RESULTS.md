# NEXUS-14 V4 — Offline Validation Results

This document records the **real CI execution evidence** for the V4 decision
core. Every result below was produced by GitHub Actions on the
`feature/nexus14-v4-enterprise` branch. Nothing here is estimated, simulated,
or hand-written from assumptions — each figure is copied from an actual
workflow run log.

## Scope and guarantees

- **Offline & deterministic.** All runs force `EMBEDDINGS_PROVIDER=hashing`, so
  no API keys and no network access are required.
- **No external writes.** The validation makes **no WordPress writes**, **no
  OpenAI calls**, and runs no live schema migration.
- **No merge / no deploy.** This work lives entirely on the feature branch.
- **Runtime gates are honestly PENDING.** The authoritative Quality Gate always
  consults the performance (Agent 22 / Lighthouse) and competitor (Agent 23 /
  SERP) reports. Offline those reports are absent, so a fully content-clean
  article is correctly **BLOCKED** with `failed_gates == {performance,
  competitor}` and **zero** content-gate failures. This is by design, not a
  defect.

## How to reproduce locally

```
EMBEDDINGS_PROVIDER=hashing PYTHONPATH=. pytest tests/ -v
EMBEDDINGS_PROVIDER=hashing PYTHONPATH=. python scripts/validate_v4_pipeline.py
```

## CI evidence (real runs)

| Run | Commit | Workflow | Result | Evidence |
| --- | ------ | -------- | ------ | -------- |
| Validation Harness #2 | `48e1e37` | `validate-v4.yml` | Success | `ALL_EXPECTED: True`; `wordpress_contacted: False`; `openai_contacted: False` |
| V4 Pipeline Tests #10 | `85d64c2` | `v4-tests.yml` | Success | `55 passed` on Python 3.10 / 3.11 / 3.12 |
| V4 Pipeline Tests #11 | `e09d104` | `v4-tests.yml` | Success | `73 passed` on Python 3.10 / 3.11 / 3.12 |

The pytest suite grew across phases as coverage was added:

| Phase | Added | Collected total |
| ----- | ----- | --------------- |
| Baseline (M10 module suite) | `tests/test_v4_pipeline.py` | 37 |
| Phase A (decision-core regression) | `tests/test_v4_validation_harness.py` | 55 |
| Phase B (failure matrix) | `tests/test_v4_failure_matrix.py` | 73 |

## Decision matrix — what was verified

The figures below were emitted by the offline harness
(`scripts/validate_v4_pipeline.py`) and corroborated by the pytest suites.

### Agent 17 — Cannibalization (decision bands)

Composite-overlap bands: `< 0.55` ALLOW, `< 0.72` HUMAN_REVIEW, `< 0.85` MERGE,
`>= 0.85` BLOCK. Decision logic verified across the full band range:

| Composite | Decision | Blocking |
| --------- | -------- | -------- |
| 0.00 | ALLOW | no |
| 0.54 | ALLOW | no |
| 0.55 | HUMAN_REVIEW | yes |
| 0.71 | HUMAN_REVIEW | yes |
| 0.72 | MERGE | yes |
| 0.84 | MERGE | yes |
| 0.85 | BLOCK | yes |
| 0.99 | BLOCK | yes |

Empty corpus -> ALLOW (max_composite 0.0, non-blocking). A near-duplicate
existing post -> a non-ALLOW, blocking decision.

### Agent 19 — Originality

| Input | Score | Passed | Notes |
| ----- | ----- | ------ | ----- |
| Clean article | 100.0 | yes | no violations, no sections to regenerate |
| Bad article | < 100 | no | violations include banned opener + emoji heading |

### Agent 20 — YMYL

| Input | Status | Notes |
| ----- | ------ | ----- |
| Clean article | PASS | 0 contradicted, 0 unverifiable |
| "TFSA limit is $99,999" | FAIL | contradicts the registry reference value |

### Quality Gate V4 — authoritative decision

| Article | Decision | Content-gate failures | Runtime-gate failures |
| ------- | -------- | --------------------- | --------------------- |
| Clean | BLOCKED | none | performance, competitor (PENDING offline) |
| Bad | BLOCKED | schema, eeat, formatting, accessibility, internal_links, originality | performance, competitor |

## Failure matrix (certification Phase 3)

Each defect is independently detected by the gate and blocks publication
(`tests/test_v4_failure_matrix.py`):

| Defect | Gate that blocks |
| ------ | ---------------- |
| Missing author (any required EEAT element) | `eeat` |
| Duplicate / broken canonical | `canonical_uniqueness` |
| Body JSON-LD (second schema source) | `schema` |
| Emoji heading | `formatting` |
| Image missing alt text | `accessibility` |
| Internal links below minimum | `internal_links` |
| Contradicted YMYL value | `ymyl` |
| Banned AI opener / emoji heading | `originality` |

## Known non-blocking warning

CI emits a Node 20 deprecation notice for `actions/checkout@v4`,
`actions/setup-python@v5`, and `actions/upload-artifact@v4` (GitHub is forcing
Node 24). This does not affect test results and is tracked as low-priority
maintenance.

## Still pending (not validated here, by design)

- Performance gate (Agent 22 / Lighthouse) and competitor gate (Agent 23 /
  SERP) require real runtime measurements supplied from staging.
- The full generation -> WordPress orchestrator is out of scope for this
  offline validation.
- EEAT consistency reconciliation remains deferred as post-validation
  technical debt.
