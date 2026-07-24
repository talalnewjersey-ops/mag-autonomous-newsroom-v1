#!/usr/bin/env bash
# NEXUS-14 production batch loop -- extracted from production_v2.yml's
# "Batch Loop -- 3 Articles Sequential" step (2026-07-12).
#
# WHY THIS EXISTS AS A SEPARATE FILE: the inline `run:` block this replaces
# hit GitHub's ~21000-char hard limit on a single expression TWICE --
# blocked once at PR #73 (fixed by trimming comments, margin ~650 chars)
# and again on 2026-07-11 when a verbose comment pushed it to 20950 chars,
# which made GitHub reject the ENTIRE workflow file as invalid and silently
# skipped the 2026-07-12 06:00 UTC scheduled run (see AUDIT-LOG.md). #73
# considered this exact extraction and deferred it ("not in a rush") --
# two outages from the same limit is the signal to stop deferring it.
#
# `set -eo pipefail` reproduces EXACTLY what GitHub Actions was already
# doing implicitly for the inline `run:` block (its default shell for a
# bash step IS `bash --noprofile --norc -eo pipefail {0}`) -- a bare
# `bash scripts/production_batch_loop.sh` invocation does NOT inherit that
# from the parent step, so it must be set explicitly here or every
# unguarded command (e.g. `mkdir -p`) would silently stop aborting on
# failure, a behavior change nobody asked for. Deliberately NOT `set -u`
# (nounset) -- that IS a stricter, new behavior not present before, and
# auditing every env var read for unset-safety is out of scope of a
# behavior-preserving extraction.
set -eo pipefail

# ---------------------------------------------------------------------------
# Pure decision-logic functions, isolated so they are unit-testable without
# running the full agent pipeline (source this file with
# PRODUCTION_BATCH_LOOP_SOURCE_ONLY=1 to get these without the loop below).
# ---------------------------------------------------------------------------

resolve_draft_only() {
  # Safety default: anything but the explicit literal "false" means
  # draft-only. Covers scheduled runs too (no workflow_dispatch inputs at
  # all, so the raw value is empty) -- a cron re-enabled without an
  # explicit override stays draft-only until someone deliberately turns it
  # off. $1 = raw DRAFT_ONLY value (may be "", "true", or "false").
  if [ "$1" = "false" ]; then
    echo "false"
  else
    echo "true"
  fi
}

resolve_max_articles() {
  # $1 = workflow_dispatch input value (may be empty), $2 = route-trigger
  # job's own output (the real per-slot value for scheduled runs -- FIX
  # 2026-07-12: the inline version this replaces referenced
  # `needs.detect.outputs.max_articles`, a job named "detect" that does
  # not exist (the job is "route-trigger"; "detect" is only its step id) --
  # that fallback was silently always empty, so every scheduled run used
  # the literal `3` default regardless of route-trigger's real per-slot
  # value. Fixed here by taking the real job output as $2.
  local n="${1:-${2:-3}}"
  case "$n" in (*[!0-9]*|"") n=3 ;; esac
  if [ "$n" -lt 1 ]; then n=1; fi
  if [ "$n" -gt 3 ]; then n=3; fi
  echo "$n"
}

resolve_article_tier() {
  # $1 = revenue score (string, e.g. from agent_18), $2 = raw
  # FORCE_OPPORTUNITY_TIER value (may be "", "true", or "false").
  local score="$1" force="$2" tier="STANDARD"
  if python3 -c "import sys; sys.exit(0 if float('${score}') > 85 else 1)" 2>/dev/null; then
    tier="PILLAR"
  fi
  if python3 -c "import sys; sys.exit(0 if float('${score}') < 70 else 1)" 2>/dev/null; then
    tier="OPPORTUNITY"
  fi
  # RODAGE SAFETY (2026-07-11): STANDARD/PILLAR fail GATE LENGTH after retry
  # (AUDIT-LOG.md) -- force OPPORTUNITY during rodage, same safe-default
  # pattern as DRAFT_ONLY (anything but the literal "false" forces it).
  if [ "$force" != "false" ]; then
    tier="OPPORTUNITY"
  fi
  echo "$tier"
}

if [ "${PRODUCTION_BATCH_LOOP_SOURCE_ONLY:-}" = "1" ]; then
  return 0 2>/dev/null || exit 0
fi

# ---------------------------------------------------------------------------
# Main batch loop (unchanged logic from the inline run: block it replaces --
# a behavior-preserving move, not a rewrite).
# ---------------------------------------------------------------------------

ARTICLES_PRODUCED=0
ARTICLES_FAILED=0

DRAFT_ONLY=$(resolve_draft_only "$DRAFT_ONLY")
echo "DRAFT_ONLY mode: ${DRAFT_ONLY}"

MAX_ARTICLES=$(resolve_max_articles "$MAX_ARTICLES_INPUT" "$MAX_ARTICLES_ROUTE")
echo "Batch will produce $MAX_ARTICLES article(s) (max_articles input respected)"

for ARTICLE_NUM in $(seq 1 "$MAX_ARTICLES"); do
  echo "===== ARTICLE ${ARTICLE_NUM} OF ${MAX_ARTICLES} ====="
  export ARTICLE_DIR="output/article_${ARTICLE_NUM}"
  mkdir -p "${ARTICLE_DIR}/"{agent_01,agent_02,agent_03,agent_04,agent_05}
  mkdir -p "${ARTICLE_DIR}/"{agent_06,agent_07,agent_08,agent_09,agent_10}
  mkdir -p "${ARTICLE_DIR}/"{agent_11,agent_12,agent_13,agent_16,agent_17,agent_18}
  GATE_FEEDBACK=""
  DRAFT="${ARTICLE_DIR}/agent_04/article_draft.md"  # DRY alias, reused ~20x below

  # Phase 1: SEO Research [BLOCKING]
  echo "[${ARTICLE_NUM}] Phase 1: SEO Research"
  ARTICLE_NUM=${ARTICLE_NUM} python -m agents.agent_01_seo_research \
    --max-topics 1 --topic "${TOPIC_OVERRIDE}" --output "${ARTICLE_DIR}/agent_01/topics.json" || {
    echo "Agent 01 FAILED"; ARTICLES_FAILED=$((ARTICLES_FAILED+1)); continue
  }

  # Phase 2: Keyword Validation [BLOCKING]
  echo "[${ARTICLE_NUM}] Phase 2: Keyword Validation"
  python -m agents.agent_02_keyword_validation \
    --input "${ARTICLE_DIR}/agent_01/topics.json" \
    --output "${ARTICLE_DIR}/agent_02/validated_topics.json" || {
    echo "Agent 02 FAILED"; ARTICLES_FAILED=$((ARTICLES_FAILED+1)); continue
  }

  # Extract topic metadata -- single-line python for YAML safety
  TOPIC=$(python3 -c "import json; d=json.load(open('${ARTICLE_DIR}/agent_02/validated_topics.json')); t=d.get('topics',d if isinstance(d,list) else [d]); item=t[0] if t else {}; print(item.get('title',item.get('keyword','newcomer guide')) if isinstance(item,dict) else str(item))" 2>/dev/null || echo "newcomer banking guide")
  KEYWORDS=$(python3 -c "import json; d=json.load(open('${ARTICLE_DIR}/agent_02/validated_topics.json')); t=d.get('topics',d if isinstance(d,list) else [d]); item=t[0] if t else {}; print(item.get('keyword','') if isinstance(item,dict) else '')" 2>/dev/null || echo "")
  # SPRINT 7: registry category + market -> routes Agent 04 official-source vertical
  CATEGORY=$(python3 -c "import json; d=json.load(open('${ARTICLE_DIR}/agent_02/validated_topics.json')); t=d.get('topics',d if isinstance(d,list) else [d]); item=t[0] if t else {}; print(item.get('category','') if isinstance(item,dict) else '')" 2>/dev/null || echo "")
  MARKET=$(python3 -c "import json; d=json.load(open('${ARTICLE_DIR}/agent_02/validated_topics.json')); t=d.get('topics',d if isinstance(d,list) else [d]); item=t[0] if t else {}; print(item.get('market','') if isinstance(item,dict) else '')" 2>/dev/null || echo "")
  # FIX 1a: Pass real SV/CPC from topic DB with defaults to Agent 18
  SV=$(python3 -c "import json; d=json.load(open('${ARTICLE_DIR}/agent_02/validated_topics.json')); t=d.get('topics',d if isinstance(d,list) else [d]); item=t[0] if t else {}; print(int(item.get('search_volume',2000)) if isinstance(item,dict) else 2000)" 2>/dev/null || echo "2000")
  CPC=$(python3 -c "import json; d=json.load(open('${ARTICLE_DIR}/agent_02/validated_topics.json')); t=d.get('topics',d if isinstance(d,list) else [d]); item=t[0] if t else {}; print(float(item.get('cpc',3.50)) if isinstance(item,dict) else 3.50)" 2>/dev/null || echo "3.50")

  # FIX 2: Agent 17 Cannibalization -- INFORMATIONAL ONLY, never blocks
  echo "[${ARTICLE_NUM}] Phase 2.5: Cannibalization Check (informational)"
  python -m agents.agent_17_cannibalization \
    --topic "${TOPIC}" --keywords "${KEYWORDS}" \
    --output "${ARTICLE_DIR}/agent_17/cannibalization_report.json" || true
  CANN_DECISION=$(python3 -c "import json; r=json.load(open('${ARTICLE_DIR}/agent_17/cannibalization_report.json')); print(r.get('decision','UNKNOWN'))" 2>/dev/null || echo "SKIPPED")
  echo "[${ARTICLE_NUM}] Cannibalization: ${CANN_DECISION} -- NOT blocking"

  # FIX 1: Agent 18 Revenue -- INFORMATIONAL ONLY, never blocks
  echo "[${ARTICLE_NUM}] Phase 2.6: Revenue Intelligence (informational)"
  python -m agents.agent_18_revenue_intelligence \
    --topic "${TOPIC}" --keywords "${KEYWORDS}" \
    --search-volume "${SV}" --cpc "${CPC}" \
    --output "${ARTICLE_DIR}/agent_18/revenue_score.json" || true
  SCORE=$(python3 -c "import json; r=json.load(open('${ARTICLE_DIR}/agent_18/revenue_score.json')); print(r.get('revenue_score',70))" 2>/dev/null || echo "70")
  echo "[${ARTICLE_NUM}] Revenue score: ${SCORE}/100 -- NOT blocking"

  # Determine article tier from revenue score (rodage override applied inside)
  ARTICLE_TYPE=$(resolve_article_tier "$SCORE" "$FORCE_OPPORTUNITY_TIER")
  echo "[${ARTICLE_NUM}] Article tier: ${ARTICLE_TYPE}"

  # Phase 3: Content Planning [BLOCKING]
  echo "[${ARTICLE_NUM}] Phase 3: Content Planning"
  python -m agents.agent_03_content_planner \
    --input "${ARTICLE_DIR}/agent_02/validated_topics.json" \
    --output "${ARTICLE_DIR}/agent_03/article_outline.json" || {
    echo "Agent 03 FAILED"; ARTICLES_FAILED=$((ARTICLES_FAILED+1)); continue
  }

  # RETRY (2026-07-06): content-writer gates (G-Substance/G3/A/B) get ONE
  # retry w/ gate feedback injected into the prompt; bounded 0..1, never more.
  # Each gate's report is also copied to *_attempt0.json on retry trigger
  # (2026-07-11, AUDIT-LOG.md) -- else attempt-0's failure reason is lost
  # when attempt 1 overwrites the unsuffixed report.
  for RETRY_ATTEMPT in 0 1; do
  # Phase 4: Article Writing [BLOCKING]
  echo "[${ARTICLE_NUM}] Phase 4: Article Writing (TIER: ${ARTICLE_TYPE}) [retry attempt ${RETRY_ATTEMPT}]"
  ARTICLE_TYPE=${ARTICLE_TYPE} python -m agents.agent_04_article_writer \
    --input "${ARTICLE_DIR}/agent_03/article_outline.json" \
    --output "$DRAFT" \
    --article-type "${ARTICLE_TYPE}" \
    --category "${CATEGORY}" --market "${MARKET}" \
    --retry-feedback "${GATE_FEEDBACK}" || {
    if [ "$RETRY_ATTEMPT" -eq 0 ]; then
      echo "Agent 04 FAILED (attempt 1/2) for article ${ARTICLE_NUM} -- retrying once with gate feedback"
      GATE_FEEDBACK="Agent 04 validation failed -- ensure min words/FAQs/sources/comparison table/expert section/disclaimer/author bio are all met."
      continue
    fi
    echo "Agent 04 FAILED (attempt 2/2, retry exhausted) for article ${ARTICLE_NUM}"
    ARTICLES_FAILED=$((ARTICLES_FAILED+1)); continue 2
  }

  # Couche 2 soften [non-blocking]: strips unsourced invented figures (see script docstring).
  echo "[${ARTICLE_NUM}] Phase 4.4: Couche 2 soften [non-blocking]"
  python scripts/soften_claims.py \
    --input "$DRAFT" \
    --report "${ARTICLE_DIR}/agent_04/soften_report.json" \
    --market "${MARKET}" --category "${CATEGORY}" || true

  # Prose polish [non-blocking]: deletion-only cleanup of soften's scaffold (see script docstring).
  echo "[${ARTICLE_NUM}] Phase 4.44: Prose polish [non-blocking]"
  python scripts/polish_prose.py \
    --input "$DRAFT" \
    --report "${ARTICLE_DIR}/agent_04/polish_report.json" || true

  # MICRO-TRIM [non-blocking] (2026-07-11, #81): mechanical fix for a tiny (<=2%)
  # GATE LENGTH overage -- zero extra API cost vs. a full retry (see script docstring).
  echo "[${ARTICLE_NUM}] Phase 4.441: Micro-Trim [non-blocking]"
  python scripts/micro_trim.py \
    --input "$DRAFT" \
    --article-type "${ARTICLE_TYPE}" \
    --report "${ARTICLE_DIR}/agent_04/micro_trim_report.json" || true

  # GATE LENGTH [BLOCKING] (2026-07-11): symmetric ceiling counterpart to agent_04's
  # floor-only word-count expansion. agent_12's own tier-relative check catches an
  # overshoot too, but sits OUTSIDE this retry loop (GATE QA/EDITOR are single-shot) --
  # real finding: witness run 5 article 2 (STANDARD, 5232w vs 4000w target, +30.8%) had
  # zero chance to self-correct before landing on that non-retriable gate. Same
  # tolerance as agent_12_quality_assurance.py's _WORD_COUNT_TOLERANCE (0.10).
  echo "[${ARTICLE_NUM}] Phase 4.442: Length Gate [BLOCKING]"
  python scripts/length_gate.py \
    --input "$DRAFT" \
    --article-type "${ARTICLE_TYPE}" \
    --output "${ARTICLE_DIR}/agent_04/length_report.json" || {
    if [ "$RETRY_ATTEMPT" -eq 0 ]; then
      echo "GATE LENGTH FAIL (attempt 1/2) for article ${ARTICLE_NUM} -- retrying once with gate feedback"
      GATE_FEEDBACK=$(python3 scripts/gate_feedback.py --gate length --report "${ARTICLE_DIR}/agent_04/length_report.json" 2>/dev/null)
      python3 scripts/structure_completeness_gate.py --input "$DRAFT" --snapshot "${ARTICLE_DIR}/agent_04/pre_retry_snapshot.json" || true
      cp "${ARTICLE_DIR}/agent_04/length_report.json" "${ARTICLE_DIR}/agent_04/length_report_attempt0.json" || true
      continue
    fi
    echo "GATE LENGTH FAIL (attempt 2/2, retry exhausted): article ${ARTICLE_NUM} still over the word-count ceiling"
    ARTICLES_FAILED=$((ARTICLES_FAILED+1)); continue 2
  }

  # Couche 3 G-Substance gate [BLOCKING]: rejects a hollow article before it can reach WordPress.
  echo "[${ARTICLE_NUM}] Phase 4.45: G-Substance Gate [BLOCKING]"
  python scripts/g_substance_gate.py \
    --input "$DRAFT" \
    --article-type "${ARTICLE_TYPE}" \
    --market "${MARKET}" --category "${CATEGORY}" \
    --output "${ARTICLE_DIR}/agent_04/g_substance_report.json" || {
    if [ "$RETRY_ATTEMPT" -eq 0 ]; then
      echo "GATE G-SUBSTANCE FAIL (attempt 1/2) for article ${ARTICLE_NUM} -- retrying once with gate feedback"
      GATE_FEEDBACK=$(python3 scripts/gate_feedback.py --gate g_substance --report "${ARTICLE_DIR}/agent_04/g_substance_report.json" 2>/dev/null)
      python3 scripts/structure_completeness_gate.py --input "$DRAFT" --snapshot "${ARTICLE_DIR}/agent_04/pre_retry_snapshot.json" || true
      cp "${ARTICLE_DIR}/agent_04/g_substance_report.json" "${ARTICLE_DIR}/agent_04/g_substance_report_attempt0.json" || true
      continue
    fi
    echo "GATE G-SUBSTANCE FAIL (attempt 2/2, retry exhausted): hollow article ${ARTICLE_NUM} (never reaches WordPress)"
    ARTICLES_FAILED=$((ARTICLES_FAILED+1)); continue 2
  }

  # URL normalization [non-blocking]: repairs a mutated .gov URL before fact-check (see script docstring).
  echo "[${ARTICLE_NUM}] Phase 4.46: URL normalization [non-blocking]"
  python scripts/normalize_urls.py \
    --input "$DRAFT" \
    --market "${MARKET}" --category "${CATEGORY}" \
    --report "${ARTICLE_DIR}/agent_04/url_normalize_report.json" || true

  # SPRINT 2 (C): DRI metric [REPORTING, non-blocking] -- diffuse repetition proof.
  python scripts/dri_metric.py \
    --input "$DRAFT" \
    --output "${ARTICLE_DIR}/agent_04/dri_report.json" || true
  # SPRINT 2 (C): Gate G3 anti-repetition [BLOCKING] -- after writer, before QA.
  echo "[${ARTICLE_NUM}] Phase 4.5: Anti-Repetition Gate G3 [BLOCKING]"
  python scripts/g3_repetition_gate.py \
    --input "$DRAFT" \
    --output "${ARTICLE_DIR}/agent_04/g3_report.json" || {
    if [ "$RETRY_ATTEMPT" -eq 0 ]; then
      echo "GATE G3 FAIL (attempt 1/2) for article ${ARTICLE_NUM} -- retrying once with gate feedback"
      GATE_FEEDBACK=$(python3 scripts/gate_feedback.py --gate g3 --report "${ARTICLE_DIR}/agent_04/g3_report.json" 2>/dev/null)
      python3 scripts/structure_completeness_gate.py --input "$DRAFT" --snapshot "${ARTICLE_DIR}/agent_04/pre_retry_snapshot.json" || true
      cp "${ARTICLE_DIR}/agent_04/g3_report.json" "${ARTICLE_DIR}/agent_04/g3_report_attempt0.json" || true
      continue
    fi
    echo "GATE G3 FAIL (attempt 2/2, retry exhausted): repetition detected in article ${ARTICLE_NUM}"
    ARTICLES_FAILED=$((ARTICLES_FAILED+1)); continue 2
  }
  # Phase 5: Fact Checking [BLOCKING GATE A]
  echo "[${ARTICLE_NUM}] Phase 5: Fact Checking [GATE A]"
  python -m agents.agent_05_fact_checker \
    --input "$DRAFT" \
    --output "${ARTICLE_DIR}/agent_05/fact_check_report.json" \
    --min-sources "${FACT_CHECK_MIN_SOURCES}" \
    --market "${MARKET}" --category "${CATEGORY}" || {
    if [ "$RETRY_ATTEMPT" -eq 0 ]; then
      echo "GATE A FAIL (attempt 1/2) for article ${ARTICLE_NUM} -- retrying once with gate feedback"
      GATE_FEEDBACK=$(python3 scripts/gate_feedback.py --gate gate_a --report "${ARTICLE_DIR}/agent_05/fact_check_report.json" 2>/dev/null)
      python3 scripts/structure_completeness_gate.py --input "$DRAFT" --snapshot "${ARTICLE_DIR}/agent_04/pre_retry_snapshot.json" || true
      cp "${ARTICLE_DIR}/agent_05/fact_check_report.json" "${ARTICLE_DIR}/agent_05/fact_check_report_attempt0.json" || true
      continue
    fi
    echo "GATE A FAIL (attempt 2/2, retry exhausted): Fact checker blocked article ${ARTICLE_NUM}"
    ARTICLES_FAILED=$((ARTICLES_FAILED+1)); continue 2
  }

  # Phase 6: EEAT Validation [BLOCKING GATE B]
  echo "[${ARTICLE_NUM}] Phase 6: EEAT Validation [GATE B]"
  python -m agents.agent_06_eeat_validator \
    --input "$DRAFT" \
    --output "${ARTICLE_DIR}/agent_06" \
    --threshold "${EEAT_SCORE_THRESHOLD}" || {
    if [ "$RETRY_ATTEMPT" -eq 0 ]; then
      echo "GATE B FAIL (attempt 1/2) for article ${ARTICLE_NUM} -- retrying once with gate feedback"
      GATE_FEEDBACK=$(python3 scripts/gate_feedback.py --gate gate_b --report "${ARTICLE_DIR}/agent_06/eeat_report.json" 2>/dev/null)
      python3 scripts/structure_completeness_gate.py --input "$DRAFT" --snapshot "${ARTICLE_DIR}/agent_04/pre_retry_snapshot.json" || true
      cp "${ARTICLE_DIR}/agent_06/eeat_report.json" "${ARTICLE_DIR}/agent_06/eeat_report_attempt0.json" || true
      continue
    fi
    echo "GATE B FAIL (attempt 2/2, retry exhausted): EEAT blocked article ${ARTICLE_NUM}"
    ARTICLES_FAILED=$((ARTICLES_FAILED+1)); continue 2
  }

  # RETRY SAFETY (2026-07-06): a retry (attempt 1) must not ship something
  # structurally worse than the draft it replaced -- compare vs the pre-retry
  # snapshot; a regression is a full failure (see structure_completeness_gate.py).
  if [ "$RETRY_ATTEMPT" -eq 1 ] && [ -f "${ARTICLE_DIR}/agent_04/pre_retry_snapshot.json" ]; then
    echo "[${ARTICLE_NUM}] Retry structural-completeness check"
    python3 scripts/structure_completeness_gate.py \
      --input "$DRAFT" \
      --compare "${ARTICLE_DIR}/agent_04/pre_retry_snapshot.json" || {
      echo "GATE RETRY-COMPLETENESS FAIL: the retry produced a structurally worse draft for article ${ARTICLE_NUM} -- never shipping it"
      ARTICLES_FAILED=$((ARTICLES_FAILED+1)); continue 2
    }
  fi
  break
  done

  # Phase 7-8: Internal Linking + Affiliate (non-blocking)
  echo "[${ARTICLE_NUM}] Phase 7-8: Linking + Affiliate (non-blocking)"
  python -m agents.agent_07_internal_linking \
    --input "$DRAFT" \
    --output "${ARTICLE_DIR}/agent_07/internal_links.json" \
    --min-links "${MIN_INTERNAL_LINKS}" || true
  python -m agents.agent_08_affiliate_optimizer \
    --input "$DRAFT" \
    --output "${ARTICLE_DIR}/agent_08/affiliate_report.json" || true

  # Phase 9: Image Prompts (non-blocking)
  echo "[${ARTICLE_NUM}] Phase 9: Image Prompts"
  python -m agents.agent_09_image_prompt_generator \
    --input "$DRAFT" \
    --metadata "${ARTICLE_DIR}/agent_04/article_metadata.json" \
    --output "${ARTICLE_DIR}/agent_09/image_prompts.json" \
    --count "${MIN_IMAGES}" || true

  # FIX 3: Phase 10 -- Gemini ONLY (Nano Banana removed)
  echo "[${ARTICLE_NUM}] Phase 10: Image Production (Gemini ONLY)"
  python -m agents.agent_10_image_production \
    --input "${ARTICLE_DIR}/agent_09/image_prompts.json" \
    --output "${ARTICLE_DIR}/agent_10/" \
    --validation-report "${ARTICLE_DIR}/agent_10/image_validation_report.json" \
    --min-images "${MIN_IMAGES}" \
    --provider gemini || true

  # Phase 10.5: Publishing Optimization (non-blocking)
  echo "[${ARTICLE_NUM}] Phase 10.5: Publishing Optimization"
  python -m agents.agent_16_publishing_optimization \
    --input "$DRAFT" \
    --faq-data "${ARTICLE_DIR}/agent_03/article_outline.json" \
    --image-url "${ARTICLE_DIR}/agent_10/featured_image_url.txt" \
    --output "${ARTICLE_DIR}/agent_16/publishing_optimizer.json" || true

  # Phase 11: WordPress Draft [BLOCKING GATE C]
  echo "[${ARTICLE_NUM}] Phase 11: WordPress Draft [GATE C]"
  python -m agents.agent_11_wordpress_integration \
    --article "$DRAFT" \
    --images "${ARTICLE_DIR}/agent_10/" \
    --rank-math "${ARTICLE_DIR}/agent_16/publishing_optimizer.json" \
    --output "${ARTICLE_DIR}/agent_11/wordpress_report.json" \
    --market "${MARKET}" --category "${CATEGORY}" \
    --validation-report "${ARTICLE_DIR}/agent_11/wordpress_validation_report.json" || {
    echo "GATE C FAIL: WordPress draft not created for article ${ARTICLE_NUM}"
    ARTICLES_FAILED=$((ARTICLES_FAILED+1)); continue
  }

  # Phase 11.5: Anti-Placeholder Gate [BLOCKING GATE D] (2026-07-18, AUDIT-LOG.md)
  # Runs AFTER agent_11 (needs its real, WordPress-bound title -- see
  # scripts/placeholder_gate.py's module docstring for why the title check
  # can't live inside agent_12) and BEFORE agent_12 scoring, so a dropped
  # template variable is caught before any more pipeline work is spent on
  # an article that's going to be rejected anyway. Real case that forced
  # this: 48854 published with 4 body-text placeholder leaks + a broken
  # Title Case, scored 98.8/100, went out with no human review at all.
  echo "[${ARTICLE_NUM}] Phase 11.5: Anti-Placeholder Gate [GATE D]"
  python scripts/placeholder_gate.py \
    --article "$DRAFT" \
    --wordpress-report "${ARTICLE_DIR}/agent_11/wordpress_report.json" \
    --image-prompts "${ARTICLE_DIR}/agent_09/image_prompts.json" \
    --output "${ARTICLE_DIR}/agent_11/placeholder_gate_report.json" || {
    echo "GATE D FAIL: placeholder artifact(s) detected in article ${ARTICLE_NUM} -- never scoring, never publishing"
    python scripts/mark_qa_failed.py --wordpress-report "${ARTICLE_DIR}/agent_11/wordpress_validation_report.json" --gate PLACEHOLDER || true
    ARTICLES_FAILED=$((ARTICLES_FAILED+1)); continue
  }

  # SPRINT 1 (B/C): Phase 12-13 QA + Chief Editor are now BLOCKING gates.
  echo "[${ARTICLE_NUM}] Phase 12-13: QA + Chief Editor [BLOCKING]"
  python -m agents.agent_12_quality_assurance \
    --article "$DRAFT" \
    --wordpress-report "${ARTICLE_DIR}/agent_11/wordpress_report.json" \
    --fact-check "${ARTICLE_DIR}/agent_05/fact_check_report.json" \
    --image-validation "${ARTICLE_DIR}/agent_10/image_validation_report.json" \
    --output "${ARTICLE_DIR}/agent_12/qa_report.json" \
    --article-type "${ARTICLE_TYPE}" \
    --min-words "${MIN_WORD_COUNT}" --min-images "${MIN_IMAGES}" \
    --min-faq "${MIN_FAQ}" --min-links "${MIN_INTERNAL_LINKS}" \
    --min-sources "${MIN_SOURCES}" --min-case-studies 0 \
    --seo-threshold 85 --eeat-threshold "${EEAT_SCORE_THRESHOLD}" || {
    echo "GATE QA FAIL: Agent 12 blocked article ${ARTICLE_NUM}"
    python scripts/mark_qa_failed.py --wordpress-report "${ARTICLE_DIR}/agent_11/wordpress_report.json" --gate QA || true
    ARTICLES_FAILED=$((ARTICLES_FAILED+1)); continue
  }
  python -m agents.agent_13_chief_editor \
    --qa-report "${ARTICLE_DIR}/agent_12/qa_report.json" \
    --article "$DRAFT" \
    --article-type "${ARTICLE_TYPE}" \
    --output "${ARTICLE_DIR}/agent_13/editor_report.json" || {
    echo "GATE EDITOR FAIL: Agent 13 blocked article ${ARTICLE_NUM}"
    python scripts/mark_qa_failed.py --wordpress-report "${ARTICLE_DIR}/agent_11/wordpress_report.json" --gate EDITOR || true
    ARTICLES_FAILED=$((ARTICLES_FAILED+1)); continue
  }

  # FIX 4: Production Gate -- 3 gates only
  echo "[${ARTICLE_NUM}] Production Gate (3-gate minimum)"
  python scripts/production_gate.py \
    --fact-check "${ARTICLE_DIR}/agent_05/fact_check_report.json" \
    --eeat-dir "${ARTICLE_DIR}/agent_06" \
    --wordpress-report "${ARTICLE_DIR}/agent_11/wordpress_validation_report.json" \
    --output "${ARTICLE_DIR}/production_gate_result.json" && {
    ARTICLES_PRODUCED=$((ARTICLES_PRODUCED+1))
    POST_ID=$(python3 -c "import json; r=json.load(open('${ARTICLE_DIR}/agent_11/wordpress_validation_report.json')); print(r.get('post_id','unknown'))" 2>/dev/null || echo "unknown")
    if [ "$DRAFT_ONLY" = "true" ]; then
      echo "DRAFT-ONLY MODE: skipping PRODUCED.json for article ${ARTICLE_NUM} -- WordPress draft ${POST_ID} stays a draft, topic will roll back to candidate"
    else
      # SPRINT 9 publish-invariant: terminal marker written ONLY after QA+editor+gate all pass.
      python3 -c "import json,sys; json.dump({'post_id': '${POST_ID}', 'article': ${ARTICLE_NUM}, 'produced': True}, open('${ARTICLE_DIR}/PRODUCED.json','w'))"
      # REAL PUBLISH (2026-07-17): the ONLY place a WordPress draft is ever
      # flipped to live 'publish' -- strictly gated inside the script itself
      # on a real (non-heuristic) QA PASS >= PUBLICATION_QUALITY_GATE (95),
      # imported from agent_12, never a second hardcoded copy. Best-effort/
      # non-blocking (same philosophy as mark_qa_failed.py above): a WP API
      # hiccup here must never fail the batch loop -- the post just stays a
      # draft if anything about the gate isn't crystal clear.
      python scripts/publish_if_qa_passed.py \
        --qa-report "${ARTICLE_DIR}/agent_12/qa_report.json" \
        --wordpress-report "${ARTICLE_DIR}/agent_11/wordpress_validation_report.json" \
        --draft-only "${DRAFT_ONLY}" || true
    fi
    echo "SUCCESS: Article ${ARTICLE_NUM} -- WordPress Draft ID: ${POST_ID}"
  } || {
    ARTICLES_FAILED=$((ARTICLES_FAILED+1))
    echo "Article ${ARTICLE_NUM} FAILED production gate"
  }
done

echo "===== BATCH COMPLETE: ${ARTICLES_PRODUCED} produced, ${ARTICLES_FAILED} failed ====="
if [ "${ARTICLES_PRODUCED}" -eq 0 ]; then
  echo "ERROR: No articles produced"
  exit 1
fi
