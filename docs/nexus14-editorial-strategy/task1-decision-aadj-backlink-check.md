# Backlink/Ranking + Distinct-Intent Check — Cluster A-adj (Canada-outbound transfers)

**Date:** 2026-07-19. **Method:** identical to prior checks — no Search Console or
external-backlink-tool access. Full-text scan of all 51 published posts (51/51 scanned,
0 errors, complete) for `<a href>` references to each URL, plus publish `date` and word
count.

## Data

| URL | Inbound internal links | Publish date | Word count |
|---|---|---|---|
| `best-apps-to-send-money-internationally-from-canada-2026` (roundup) | 5 | 2026-06-13 | 7,675 |
| `wise-vs-remitly-canada-2026` (head-to-head) | **8** | **2026-06-12 (1 day older)** | **8,917 (longer)** |

Notably, the roundup page's own content **links to** `wise-vs-remitly-canada-2026` (one of
its 5 inbound links is FROM the other candidate) — the roundup treats it as a legitimate
sibling/spoke page, not as a redundant twin it's competing against.

## Distinct-intent check (performed first, per your instruction — not a default merge)

**Question: is "Wise vs Remitly Canada" a genuine standalone comparative search intent,
with clean head-to-head content, distinct from the general roundup?**

**Answer: YES.** Contrast with the `rbc-vs-scotiabank-vs-td` check (Cluster F), which
FAILED this same test:

| Signal | rbc-vs-scotiabank-vs-td (FAILED, merged) | wise-vs-remitly-canada (PASSES, kept) |
|---|---|---|
| Word count vs. its comparison point | 1,244 (thin) | 8,917 (the longest page in this cluster) |
| Internal links vs. the roundup | 1 (weak signal) | 8 (more than the roundup itself: 5) |
| Roundup's own title/meta already claims this comparison? | Yes (RBC vs Scotia vs TD explicitly in the roundup's SEO title) | No — the roundup's meta covers multiple providers generally, does not claim a dedicated Wise-vs-Remitly head-to-head |
| Content depth | Generic, overlapping | Specific savings figures ($12-$38 on $1,000), dedicated comparison structure |
| Query-pattern precedent | Weaker — "X vs Y vs Z bank" 3-way comparisons are less commonly searched as their own head-term than a 2-way brand comparison | "[Brand] vs [Brand]" is a well-established standalone comparison search pattern (this site's own USA-side equivalent structure exists too, though that one failed the test for different reasons — see Cluster A) |

All four checkable signals point the same direction here, and in the opposite direction from
the rbc-vs-scotiabank case. This is not a coin flip.

## Verdict: KEEP BOTH — no merge, no redirect, no canonical reassignment

`best-apps-to-send-money-internationally-from-canada-2026` stays the general Canada-outbound
roundup. `wise-vs-remitly-canada-2026` stays as a genuinely distinct, deep, dedicated
head-to-head comparison page — and per the data, it's actually the *stronger* asset of the
two (more links, older, longer), so even if a merge had been warranted, this check would
have flagged the currently-implied direction (fold the comparison page into the roundup) as
another inversion candidate. Since no merge is warranted at all, this doesn't come up in
practice, but noting it for completeness: **do not assume the roundup is automatically the
"bigger" page** — on every measured signal here, the comparison page is bigger.

**Cluster A-adj is now resolved** (previously flagged "unresolved — your call" in the
original Task 1 audit). No redirect entry added to `task2-redirects.csv` since no
consolidation applies.
