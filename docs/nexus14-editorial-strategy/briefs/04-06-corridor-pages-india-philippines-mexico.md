# Briefs 4-6: Corridor Pages (US -> India / Philippines / Mexico)

- **Slugs:** `/send-money-to-india-from-usa-2026/`, `/send-money-to-philippines-from-usa-2026/`,
  `/send-money-to-mexico-from-usa-2026/`
- **Cluster check:** none of the three corridors currently has a dedicated page. The closest
  existing content is the general `/best-money-transfer-apps-immigrants/` pillar (Cluster A)
  and the USA->Canada corridor page (`/best-way-to-send-money-usa-to-canada-2026/`) — these
  three briefs follow that same corridor-page pattern, one level down from the pillar, same
  relationship as the Canada corridor page already has. No overlap risk between the three new
  pages themselves (distinct destination country = distinct primary keyword by construction),
  and no overlap with the pillar as long as each stays corridor-specific rather than repeating
  the general "best apps" roundup.
- **Primary keywords:** "send money to india from usa", "send money to philippines from usa",
  "send money to mexico from usa" (search volume/CPC: `[estimation: none available]` for all
  three — these are very likely high-volume given remittance corridor size, but do not state a
  number without a keyword-tool source)

## Shared structure (apply per corridor, swap country-specific data)

1. Quick Answer box — cheapest option for a $500/$1,000 transfer to that specific country, with
   the actual fee+FX numbers (see per-corridor facts below), refreshed on a defined cadence
   (recommend monthly given remittance-tax/FX volatility — flag as an ops requirement, not
   just a one-time write).
2. **1% federal remittance tax explainer callout** (effective Jan 1, 2026) — short, links out
   to the dedicated hub page (see Brief 7 below) rather than re-explaining it in full on every
   corridor page — avoids the exact kind of content duplication this whole audit is trying to
   eliminate.
3. Corridor-specific fee + FX comparison table — columns: `Provider | Transfer fee | FX margin
   vs. mid-market | Total cost on $500 | Total cost on $1,000 | Payout speed | Payout method
   (bank/cash pickup/mobile wallet)`
4. Corridor-specific payout methods section — this is the biggest per-country differentiator
   (e.g., mobile wallet payout matters far more for Philippines than for Mexico) — do not
   templatize this section, it needs real per-country research at write time.
5. Corridor calculator embed (reuse the existing homepage transfer-calculator pattern/JS if
   it can be parameterized by destination country — check with the engineering side before
   assuming this is a drop-in reuse; not verified in this session).
6. FAQ (from real PAA, per corridor — verify against live SERP, do not reuse the same FAQ
   across all three corridors even though the structure is shared):
   - What's the cheapest way to send $[amount] to [country]?
   - Is the new 1% remittance tax charged on transfers to [country]?
   - Which providers offer cash pickup in [country]?
7. Schema: Article + FAQPage + BreadcrumbList (per page)

## Verified facts (as supplied — FX margins and fee structures change; re-verify at write time per corridor)
- **Wise:** mid-market exchange rate + transparent upfront fee (consistent across corridors —
  the differentiator is payout method/speed per country, not pricing structure).
- **Remitly:** Economy vs. Express tiers — note which U.S. states are *not* subject to the new
  remittance tax (this is federal, not state, so re-verify this specific claim carefully before
  publishing — "states not subject to remittance tax" needs a precise, sourced explanation of
  the actual tax mechanism, not a vague carve-out claim).
- **Xoom:** $0 fee on eligible transfers; some transfers are tax-exempt under specific
  conditions — verify exact eligibility criteria per corridor before publishing a blanket claim.

## Affiliate
- Wise — Partnerize network — commission: **verify in-network**
- XE — Awin network — commission: **verify in-network**

## Internal links (per corridor page)
- `/best-money-transfer-apps-immigrants/` (pillar, links up)
- The 1% remittance tax hub page (Brief 7, links to and from)
- Cross-link the other two corridor pages only if genuinely useful to the reader (e.g., a
  "sending to multiple countries" note), not for link-count padding.

## Sources (official only, per corridor)
- CFPB remittance transfer rule (>$15 disclosure requirement, 30-minute cancellation window)
- World Bank Remittance Prices Worldwide database (for corridor-specific average cost benchmarks)
- IRS / Treasury guidance on the 1% remittance excise tax (effective Jan 1, 2026)
- Provider's own current fee schedule page, dated at retrieval (fee schedules change without notice)
