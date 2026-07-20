# Task 1 — Cannibalization Audit (VERIFIED, page-level)

**Method:** fetched each live URL via `wp-json/wp/v2/posts/{id}`, read `title.rendered`,
`yoast_head_json.title` (actual SEO title tag), `yoast_head_json.description` (meta
description), word count (stripped `content.rendered`), and `modified` date. Report only —
nothing changed on the site.

**Caveat on FAQ schema:** `yoast_head_json.schema` did not surface `FAQPage` on any of the
25 pages checked, including pages known to have an on-page FAQ section. The site runs Rank
Math, not Yoast — `yoast_head_json` looks like a compatibility shim that may not carry Rank
Math's own JSON-LD injection. Treat "FAQ schema" as **unverified, not "absent"** until
checked by view-source on a live page or a Rank Math-native export.

**Caveat on all numbers:** no search-volume, CPC, or keyword-difficulty data source is wired
into this repo (no GSC/keyword-tool credentials found). Every priority call below is a
content/overlap judgment, not a traffic-value judgment — flag as `[estimation: none available]`
wherever volume would normally inform the call.

---

## Systemic finding (not in the original brief, discovered during verification)

Six of the newer posts share **byte-identical templated SEO metadata**:

> `"Complete guide to {keyword} for {market} immigrants in 2026. Compare top options, fees, and requirements."`

Affected: `48842` (Wise vs XE vs OFX vs Remitly), `48709` (credit cards no SSN), `48733`
(newcomer bank accounts Canada), `48747` (credit cards newcomers Canada), `48682` (car
insurance), `48384` (HISA international students). This is very likely the same defect
diagnosed earlier this session on post 48870: `agent_16_publishing_optimization` emitted an
**empty** `title`/`keyword`/`seo_title` (`output/article_1/agent_16/publishing_optimizer.json`
had `"title": "", "seo_title": " | MoneyAbroadGuide.com"`), and something downstream falls
back to a generic template instead of failing loudly. This degrades differentiation between
pages independently of topic overlap — a real page could have a unique angle and still read
as a duplicate to Google because its title tag/meta are generic boilerplate. **Recommend a
follow-up ticket** (not in scope of Task 4's gate, since it's a metadata-generation bug, not
a topic-selection bug) to make `agent_16` fail the run instead of silently degrading to
placeholder-looking copy — arguably this should feed the same anti-placeholder gate (`GATE
D`) that already blocks broken title-case acronyms.

---

## CLUSTER A — USA money transfer (HIGH)

| URL | Title tag (live) | Meta description (live) | Words | Modified |
|---|---|---|---|---|
| `/best-money-transfer-apps-immigrants/` | Best Money Transfer Apps for Immigrants (2026) - Money Abroad Guide | Compare Wise, Remitly, OFX and more by fees, exchange rates and speed | 3,395 | 2026-06-27 |
| `/best-wise-vs-xe-vs-ofx-vs-remitly-.../` | Best Wise Vs Xe Vs Ofx Vs Remitly: Complete Guide for USA Immigrants (2026) | Complete guide to wise vs xe vs ofx vs remitly... *(generic template, see above)* | 4,030 | 2026-07-17 |
| `/best-way-to-send-money-usa-to-canada-2026/` | Send Money from USA to Canada 2026: Cheapest Transfer Methods (Wise saves $38) | Wise is cheapest (saves $38 on $1,000 vs bank wire)... | 10,580 | 2026-07-18 |

**Shared primary intent:** page 1 and page 2 both target "compare Wise / Remitly / OFX /
XE for [USA] immigrants" — same 4 providers, same head-term intent, no differentiation in
scope. Page 3 is genuinely different: it's corridor-specific (USA→Canada), 2.6–3x deeper,
and already carries corridor-specific proof points (the "$38" claim) — **it does not need
re-scoping, it is already correctly scoped as corridor long-tail.** The brief's suggestion to
"re-scope USA→Canada to corridor long-tail" is already satisfied by the existing page.

**Verdict:** MERGE (2→1) | KEEP (3)
**Canonical:** `/best-money-transfer-apps-immigrants/` absorbs `/best-wise-vs-xe-vs-ofx-vs-remitly-.../` via 301.

### CLUSTER A-adj — Canada-side transfer (found during verification, not in original brief)

| URL | Title tag | Words | Modified |
|---|---|---|---|
| `/best-apps-to-send-money-internationally-from-canada-2026/` | Best Apps to Send Money from Canada 2026 \| Top Picks | 7,675 | 2026-07-11 |
| `/wise-vs-remitly-canada-2026/` | Wise vs Remitly Canada 2026: Best Wise Alternative & Money Transfer Comparison | 8,917 | 2026-07-18 |

**Verdict (RESOLVED 2026-07-19 — see `task1-decision-aadj-backlink-check.md`): KEEP BOTH,
no merge.** Distinct-intent check performed (not defaulted to merge, matching the same bar
applied to `rbc-vs-scotiabank-vs-td` in Cluster F): `wise-vs-remitly-canada-2026` passes —
it's a dedicated, deep head-to-head comparison (specific $12-$38 savings figures, not a
generic overlap), and on every measured signal (8 internal links vs. the roundup's 5, 1 day
older, 8,917 vs. 7,675 words) it's actually the *stronger* of the two pages, not a redundant
duplicate. This is the opposite outcome from `rbc-vs-scotiabank-vs-td`, which failed the same
test (thin, 1 internal link, its comparison already claimed by the target page's own title) and
got merged. No redirect, no canonical change for this cluster.

---

## CLUSTER B — USA banking / ITIN (HIGH)

| URL | Title tag | Meta description | Words | Modified |
|---|---|---|---|---|
| `/best-banks-newcomers-usa-2026/` | Best Banks for Newcomers to the USA (2026 Complete Guide) | banks accepting ITIN or passport, how to avoid fees, steps to open | 6,442 | 2026-07-18 |
| `/open-bank-account-newcomer-usa-2026/` | How to Open a Bank Account as a Newcomer in the USA (2026 Guide) | required documents, best banks for immigrants, SSN vs ITIN | 5,751 | 2026-07-18 |
| `/best-itin-friendly-bank-accounts-usa/` | Best ITIN Bank Accounts for Immigrants (2026) | Open a checking account without an SSN at top banks, credit unions & fintechs | 6,527 | 2026-07-12 |

**Shared primary intent:** page 1 (best banks/fees/features) and page 2 (how-to-open,
documents, SSN-vs-ITIN) both explicitly claim "best banks for immigrants" territory in their
own meta descriptions — confirmed overlap on the roundup angle. Page 2's procedural content
(documents checklist, step-by-step) is real unique value worth preserving inside page 1
rather than discarding. Page 3 (ITIN-specific document/eligibility angle) is distinct enough
from page 1's general fees/features framing to stand alone, matching the brief's proposal.

**Verdict:** MERGE (2→1, preserve the how-to/documents section as a new H2 on the target) | KEEP (1, 3)
**Canonical:** `/best-banks-newcomers-usa-2026/` (fees/features) · `/best-itin-friendly-bank-accounts-usa/` (ITIN documents)

---

## CLUSTER C — USA credit cards (HIGH)

| URL | Title tag | Meta description | Words | Modified |
|---|---|---|---|---|
| `/best-credit-cards-for-newcomers-usa-2026/` | Best Credit Cards for Newcomers USA 2026 (No SSN Needed) | Petal 2, Discover, Deserve EDU, Cap One reviewed | 4,466 | 2026-07-09 |
| `/best-credit-cards-for-new-immigrants-no-ssn-.../` | Best Credit Cards For New Immigrants No Ssn: Complete Guide (2026) | *(generic template)* | 4,544 | 2026-07-12 |

**Shared primary intent:** page 1's own title tag already says **"No SSN Needed"** — this is
not adjacent overlap, this is the same primary keyword ("credit cards for newcomers/immigrants,
no SSN") on two separate URLs. `SequenceMatcher` similarity on the raw titles is only 0.59
(see Task 4 evidence) despite this being a confirmed duplicate — direct proof that lexical
similarity alone cannot be trusted to catch this class of duplicate.

**Verdict (DECISION 1, corrected 2026-07-19 — see `task1-decision1-backlink-check.md`):
CONSOLIDATE.** Backlink check (internal-link scan, no GSC access available): page 1 has 6
real internal inbound links (from the ITIN, credit-building, and budgeting cluster) and is
older/more indexed; page 2 has 0. Redirecting page 2 into page 1 loses no link equity;
re-scoping page 1 away from its current "no SSN" intent would have orphaned those 6 links
instead — corrected from an earlier same-day call that had this backwards.
**Canonical:** `/best-credit-cards-for-newcomers-usa-2026/` (page 1) — already carries the
exact "no SSN" title, more specific brand list, older/more indexed, and the internal-link
equity. Before redirecting, graft into page 1 any card/brand named only in page 2's content.

---

## CLUSTER D — USA insurance

| URL | Words | Modified |
|---|---|---|
| `/best-car-insurance-for-foreign-drivers-and-international-students-.../-4` | 4,480 | 2026-07-12 |

**Confirmed:** exactly **one** live post matches this topic (checked against the full list of
51 published slugs — no `-2`/`-3` variants are live). `data/topic_registry.json` has exactly
one entry for `us-car-insurance-foreign-drivers-students`, `status: published`, `post_id:
48682` — no duplicate or orphaned queue rows for this topic. The `-4` in the slug is WordPress's
own slug-collision counter from prior *WordPress-side* draft attempts (drafts/trash aren't
visible via the public REST API, so their existence can't be confirmed without wp-admin
access — but the registry itself shows no re-selection risk going forward, since `published`
is already in `EXCLUDED_STATUSES`).

**Verdict:** no action needed. Clean.

---

## CLUSTER E — USA taxes

| URL | Title tag | Meta description | Words | Modified |
|---|---|---|---|---|
| `/taxes-for-new-immigrants-to-the-usa-2026/` | Taxes for New Immigrants to the USA (2026): Complete IRS Guide | resident vs nonresident alien, dual-status return, FBAR, **Form 1040-NR** | 2,532 | 2026-07-08 |
| `/us-expat-tax-filing-guide-2026/` | US Expat Tax Guide 2026: FBAR, Form 2555 & More | Complete handbook for **Americans living abroad**. FBAR, **Form 2555**, FATCA, foreign tax credits | 8,531 | 2026-07-09 |
| `/us-bank-interest-tax-nonresident-alien/` | US Bank Interest Tax for Non-Resident Aliens 2026 | HYSA tax rules, **Form 1042-S** and withholding | 4,488 | 2026-07-12 |

**Shared primary intent:** this is a **false-positive cluster**, not real cannibalization.
Page 2 serves the *opposite* audience — Americans living abroad (outbound), using an entirely
different form set (Form 2555 foreign earned income exclusion, FATCA) — vs. pages 1 and 3,
which serve immigrants arriving *into* the USA (inbound), using Form 1040-NR / 1042-S. The
"resident vs nonresident alien" phrase appears in both because it's a genuinely shared legal
concept, not a shared search intent. Pages 1 and 3 have real but limited overlap (both touch
residency status) — page 3's Form-1042-S/bank-interest angle is a legitimate narrow spoke off
page 1's broader filing-overview pillar, not a duplicate.

**Separate flag (audience/strategy, not cannibalization):** page 2 (`us-expat-tax-filing-guide-2026`)
targets Americans abroad — this is arguably **off-strategy** against the site's stated audience
("immigrants and newcomers in USA and Canada" per the project's CLAUDE.md), not a duplicate-content
problem. Worth a separate decision: keep as a deliberate adjacent vertical (different monetization
angle — expat tax software affiliates), or deprioritize. Not resolved here.

**Verdict:** KEEP all three. No merge, no redirect.

---

## CLUSTER F — Canada banking (HIGH — messier than the brief assumed)

| URL | Title tag | Words | Modified |
|---|---|---|---|
| `/best-banks-newcomers-canada-2026/` | Best Banks for New Immigrants & Newcomers Canada 2026: **Scotiabank vs RBC vs TD Compared** | 2,589 | 2026-07-08 |
| `/best-newcomer-bank-accounts-in-canada-.../` | Best Newcomer Bank Accounts In Canada: Complete Guide *(generic template)* | 4,128 | 2026-07-15 |
| `/rbc-vs-scotiabank-vs-td-newcomers-canada-2026/` | **RBC vs Scotiabank vs TD** for Newcomers Canada 2026: Which Big Bank Wins? | 1,244 | 2026-07-12 |
| `/student-bank-account-canada-newcomers-2026/` | How to Open a Bank Account in Canada as an International Student | 6,592 | 2026-07-12 |

**Shared primary intent — three-way overlap, not two-way:** page 1's own SEO title *already*
says "Scotiabank vs RBC vs TD Compared" — meaning page 1 already substantially covers the
exact comparison that page 3 is a standalone (and much thinner, 1,244-word) page for. Page 2
duplicates page 1's general "best accounts for newcomers" roundup framing. This is a genuine
three-page overlap on "which big bank is best for a Canadian newcomer," not the two-page
overlap the brief assumed. Page 4 (international students) is confirmed distinct — different
persona, matches the brief.

**Verdict:** MERGE (2→1, 3→1) | KEEP (1, 4)
**Canonical:** `/best-banks-newcomers-canada-2026/` — already the most complete on the exact
"RBC vs Scotiabank vs TD" query the thin page 3 was trying to own; absorb page 3's content as
a dedicated comparison-table section if it has anything page 1 lacks (it's thin, so likely
just tightens page 1, doesn't need much grafting).

### CLUSTER F-adj — found during verification, not in original brief

| URL | Title tag | Words |
|---|---|---|
| `/bank-newcomer-bonus-300-cad-canada-2026/` | Best Bank Welcome Bonus Newcomers Canada 2026: $300 CAD Compared | 1,677 |
| `/best-banks-iranian-newcomers-canada-2026/` | Best Banks for Iranian Newcomers in Canada (2026): Which Banks Accept You? | 3,668 |

**Assessment:** the bonus-offer page is a real long-tail angle (specific $ promos, updates
faster than an evergreen roundup) but is thin (1,677 words) and has partial overlap risk with
whatever "signup bonus" subsection page 1 already carries — light flag, not a hard merge call,
your judgment. The Iranian-newcomers page is a genuinely distinct audience segment (sanctions/
passport-acceptance is a real, different question) — no overlap concern.

**Verdict:** KEEP both, no action. (Flagged for awareness only.)

---

## CLUSTER G — Canada credit cards (HIGH)

| URL | Title tag | Meta description | Words | Modified |
|---|---|---|---|---|
| `/best-credit-cards-for-newcomers-in-canada-.../` | Best Credit Cards For Newcomers In Canada: Complete Guide *(generic template)* | 4,214 | 2026-07-15 |
| `/best-credit-cards-newcomers-canada-2026/` | Best Credit Cards for Newcomers in Canada (2026 Complete Guide) | newcomer program cards, secured cards, student cards, no Canadian credit history | 5,769 | 2026-07-17 |

**Shared primary intent:** near-identical title/intent, confirmed duplicate. Page 2 has the
real (non-templated) meta description and more specific content signals (program cards vs.
secured vs. student cards) and is more recently substantively updated.

**Verdict:** MERGE (1→2)
**Canonical:** `/best-credit-cards-newcomers-canada-2026/`

---

## CLUSTER H — Canada savings

| URL | Title tag | Meta description | Words | Modified |
|---|---|---|---|---|
| `/high-interest-savings-newcomers-canada-2026/` | Best High-Interest Savings Accounts for Newcomers to Canada (2026) | CDIC protection, **the HISA vs TFSA difference**, CRA taxation | 4,266 | 2026-07-08 |
| `/best-high-interest-savings-accounts-.../international-students-.../` | *(garbled title — "Canada – International Students Immigrants", generic template)* | 4,146 | 2026-07-08 |
| `/tfsa-newcomers-canada-2026/` | Best TFSA Accounts for Newcomers to Canada (2026) | who qualifies, the $7,000 limit, room isn't pro-rated | 1,724 | 2026-07-08 |

**Shared primary intent:** page 1 and page 3 have light overlap (page 1's meta explicitly
covers "HISA vs TFSA difference") but page 3 is a legitimate deep-dive spoke (contribution
limits, eligibility mechanics) — matches the brief's "keep TFSA" call, no action. Page 2
(international-students HISA) is a persona-specific variant — **for consistency with Cluster
F's precedent** (where the international-student banking page was confirmed as a legitimately
distinct persona page, not a duplicate), recommend **KEEP, not merge** — same logic applies
here. Separately: page 2's title/meta are broken (mangled "Canada – International Students
Immigrants" string, generic templated description) — this is a **data-quality fix, not a
cannibalization fix**. Flagging for a title/meta cleanup pass, out of scope for the redirect
map.

**Verdict:** KEEP all three (no redirects). Separate action: fix page 2's title/meta.

---

## Summary table

| Cluster | Verdict | Canonical | Pages to 301 |
|---|---|---|---|
| A | MERGE 1, KEEP 1 | `/best-money-transfer-apps-immigrants/` | `best-wise-vs-xe-vs-ofx-vs-remitly-...` |
| A-adj | KEEP BOTH (resolved 2026-07-19, distinct-intent check passed) | — | — |
| B | MERGE 1, KEEP 2 | `/best-banks-newcomers-usa-2026/` + `/best-itin-friendly-bank-accounts-usa/` | `open-bank-account-newcomer-usa-2026` |
| C | MERGE (Decision 1, corrected 2026-07-19) | `/best-credit-cards-for-newcomers-usa-2026/` | `best-credit-cards-for-new-immigrants-no-ssn-...` |
| D | Clean, no action | — | — |
| E | KEEP all (false-positive cluster) | — | — |
| F | MERGE 2, KEEP 2 | `/best-banks-newcomers-canada-2026/` | `best-newcomer-bank-accounts-in-canada-...`, `rbc-vs-scotiabank-vs-td-newcomers-canada-2026` |
| F-adj | KEEP both, flagged only | — | — |
| G | MERGE 1 | `/best-credit-cards-newcomers-canada-2026/` | `best-credit-cards-for-newcomers-in-canada-...` |
| H | KEEP all, fix metadata on 1 page | — | — |

**Net: 6 confirmed 301 candidates, all clusters resolved as of 2026-07-19 (Cluster C corrected to MERGE; Cluster A-adj resolved to KEEP BOTH after a distinct-intent check). Zero clusters remain unresolved.**
