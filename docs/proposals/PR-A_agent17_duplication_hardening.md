# PR A — Priority 1: Agent 17 Duplication Hardening (DRAFT PROPOSAL)

> **Draft proposal. Do NOT merge. Do NOT deploy. Do NOT push to main.** Human review required.
> Implements Priority 1 from the NEXUS-14 audit (Issue #4). Companion to PR #5.

## Problem identified

The system produced **duplicate Canada/USA drafts**. The current cannibalization protection (Agent 17 + Gate 16) is too weak to stop near-duplicates and does not detect country/category collisions at all.

## Root cause (from reading `agents/agent_17_cannibalization.py` and `scripts/v2_quality_gate.py`)

1. **AI can override a high mechanical score.** Agent 17 only sets `blocking=True` when `max_score >= REJECT_THRESHOLD (0.85)` **OR** the AI returns `REJECT_DUPLICATE`. A near-duplicate scoring 0.72–0.84 passes if the AI says `CREATE_NEW`. The detection floor (`SIMILARITY_THRESHOLD = 0.72`) only records a conflict; it does not block.
2. **No slug check.** Slugs are never compared, so two posts with near-identical slugs are not caught.
3. **No country / category check.** "Car Insurance for Newcomers in **Canada**" and "...in the **USA**" are different articles, but a title-similarity of ~0.8 plus the AI possibly merging them can mishandle them; conversely two same-country variants slip through. Country is never extracted or compared.
4. **Stopword list strips primary-keyword signal.** `extract_keywords` removes `best, top, guide, complete, new` etc., so "Best Bank Bonuses" vs "Bank Bonuses Guide" lose the very tokens that define the primary keyword, deflating `keyword_overlap`.
5. **Gate 16 trusts `blocking` only.** `v2_quality_gate.py` passes Gate 16 whenever `blocking == False` and the decision is in the allowed set — so a weak Agent 17 result auto-passes.

## Proposed fix

Strengthen Agent 17 to compute **five independent duplication signals** and **block when ANY exceeds its threshold**, regardless of the AI's opinion (AI becomes advisory, not an override). Add explicit **slug**, **near-duplicate title**, **primary-keyword**, **country**, and **category** checks. Generation **stops and requires manual review** when duplication risk exceeds threshold.

### New thresholds (config-driven)

```yaml
duplication_guard:
  title_similarity_block: 0.78      # was effectively 0.85 (AI could override)
  slug_similarity_block: 0.80
  primary_keyword_match_block: 0.90 # near-identical primary keyword
  near_duplicate_title_block: 0.82
  country_mismatch_to_category: BLOCK
  category_mismatch: BLOCK
  ai_can_override_mechanical_block: false   # AI is advisory only
  on_block: STOP_REQUIRE_MANUAL_REVIEW
```

### Code patch (drop-in additions to `agents/agent_17_cannibalization.py`)

```python
# --- NEW: country detection -------------------------------------------------
USA_TOKENS  = {"usa", "u.s.", "us", "america", "american", "irs", "ssn", "itin",
               "fdic", "uscis", "401k", "ira"}
CANADA_TOKENS = {"canada", "canadian", "cra", "rrsp", "tfsa", "gc.ca", "sin",
                 "newcomer to canada", "ontario", "quebec", "bc"}

def detect_country(text):
    t = text.lower()
    is_ca = any(tok in t for tok in CANADA_TOKENS)
    is_us = any(tok in t for tok in USA_TOKENS)
    if is_ca and not is_us: return "CA"
    if is_us and not is_ca: return "US"
    if is_ca and is_us:     return "BOTH"
    return "UNKNOWN"

# --- NEW: slug helpers ------------------------------------------------------
def slugify(title):
    s = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    return s

def slug_similarity(a, b):
    return SequenceMatcher(None, slugify(a), slugify(b)).ratio()

# --- NEW: primary keyword (do NOT strip best/top/guide for primary signal) --
def primary_keyword(title):
    # keep commercial modifiers; only drop pure stopwords
    drop = {'a','an','the','is','in','on','at','to','for','of','and','or','with','how','your','our'}
    return ' '.join(w for w in re.findall(r'[a-z0-9]+', title.lower())
                    if w not in drop)

def primary_keyword_match(a, b):
    return SequenceMatcher(None, primary_keyword(a), primary_keyword(b)).ratio()
```

Replace the decision block so a mechanical block cannot be overridden by the AI:

```python
new_country = detect_country(new_topic + ' ' + ' '.join(new_kws))
mechanical_block = False
block_reasons = []

for article in all_content:
    title = clean_title(article)
    tsim  = text_similarity(new_topic, title)
    ksim  = keyword_overlap(new_kws, extract_keywords(title))
    ssim  = slug_similarity(new_topic, article.get("slug", title))
    pksim = primary_keyword_match(new_topic, title)
    a_country = detect_country(title + ' ' + article.get("slug",""))

    if tsim  >= CFG["title_similarity_block"]:     mechanical_block = True; block_reasons.append(("title", title, tsim))
    if ssim  >= CFG["slug_similarity_block"]:      mechanical_block = True; block_reasons.append(("slug", title, ssim))
    if pksim >= CFG["primary_keyword_match_block"]:mechanical_block = True; block_reasons.append(("primary_keyword", title, pksim))
    # Same country + high title sim = true duplicate; different country = NOT a duplicate
    if a_country == new_country and tsim >= CFG["near_duplicate_title_block"]:
        mechanical_block = True; block_reasons.append(("near_dup_same_country", title, tsim))

# AI is advisory ONLY. It can RAISE caution but never clear a mechanical block.
if mechanical_block:
    decision, blocking = DECISIONS["REJECT"], True
    action = "BLOCKED: duplication risk exceeded threshold. Manual review required: " + str(block_reasons[:5])
elif ai_dec == DECISIONS["REJECT"]:
    decision, blocking = DECISIONS["REJECT"], True
    action = "BLOCKED by semantic analysis."
else:
    decision, blocking = ai_dec, False
    action = ai.get("recommended_action", "Proceed; content gap confirmed.")
```

> Note on country: different-country variants (CA vs US) are treated as **distinct, legitimate** articles (not duplicates), while **same-country** near-duplicates are blocked. This directly fixes the Canada/USA confusion without suppressing legitimate per-country coverage. Category assignment itself is enforced in **PR B**.

## Files affected

- `agents/agent_17_cannibalization.py` (logic) — patch shown above.
- `config/nexus14_v2_config.yaml` — add `duplication_guard` block.
- `scripts/v2_quality_gate.py` — Gate 16 should also fail if `block_reasons` is non-empty (defense in depth).
- This proposal doc: `docs/proposals/PR-A_agent17_duplication_hardening.md`.

## Risk assessment

- **Low–medium.** Lowering the block threshold may produce more "manual review" stops. That is the intended trade-off (false-positive stop > duplicate published). The `ai_can_override = false` change removes a silent failure mode.
- Country detection is keyword-based; `BOTH/UNKNOWN` cases fall back to title similarity, so no legitimate article is wrongly merged.

## Expected SEO impact

Eliminates cannibalization between near-duplicate pages (which split ranking signals), strengthening the surviving canonical page. Net positive for rankings.

## Expected content quality impact

Fewer thin/overlapping articles; each topic gets one strong canonical page. Positive.

## Expected monetization impact

Neutral-to-positive: consolidated authority pages convert better than fragmented duplicates; no change to affiliate/ebook density.
