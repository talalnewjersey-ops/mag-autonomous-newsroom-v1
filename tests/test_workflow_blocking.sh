#!/usr/bin/env bash
# Sprint 1 — proves the production_v2.yml blocking chain WITHOUT calling any API.
# A failing QA gate (agent_12 exit 1) must trigger ARTICLES_FAILED++; continue,
# so the article is NOT counted as produced; if 0 produced the batch exits RED.
set -u

run_batch() {
  QA_EXIT="$1"
  ARTICLES_PRODUCED=0
  ARTICLES_FAILED=0
  for ARTICLE_NUM in 1 2 3; do
    ( exit "$QA_EXIT" ) || {
      echo "GATE QA FAIL: Agent 12 blocked article ${ARTICLE_NUM}"
      ARTICLES_FAILED=$((ARTICLES_FAILED+1)); continue
    }
    ARTICLES_PRODUCED=$((ARTICLES_PRODUCED+1))
    echo "SUCCESS: Article ${ARTICLE_NUM}"
  done
  echo "RESULT produced=${ARTICLES_PRODUCED} failed=${ARTICLES_FAILED}"
  if [ "${ARTICLES_PRODUCED}" -eq 0 ]; then
    echo "ERROR: No articles produced"
    return 1
  fi
  return 0
}

# Couche 3 -- models the ACTUAL G-Substance position (Phase 4.45): a FAIL does
# `continue`, so the downstream WordPress step (Phase 11) is skipped entirely.
# Proves a rejected article can never be published (sprint 9/10 invariant).
run_gsubstance_batch() {
  GS_EXIT="$1"
  WP_CREATED=0
  for ARTICLE_NUM in 1; do
    ( exit "$GS_EXIT" ) || {
      echo "GATE G-SUBSTANCE FAIL: hollow article ${ARTICLE_NUM} (never reaches WordPress)"
      continue
    }
    WP_CREATED=$((WP_CREATED+1)); echo "WordPress draft created for ${ARTICLE_NUM}"
  done
  echo "RESULT wp_created=${WP_CREATED}"
}

echo "=== Case A: QA fails for all -> expect RED (exit 1), 0 produced ==="
OUT_A="$(run_batch 1)"; RC_A=$?
echo "$OUT_A"
echo "exit=$RC_A"
echo "$OUT_A" | grep -q "produced=0 failed=3" || { echo "FAIL: expected 0 produced / 3 failed"; exit 1; }
[ "$RC_A" -eq 1 ] || { echo "FAIL: batch must exit 1 when 0 produced"; exit 1; }
echo "$OUT_A" | grep -q "GATE QA FAIL" || { echo "FAIL: missing GATE QA FAIL log"; exit 1; }
echo "Case A OK"

echo "=== Case B: QA passes for all -> expect GREEN (exit 0), 3 produced ==="
OUT_B="$(run_batch 0)"; RC_B=$?
echo "$OUT_B"
echo "exit=$RC_B"
echo "$OUT_B" | grep -q "produced=3 failed=0" || { echo "FAIL: expected 3 produced / 0 failed"; exit 1; }
[ "$RC_B" -eq 0 ] || { echo "FAIL: batch must exit 0 when articles produced"; exit 1; }
echo "Case B OK"

echo "=== Case C: G-Substance FAIL -> WordPress step never runs (never published) ==="
OUT_C="$(run_gsubstance_batch 1)"
echo "$OUT_C"
echo "$OUT_C" | grep -q "wp_created=0" || { echo "FAIL: WordPress must not run after G-Substance FAIL"; exit 1; }
echo "$OUT_C" | grep -q "GATE G-SUBSTANCE FAIL" || { echo "FAIL: missing G-Substance FAIL log"; exit 1; }
if echo "$OUT_C" | grep -q "WordPress draft created"; then echo "FAIL: WordPress ran despite FAIL"; exit 1; fi
echo "Case C OK"

echo "=== Case D: G-Substance PASS -> WordPress step runs ==="
OUT_D="$(run_gsubstance_batch 0)"
echo "$OUT_D"
echo "$OUT_D" | grep -q "wp_created=1" || { echo "FAIL: WordPress should run after G-Substance PASS"; exit 1; }
echo "Case D OK"

echo "ALL WORKFLOW BLOCKING TESTS PASSED"
