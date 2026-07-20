# Backlink/Ranking Check — Clusters B, F, G (same method as Cluster C)

**Date:** 2026-07-19. **Method:** identical to the Cluster C check — no Search Console or
external-backlink-tool access exists in this session. Full-text scan of all 51 published
posts' rendered content for `<a href>` references to each candidate URL (51/51 scanned, 0
errors, complete), plus each candidate's own `date` field (original publish date) as the
ancienneté/indexation-age proxy. **Internal links only — external backlinks and real GSC
ranking data remain `[estimation: unavailable]`.**

## Cluster B — USA banking

| URL | Inbound internal links | Publish date | Role |
|---|---|---|---|
| `open-bank-account-newcomer-usa-2026` | 7 | 2026-06-14 (older) | source (merges in) |
| `best-banks-newcomers-usa-2026` | 8 | 2026-06-22 | **canonical** |

**Not a clean inversion case like Cluster C.** The gap is 7 vs. 8 — within noise, not a
stark asymmetry. `open-bank-account` is actually 8 days *older*, which cuts the other way.
**Decision: keep the currently proposed direction** (`open-bank-account` → `best-banks-
newcomers-usa-2026`), but on a different basis than a link-count landslide: `best-banks-
newcomers-usa-2026` has marginally more links AND is the broader "best banks" roundup (the
correct home for a merged page per Task 1's scope reasoning), while `open-bank-account`'s
real value is its procedural how-to-open content — preserved via the graft step already
specified in Task 1, not lost. Flagging explicitly that this call rests on scope/depth, not
on a decisive link-count gap; if you weight "older page wins" more heavily than "broader
scope wins" for ties this close, this is the one pair worth a second look.

`best-itin-friendly-bank-accounts-usa` — not touched, distinct ITIN-document intent, per
Task 1, unaffected by this check (kept as-is).

## Cluster F — Canada banking

| URL | Inbound internal links | Publish date | Role |
|---|---|---|---|
| `best-newcomer-bank-accounts-in-canada-...` | 1 | 2026-07-13 (newest) | source (merges in) |
| `best-banks-newcomers-canada-2026` | **19** | **2026-03-05 (oldest by 4 months)** | **canonical** |
| `rbc-vs-scotiabank-vs-td-newcomers-canada-2026` | 1 | 2026-06-22 | source (merges in) |

**Confirms the current direction — no inversion.** `best-banks-newcomers-canada-2026` is not
just ahead, it's the dominant asset on this whole site for the newcomer-banking topic: 19
internal links (vs. 1 and 1) and published 4 months before either competitor. This is the
strongest signal found in any of the four clusters checked so far.

**`rbc-vs-scotiabank-vs-td` distinct-intent check (per your instruction, not a default
merge):** verified, not just assumed. Three points against treating it as a separate
standing intent: (1) the canonical page's own SEO title already claims this exact
comparison ("Scotiabank vs RBC vs TD Compared" — confirmed in the Task 1 audit); (2) only 1
internal link — no meaningful topical signal treating it as its own destination; (3) thin
at 1,244 words vs. the canonical's 2,589. **Conclusion: not a genuinely distinct intent —
merge stands**, the "verify, don't default-merge" bar is met by this evidence, not overridden
by it.

## Cluster G — Canada credit cards

| URL | Inbound internal links | Publish date | Role |
|---|---|---|---|
| `best-credit-cards-for-newcomers-in-canada-...` | 1 | 2026-07-13 (newer) | source (merges in) |
| `best-credit-cards-newcomers-canada-2026` | 4 | 2026-06-22 (older) | **canonical** |

**Confirms the current direction — no inversion.** 4 vs. 1 links, older page, consistent
signal on both axes. No change from the original Task 1 call.

## Cross-market oddity noticed (not part of this check's scope, flagging only)

`best-credit-cards-newcomers-canada-2026` (a Canada page) is itself linked from
`best-credit-cards-for-new-immigrants-no-ssn-...-usa-immigrants-2026` (a USA page) —
and separately, `best-banks-newcomers-canada-2026` is linked from
`best-way-to-send-money-usa-to-canada-2026` (also USA-side). Neither affects the decisions
above, but both look like the internal-linking step occasionally crosses USA/Canada market
boundaries where it probably shouldn't. Not investigated further — out of scope for this
consolidation pass, flagging for awareness only.

## Summary — same-day corrections vs. confirmations

| Cluster | Original direction | This check | Result |
|---|---|---|---|
| C (done previously) | page-2 canonical | 6 vs. 0 links | **INVERTED** |
| B | open-bank → banks-newcomers | 7 vs. 8 links (close) | **kept**, weaker signal than C |
| F | both → banks-newcomers-canada | 1/1 vs. 19 links | **confirmed**, strongest signal found |
| G | newer page → older page | 1 vs. 4 links | **confirmed** |
