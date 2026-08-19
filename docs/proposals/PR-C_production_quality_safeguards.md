# PR C — Priorities 3-5: Production Throttle, Topic Selection & Anti-Thin-Content Safeguards (DRAFT PROPOSAL)

> **Draft proposal. Do NOT merge. Do NOT deploy. Do NOT push to main.** Human review required.
> Implements Priorities 3, 4, 5 from the NEXUS-14 audit (Issue #4). Companion to PR #5, PR-A, PR-B.

---

## Priority 3 — Maintain up to 6 articles/day WITHOUT sacrificing quality

### Problem identified
The 6/day target (3 morning + 3 afternoon) can pressure the pipeline into publishing weak articles just to hit the number.

### Root cause
The workflow targets a fixed batch size of 3; there is no explicit "publish only what passes" rule, so a batch that yields only 3 strong topics out of 6 could be back-filled with low-value topics to reach the count.

### Proposed fix — "publish-what-qualifies" (cap, not quota)
Treat **6 as a ceiling, never a quota**. Each batch generates candidates, runs all gates, and publishes **only** those that pass. If 3 pass, publish 3; if 4, publish 4; never generate filler to reach 6.

```yaml
production:
  max_articles_per_day: 6        # CEILING, not a target
  batches: { morning: 3, afternoon: 3 }   # max per batch
  publish_rule: "PUBLISH_ONLY_GATE_PASSING"
  backfill_to_hit_target: false  # never generate filler
  min_acceptable_per_day: 0      # 0 strong topics => publish 0; quality wins
  note: "If fewer topics meet the bar, publish fewer. Quality > volume."
```

### Risk assessment
Very low. Strictly reduces low-quality output. Worst case: some days publish <6 (acceptable and intended).

### SEO / quality / monetization impact
Positive across all three — Google rewards consistent quality over volume; thin filler is the main ranking and AdSense risk; fewer-but-stronger commercial pages convert better.

---

## Priority 4 — Best topics only (cluster-driven selection)

### Problem identified
Weak topics (low demand, low user value, duplicate intent) can enter the queue.

### Root cause
Topic scoring (pre-PR #5) was revenue-only; there was no cluster/authority lens and no explicit floor on user value + demand.

### Proposed fix — cluster-gated selection on top of the PR #5 balanced score
Only queue topics that (a) clear the balanced score floor AND (b) belong to a priority cluster AND (c) pass the PR-A duplication guard.

```yaml
topic_selection:
  use_balanced_score: true        # 40 user value / 25 intent / 15 demand / 10 affiliate / 10 authority (PR #5)
  min_balanced_score: 70
  min_search_demand: 500
  priority_clusters:
    - banking
    - credit_cards
    - credit_building
    - car_insurance
    - money_transfers
    - taxes
    - health_insurance
    - first_90_days
    - driver_license
  reject_if:
    - search_demand_below_min
    - user_value_below_floor
    - duplicate_intent           # delegated to Agent 17 (PR-A)
    - outside_priority_clusters_unless_pillar_support
```

### Risk assessment
Low. May shrink the candidate pool; mitigated because the nine clusters are broad. Cluster list is config-driven and easy to extend.

### SEO / quality / monetization impact
Positive — concentrating on nine high-intent clusters builds topical authority faster, raises average user value, and aligns content with the highest-commission verticals (banking, credit, insurance, money transfer, taxes).

---

## Priority 5 — Article quality safeguards (anti-thin / anti-generic / EEAT)

### Problem identified
The biggest risk is not too few articles, but articles that are repetitive, thin, generic, under-researched, too similar to existing content, or that fail EEAT.

### Root cause (from reading scripts/v2_quality_gate.py)
1. **Word-count drift:** Gate 01 still hardcodes `GATES_PILLAR word_count_min = 7000` and STANDARD `3500`, contradicting the YAML v3.1 cost-optimized tiers (PILLAR 4500 / STANDARD 4000 / OPPORTUNITY 3500) and PR #5. Must be reconciled.
2. **No "thin/generic" detector:** gates count words/FAQ/sources but never measure originality, repetition, or research depth.
3. **EEAT and SEO floors exist (>=90)** but there is **no OPPORTUNITY tier** in the gate file (only STANDARD/PILLAR), so a 3-tier system is only half-enforced.
4. **Internal-links min is still 5** in the gate (PR #5 raises the policy to 10).

### Proposed fix
A. **Reconcile Gate 01 word counts to the 3-tier YAML** and add an OPPORTUNITY gate set:
```python
GATES_STANDARD["word_count_min"]    = 4000   # was 3500
GATES_PILLAR["word_count_min"]      = 4500   # was 7000
GATES_OPPORTUNITY = {**GATES_STANDARD, "word_count_min": 3500, "faq_min": 8,
                     "sources_min": 3, "images_min": 3}
GATES = {"PILLAR": GATES_PILLAR, "STANDARD": GATES_STANDARD,
         "OPPORTUNITY": GATES_OPPORTUNITY}[article_type]
```
B. **Raise internal links** to match PR #5: `internal_links_min = 10` (inbound tracked separately).
C. **Add Gate 20 — Originality / Anti-Thin** (new, blocking):
```python
# Inputs from a new originality check (Agent 12 extension or standalone):
#   - duplicate_sentence_ratio (vs corpus)   -> must be < 0.15
#   - internal_repetition_ratio              -> must be < 0.10
#   - unique_data_points (real numbers/cites)-> must be >= 8
#   - template_similarity (vs last 5 posts)  -> must be < 0.50
origin = load_json_report(args.originality_report, "Originality")
checks = {
  "duplicate_sentence_ratio": origin.get("duplicate_sentence_ratio", 1) < 0.15,
  "internal_repetition_ratio": origin.get("internal_repetition_ratio", 1) < 0.10,
  "unique_data_points":        origin.get("unique_data_points", 0) >= 8,
  "template_similarity":       origin.get("template_similarity", 1) < 0.50,
}
gate20_pass = all(checks.values())
if not gate20_pass:
    all_failures.append(f"GATE 20 FAIL: thin/generic/repetitive content - {[k for k,v in checks.items() if not v]}")
```
D. **Keep EEAT >=90 and SEO >=90 as hard floors** (target >=95 for money pages per PR #5). Do **not** relax to increase production.

### Recommendation summary (how every article stays publication-quality)
- Real numbers + government sources required (existing Gate 06, raised research-depth via Gate 20 unique_data_points).
- Originality gate blocks template/repetition (Gate 20).
- Duplication guard blocks near-duplicates (PR-A).
- Country/category integrity (PR-B).
- Balanced topic selection prevents low-value topics entering (Priority 4).
- Publish-what-qualifies prevents filler (Priority 3).

### Files affected
- `docs/proposals/PR-C_production_quality_safeguards.md` — **this PR**
- Follow-up application targets: `scripts/v2_quality_gate.py` (word-count reconciliation, OPPORTUNITY tier, Gate 20, internal-links 10), `config/nexus14_v2_config.yaml` (production publish-rule, topic_selection), `agents/agent_01_seo_research.py` / `agent_03_content_planner.py` (cluster gating), new originality check feeding Gate 20.

### Risk assessment
Low–medium. Gate 20 needs a reliable originality signal; until calibrated, run it as **warning for 1-2 batches**, then flip to blocking. Word-count reconciliation must be confirmed as canonical (YAML v3.1 chosen, consistent with PR #5).

### Expected SEO impact
Strongly positive — originality + correct tiers + 10 internal links + cluster focus are exactly the levers that improve rankings and indexation.

### Expected content quality impact
Strongly positive — directly targets the thin/generic/repetitive failure modes.

### Expected monetization impact
Positive — higher-quality cluster pages rank and convert better; supports AdSense approval readiness; protects long-term affiliate revenue.
