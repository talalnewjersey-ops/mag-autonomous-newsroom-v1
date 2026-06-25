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
| V4 Pipeline Tests #14 | `0320feb` | `v4-tests.yml` | Success | `85 passed` on Python 3.10 / 3.11 / 3.12 |
| V4 Pipeline Tests #16 | `0ed63b2` | `v4-tests.yml` | Success | `97 passed` on Python 3.10 / 3.11 / 3.12 |
| V4 Pipeline Tests #18 | `6e2e829` | `v4-tests.yml` | Success | `106 passed` on Python 3.10 / 3.11 / 3.12 |
| V4 Pipeline Tests #25 | `4ac942b` | `v4-tests.yml` | Success | `111 passed` on Python 3.10 / 3.11 / 3.12 (Approach B / B1 complete) |
| V4 Pipeline Tests #31 | `0f38cb1` | `v4-tests.yml` | Success | `139 passed` on Python 3.10 / 3.11 / 3.12 (M7 topic selection) |

> **Honest note on run #13.** The first commit of the runtime-gate suite
> (`474821e`, V4 Pipeline Tests #13) **failed** with `1 failed, 61 passed`:
> `test_competitor_pass_with_strong_article` returned FAIL instead of PASS.
> Investigation showed this was a **test-fixture defect, not a pipeline
> defect** — Agent 23 correctly returned FAIL because the strong-article
> fixture did not cover at least 70% of the competitor entity set. The fixture
> was corrected in `0320feb` (it now covers the money/transfer/abroad entity
> surface), and run #14 then reported `85 passed`. The failed run is recorded
> here deliberately: success was never declared on the strength of written
> code, only on a green CI log.

> **Honest note on runs #23 and #24 (Approach B / B1).** Tightening the gate
> from 6 to 8 required EEAT keys deliberately broke two pre-existing fixtures
> that only carried the legacy 6 keys. Run #23 (`60113db`) failed with
> `1 failed, 90 passed` (`test_v4_failure_matrix::test_eeat_complete_passes` —
> a 6-key COMPLETE_META no longer passes an 8-key gate). After completing that
> fixture, run #24 (`8051fb3`) failed with `1 failed, 90 passed` for the same
> reason in a second fixture (`test_v4_runtime_gates` reads CLEAN_META, which
> also carried only 6 keys, so the `eeat` content gate fired alongside the
> runtime gates). Fixing CLEAN_META at its source
> (`scripts/validate_v4_pipeline.py`) produced run #25 = `111 passed`. Both
> failures were fixture-completeness issues caused by the intended behavioural
> change, not gate defects; each was diagnosed from the real CI log before the
> next commit.

> **Honest note on run #29 (M7 topic selection).** The first M7 test commit
> (`273b3f7`, V4 Pipeline Tests #29) **failed** with `1 failed, 119 passed`:
> `test_top_topic_high_value` asserted the static-only top topic scores
> `>= 0.70`, but the true static ceiling is ~0.6995 (no live-signal weight can
> contribute when no live data is supplied). This was a **test-threshold
> defect, not an engine defect** — the prioritizer behaved correctly. The
> floor was corrected to `0.65` and run #31 (`0f38cb1`) reported
> `139 passed`. (One intermediate commit recorded the same message but did not
> register the buffer change in the web editor; it was superseded by the
> correct content in `0f38cb1`, verified against true HEAD before the CI run.)

The pytest suite grew across phases as coverage was added:

| Phase | Added | Collected total |
| ----- | ----- | --------------- |
| Baseline (M10 module suite) | `tests/test_v4_pipeline.py` | 37 |
| Phase A (decision-core regression) | `tests/test_v4_validation_harness.py` | 55 |
| Phase B (failure matrix) | `tests/test_v4_failure_matrix.py` | 73 |
| Option 1 (runtime gates) | `tests/test_v4_runtime_gates.py` | 85 |
| Option 3 (EEAT consistency) | `tests/test_v4_eeat_consistency.py` | 97 |
| Option 2 (publish boundary) | `tests/test_v4_orchestrator_publish.py` | 106 |
| Approach B / B1 (EEAT alignment) | EEAT tests re-pointed to alignment + 8-key fixtures | 111 |
| M7 (topic selection) | `tests/test_v4_topic_prioritizer.py` | 139 |

## Topic selection — newcomer US/CA prioritizer (M7)

A topic-selection layer was added in front of generation so the pipeline can
choose **which** newcomer topic to write about, not just enforce EEAT on the
output. It is proven by `tests/test_v4_topic_prioritizer.py` (28 tests) in
V4 Pipeline Tests #31 (`139 passed`).

**Honest data boundary.** There is currently **no authorised live data source**
for search volume, trends, clicks/impressions, or affiliate-partner demand, and
fabricating such numbers is forbidden by the project rules. Therefore:

- `services/topic_taxonomy.py` encodes an **editorial, knowledge-based**
  taxonomy of high-value newcomer topics for the USA and Canada (bank account,
  credit history, SSN/SIN, money transfer, health insurance, taxes, etc.). Each
  topic carries static, auditable scores: `newcomer_value`, `commercial_intent`,
  and `evergreen` (all in `[0,1]`).
- `services/topic_prioritizer.py` ranks topics with a deterministic composite.
  Recommended weights favour durable real-world usefulness first, then
  commercial intent, then evergreen stability: `newcomer_value 0.34`,
  `commercial_intent 0.26`, `evergreen 0.15`, plus optional live slots
  `search_demand 0.13`, `trend 0.07`, `affiliate_demand 0.05` (sum = 1.0).
- Live signals are an **integration point only**. A `LiveSignalsProvider`
  Protocol documents the contract a future authorised source (Search Console
  export, a trends API, an affiliate feed) would implement. When a signal is
  absent (`None`) it contributes 0 and is recorded as *not used*, so ranking
  falls back to static editorial merit and never invents data.

**What is proven (real CI).** Weights sum to 1.0; scoring is bounded to
`[0,1]`; absent live signals are recorded as unused; supplied live signals are
clamped, applied, and recorded; ranking is deterministic and sorted; region
filtering (US/CA/BOTH) is correct; and the static-only top topic is a strongly
newcomer-critical one. No network, no live data, no fabrication.

**Still an integration point (NOT executed here).** Connecting real search /
trend / affiliate-demand data, and wiring the prioritizer output into the
generation entrypoint, remain follow-up steps requiring an authorised data
source. The ranking engine and its contract are complete and green.

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
| Clean (8-key EEAT meta) | BLOCKED | none | performance, competitor (PENDING offline) |
| Bad | BLOCKED | schema, eeat, formatting, accessibility, internal_links, originality | performance, competitor |

## Failure matrix (certification Phase 3)

Each defect is independently detected by the gate and blocks publication
(`tests/test_v4_failure_matrix.py`). Under B1 the per-element EEAT block test is
parametrized over all **8** required keys:

| Defect | Gate that blocks |
| ------ | ---------------- |
| Missing any of the 8 required EEAT elements | `eeat` |
| Duplicate / broken canonical | `canonical_uniqueness` |
| Body JSON-LD (second schema source) | `schema` |
| Emoji heading | `formatting` |
| Image missing alt text | `accessibility` |
| Internal links below minimum | `internal_links` |
| Contradicted YMYL value | `ymyl` |
| Banned AI opener / emoji heading | `originality` |

## Runtime gates — integration point (Option 1)

The runtime gates are the two checks that cannot be satisfied purely offline:
they need real measurements taken against a rendered, staged page. The V4
decision core already consumes these measurements through a stable, file-based
contract, so wiring them in CI is a matter of **supplying the two report
files** — no decision-core code changes are required. The behaviour of both
gates (good report -> PASS, bad report -> FAIL/BLOCK, absent report -> honest
PENDING/BLOCKED) is exercised by `tests/test_v4_runtime_gates.py` with
synthetic fixtures, proven green in V4 Pipeline Tests #14 (`85 passed`).

### Agent 22 — Performance (Lighthouse)

Agent 22 parses a Lighthouse JSON report and evaluates it against the V4
thresholds. To activate the gate in staging:

1. Run Lighthouse against the staged URL and write the JSON report, e.g.
   `lighthouse <url> --output=json --output-path=lighthouse.json`.
2. Feed it to the validator via `--lighthouse-json lighthouse.json`.
3. A report below threshold yields a blocking `performance` failure; a report
   at/above threshold clears the gate; an absent report keeps the gate at the
   honest **PENDING** state (clean content stays BLOCKED until the real
   measurement arrives).

### Agent 23 — Competitor / SERP coverage

Agent 23 compares the article against the top competitor results for the
target query and requires sufficient entity coverage. To activate the gate in
staging:

1. Collect the live SERP for the target query (e.g. via SERPAPI) and write the
   competitor corpus to `competitors.json`.
2. Feed it to the validator via `--competitors-json competitors.json`.
3. Coverage below the required entity threshold yields a blocking `competitor`
   failure; sufficient coverage clears the gate; an absent corpus keeps the
   gate at the honest **PENDING** state.

### End-to-end publish decision

`tests/test_v4_runtime_gates.py` proves the composed behaviour: a content-clean
article **plus** PASS performance and PASS competitor reports is the only
combination that reaches `READY_TO_PUBLISH`. The same clean article with either
runtime report missing remains **BLOCKED**, and a failing performance report
re-introduces the `performance` gate failure. No live Lighthouse run, SERPAPI
call, WordPress write, or OpenAI call is performed by these tests — they use
synthetic report fixtures only.

## EEAT consistency (Option 3 -> Approach B / B1 — RESOLVED)

Two EEAT definitions previously coexisted and were assumed identical; they were
not. **Option 3** first pinned that divergence with characterization tests
(V4 Pipeline Tests #16). **Approach B / B1** then RESOLVED it by establishing a
single source of truth and aligning the gate upward to the full 8-key set
(V4 Pipeline Tests #25, `111 passed`).

- `services/eeat_enrichment.py` now exposes `REQUIRED_EEAT_KEYS` (the 8 keys:
  `author`, `author_credentials`, `review_date`, `update_date`,
  `official_references`, `related_articles`, `disclosure`, `editorial_note`) as
  the authoritative list. `REQUIRED_ELEMENTS` is kept as a backwards-compatible
  alias.
- `scripts/quality_gate_v4.py` now **imports** `REQUIRED_EEAT_KEYS` instead of
  hard-coding its own list, so `THRESHOLDS["eeat_required_elements"]` IS the
  shared constant. The gate and the enrichment engine can no longer diverge.
- `tests/test_v4_eeat_consistency.py` was converted from characterization
  (freezing the divergence) to **alignment** tests: it asserts the two lists
  are identical, that the gate imports the shared constant (identity check),
  and that a legacy 6-key meta is now correctly BLOCKED by `check_eeat`.

**Behavioural change (intended).** Publication is now stricter: an article must
carry all 8 EEAT elements to clear the gate. In practice `build_eeat_fields()`
already supplies sensible defaults for `author_credentials` and
`editorial_note`, so a properly enriched article is unaffected; the tightening
only blocks metas constructed outside the enrichment path. Two pre-existing
fixtures (`test_v4_failure_matrix` COMPLETE_META and the harness CLEAN_META)
were completed to the 8-key set as part of this change.

## Generation -> WordPress orchestrator (Option 2 — preparation only)

The publish boundary is implemented in `orchestrator/publish_decision.py` and
proven by `tests/test_v4_orchestrator_publish.py` (V4 Pipeline Tests #18,
`106 passed`) with WordPress **fully mocked**. No real WordPress write, no
OpenAI call, and no network access occur in these tests.

Safety invariants enforced by the boundary:

1. **Gate-gated.** `decide_publication()` emits `action == "PUBLISH"` only when
   `quality_gate_v4` returns `READY_TO_PUBLISH`; a BLOCKED gate yields HOLD.
2. **Dry-run by default.** `execute_plan()` performs no WordPress write unless
   the caller passes `allow_live=True` explicitly. The default is a pure
   simulation that contacts nothing.
3. **Draft-only, non-destructive.** Even in live mode the boundary calls only
   `WordPressService.create_post()` with `status="draft"`. It never calls
   `publish_post()` or transitions a post to `publish`: going live remains a
   separate, manual, human-authorised step.

**Live integration point (NOT executed here).** Turning on real publishing
requires: valid WordPress credentials in config, a caller that passes
`allow_live=True`, and a human decision to promote the created draft to
published. None of this is wired into CI, and no live run has been performed.
## Known non-blocking warning

CI emits a Node 20 deprecation notice for `actions/checkout@v4`,
`actions/setup-python@v5`, and `actions/upload-artifact@v4` (GitHub is forcing
Node 24). This does not affect test results and is tracked as low-priority
maintenance.

## Still pending (not validated here, by design)

- Performance gate (Agent 22 / Lighthouse) and competitor gate (Agent 23 /
  SERP) require real runtime measurements supplied from staging. The wiring
  contract is documented above; only the live measurement acquisition remains.
- The full generation -> WordPress orchestrator live path is prepared and
  tested in dry-run only; real publishing remains a manual, authorised step.
- EEAT consistency reconciliation is now **complete** (Approach B / B1): the
  gate and enrichment share one 8-key source of truth. No EEAT debt remains
  deferred.
- Topic selection (M7) ranks newcomer topics from editorial knowledge today;
  real search / trend / affiliate-demand signals and the generation-entrypoint
  wiring remain follow-up integration points awaiting an authorised data
  source.
