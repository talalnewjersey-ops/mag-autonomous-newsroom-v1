# Task 4 — Pipeline Upgrade Proposal (branch: `nexus14/priority-engine`)

**Nothing in this branch is applied to production.** All additions are either new,
inert files, or additive log-only hooks into existing agents (see the diff summary
below — `decision`/`blocking`/`pool.sort()` in the touched files are byte-for-byte
unchanged). Staged locally, not committed, not pushed.

## Critical discovery before proposing anything new

The repo already has a cannibalization detector: `agents/agent_17_cannibalization.py`,
invoked on every article run (`scripts/production_batch_loop.sh` line 134, confirmed
running in today's production log — "Fetched 49 articles (status=publish)"). It has:
- Title similarity (`difflib.SequenceMatcher`)
- Keyword Jaccard overlap
- An AI semantic pass (Claude Opus) when `ANTHROPIC_API_KEY` is set
- Slug-collision detection
- `REJECT_THRESHOLD = 0.85`, `SIMILARITY_THRESHOLD = 0.72` (observation)

**It never blocks.** `scripts/production_batch_loop.sh` line 132-138 is explicit:
```
# FIX 2: Agent 17 Cannibalization -- INFORMATIONAL ONLY, never blocks
...
echo "[${ARTICLE_NUM}] Cannibalization: ${CANN_DECISION} -- NOT blocking"
```
This is a deliberate, documented state (`# FIX 2`), not an oversight — **why it was
disabled is not established by anything read in this session** and should be
investigated (check `AUDIT-LOG.md` / git blame on that line) before anyone flips it
back to blocking. It may have been disabled because of a real false-positive problem
with the lexical metrics — which the next finding supports.

There is also a SECOND, separate, even-weaker dedup check earlier in the pipeline:
`agent_01_seo_research.py::_is_near_duplicate` (`SequenceMatcher` only, 0.80
threshold), which filters the candidate pool *before* selection. Two independent,
both-lexical dedup layers exist; neither is strong enough (next section), and only
the earlier one (`_is_near_duplicate`) actually filters anything.

## Empirical proof the existing lexical metrics are insufficient

Using agent_17's own `text_similarity` + `keyword_overlap` functions, imported and
run live against the 5 confirmed real-world duplicate pairs found in the 2026-07-19
editorial audit (`docs/nexus14-editorial-strategy/task1-cannibalization-audit.md`):

| Pair | title_sim | keyword_overlap | combined | Agent 17 verdict |
|---|---|---|---|---|
| Cluster C (credit cards, no-SSN) | 0.586 | 0.571 | 0.586 | **MISSED** (below 0.72) |
| Cluster G (credit cards, Canada) | 0.778 | 0.800 | 0.800 | flagged at observe (0.72), still below REJECT (0.85), and observe-only never blocks anyway |
| Cluster A (money transfer roundup vs. comparison) | 0.508 | 0.125 | 0.508 | **MISSED** |
| Cluster F, page 1 vs 2 (Canada banks) | 0.444 | 0.250 | 0.444 | **MISSED** |
| Cluster F, page 1 vs 3 (Canada banks) | 0.582 | 0.182 | 0.582 | **MISSED** |

**4 of 5 confirmed duplicates fall below even the 0.72 observation threshold.** Even
with `AGENT17_OBSERVE_ONLY=false`, this specific metric would not have caught most of
what the manual audit found. The gap is the metric, not just the flag.

A pure-stdlib TF-IDF cosine proxy (this proposal's `agents/_embedding_similarity.py`,
built for offline demonstration since no `OPENAI_API_KEY` is available in this local
session) does somewhat better on richer text (title+meta) but **still cannot cleanly
separate confirmed duplicates from confirmed-distinct pages** — dupe scores 0.19-0.57,
distinct-page control scores 0.13-0.38, ranges overlap. This is reported honestly in
that module's docstring, not glossed over: it is evidence FOR needing real semantic
embeddings in production, not a working substitute for them.

## What this branch actually adds

1. **`agents/_priority_score.py`** — Task 4(a). `PriorityScore = 0.25*Revenue +
   0.25*Winnability + 0.15*IntentFit + 0.10*AuthorityContribution +
   0.15*CannibalizationSafety + 0.10*Freshness`, each factor 0-5, scaled to 0-100.
   Only `Revenue` (from `monetization_score`) and `IntentFit`-proxy (from
   `traffic_score`) are real registry fields; the other four factors default to a
   neutral 3/5 with an explicit `[estimation: ...]` basis string logged alongside
   every score — no factor is ever presented as measured when it isn't.

2. **`agents/_embedding_similarity.py`** — Task 4(b), semantic layer. Real path:
   `openai_embedding_similarity()` via `text-embedding-3-small` (OPENAI_API_KEY is
   already a configured repo secret, used elsewhere by `generate_drafts.py`).
   Fallback path for when the key is unavailable: `tfidf_proxy_similarity()`, loudly
   logged as degraded, never silent.

3. **`agents/agent_17_cannibalization.py` diff** — adds a `semantic_similarity` block
   to the existing `observation` section of the report. Batches ONE similarity call
   across all existing titles (not per-article). Does not touch `decision`,
   `blocking`, `score`, or `conflicts` — those are exactly as they were before this
   patch. Falls back to the TF-IDF proxy with a loud warning log if no API key.

4. **`agents/agent_01_seo_research.py` diff** — adds a `PRIORITY_ENGINE_DRY_RUN`
   (default `true`) block inside `_select_from_registry` that computes and logs what
   PriorityScore-based selection would have picked, and whether it matches the
   actual (unchanged) monetization/traffic selection. Does not touch `pool.sort()`.

5. **`data/corpus_index.json`** — one-time corpus snapshot (51 published posts,
   title+slug), built from the live WP REST API (read-only), same fetch pattern
   agent_17 already uses.

6. **`scripts/dry_run_priority_engine.py`** — standalone, no network calls, reads
   only `data/topic_registry.json` + `data/corpus_index.json`. Actually run this
   session; full output in `task4-dry-run-log.txt` in this same directory.

## What is explicitly NOT proposed here

- A slug-exists / keyword-registry REJECT gate wired into the selection loop, as
  literally specified in Task 4(b)'s third bullet and 4(c)'s "drop gate failures"
  step. **Rationale:** `agent_01_seo_research.py` already has `EXCLUDED_STATUSES`
  and `_is_near_duplicate` doing a version of this at the registry level, and
  `agent_17` already does a slug-collision check post-selection
  (`observation.slug_collisions`). Wiring a THIRD independent slug/keyword check
  risks exactly the kind of redundant, semi-overlapping-but-not-quite-consistent
  guardrail sprawl this whole audit exists to clean up. **Recommend:** once you
  decide how to handle the `AGENT17_OBSERVE_ONLY` question (see below), extend
  agent_17's existing slug-collision + semantic-similarity checks into a real
  keyword-registry lookup (Task 2's `task2-keyword-registry.json` is a start) rather
  than building a parallel fourth mechanism. Flagging as a design decision for you,
  not resolving it here.
- Calendar-diversity enforcement (Task 4c) — `_select_from_registry` already has a
  category-rotation tie-breaker (`cat_usage`); whether that satisfies "no same
  category two days running" depends on how batches are scheduled
  (`production_v2.yml`'s cron cadence, not reviewed in this session per the
  no-CI/CD-touching constraint). Flagging as unresolved, not touching CI config to
  investigate further.

## Before promoting anything here out of dry-run

1. Find out why `AGENT17_OBSERVE_ONLY` / the `# FIX 2` comment exists — check
   `AUDIT-LOG.md` and git history on that line. If it was a false-positive problem,
   the semantic-similarity addition in this branch may be the actual fix; if it was
   something else (rate limits, cost, a bad incident), that needs its own read before
   re-enabling blocking.
2. Get `OPENAI_API_KEY` embedding calls actually run against a real batch of
   candidate topics (this session had no local API key) and compare against the
   TF-IDF proxy's calls on the same pairs, to confirm the real embedding threshold
   (0.86 per the original spec) actually holds on this corpus before trusting it.
3. Run `PRIORITY_ENGINE_DRY_RUN=true` (already the default) for several real
   production batches and read the logged "would-select" vs. "actual-select" lines
   before ever considering flipping it to change real selection.
