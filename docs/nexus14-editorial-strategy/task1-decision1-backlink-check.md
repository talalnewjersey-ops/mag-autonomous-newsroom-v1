# Decision 1 — Backlink/Ranking Check (Cluster C, USA credit cards)

**Date:** 2026-07-19. **Method used:** no Search Console access exists in this session
(not connected, no credentials found locally or in repo secrets for a GSC API). Per
your fallback instruction, checked internal links instead: full-text scan of all 51
published posts' rendered content for `<a href>` references to either candidate URL.
External backlinks (from other websites) are **not checked — no backlink-tool access
(Ahrefs/Moz/Semrush/etc.) exists in this session either.** This check covers internal
link equity only; treat external-backlink status as `[estimation: unavailable]`.

## Result (51/51 posts scanned, 0 errors, complete)

| Page | Internal inbound links found |
|---|---|
| `/best-credit-cards-for-newcomers-usa-2026/` (post 46281, the older "newcomers" page) | **6** |
| `/best-credit-cards-for-new-immigrants-no-ssn-complete-guide-for-usa-immigrants-2026/` (post 48709, the proposed canonical) | **0** |

Linking posts (all 6, pointing to 46281):
- `best-banks-newcomers-usa-2026`
- `how-to-get-itin-number-usa-2026`
- `how-to-build-credit-in-usa-without-ssn`
- `best-itin-friendly-bank-accounts-usa`
- `usa-budget-planner-2026`
- `cost-of-living-usa-2026`

These aren't random — they're exactly the topically-adjacent cluster (ITIN, credit-building,
budgeting) you'd expect to link into a "best credit cards" page, suggesting real, intentional
internal linking rather than incidental mentions.

## Decision: CONSOLIDATE — corrected 2026-07-19 (supersedes this doc's original same-day RE-SCOPE call)

**Original read of this data (superseded):** treated the 6-link page as the one needing
protection *from* a redirect, and proposed re-scoping it elsewhere while handing the
"canonical" label to the 0-link page. On reflection that has it backwards — it would have
moved the primary "no SSN / ITIN" keyword onto the orphaned page and left the actual linked
asset re-purposed, i.e. exactly the link-equity loss this check exists to prevent.

**Corrected decision:** consolidate the *weaker* asset into the *stronger* one.
`/best-credit-cards-for-newcomers-usa-2026/` (post 46281) is the stronger asset on every
signal this check can see — 6 real topical internal links, older (2026-07-09 vs. 2026-07-12),
and its title tag already targets "No SSN Needed" — so it becomes canonical, unchanged in
intent. `/best-credit-cards-for-new-immigrants-no-ssn-complete-guide-for-usa-immigrants-2026/`
(post 48709, 0 internal links) redirects into it via 301.

**Before redirecting:** graft into the canonical page any card/brand named only in the
no-SSN page's content, so nothing unique is lost in the merge. Not done in this
propose-only pass — listed as a pre-301 action item, not executed.

**No content rewrite needed** — this is a straightforward consolidation, not a re-scope. The
canonical page keeps its current intent; only the redirect and a content graft are required.
