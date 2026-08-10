# Page SEO-Title Tool — Safety Record

Built 2026-08-09/10 as part of the AdSense/SEO cleanup one-shot, Checkpoint C
(14 generic Page titles) preparation. Documents the gates in
`scripts/set_page_yoast_title.py`, for the same auditability reason every
other fix in this repo's `audit/pending_fixes/` directory is recorded.

## Why this tool exists

`apply_single_post_fix.py` (this repo's only prior WordPress-write tool)
is hardcoded to `/wp-json/wp/v2/posts/` and only ever writes the `content`
or `excerpt` field. It cannot touch WordPress Pages, and cannot touch any
Yoast SEO field — Yoast does not expose its SEO-title field through the
standard WP REST `meta` schema on this install (confirmed empty via
`OPTIONS /wp-json/wp/v2/pages`, unauthenticated, 2026-08-09). Yoast instead
exposes its own dedicated REST route pair — its SEO > Tools > Bulk Editor
screen:
- `GET /yoast/v1/bulk_editor/posts` — read title/description rows
- `POST /yoast/v1/bulk_editor/update_search` — write them

Phase A (`scripts/discover_yoast_page_title_field.py`, a strictly
read-only companion script, committed and run first) confirmed empirically
— not by assumption — that the per-row title field is named `seo_title`,
distinct from the plain WordPress post title. Observed directly against
page 46450 (Corrections Policy): `"seo_title": ""` (nothing custom set),
`"title": "Corrections Policy"` (the unrelated core WP field).

## Single-field principle

By explicit instruction, the write payload is deliberately minimal:
```json
{"items": [{"id": <page_id>, "seo_title": "<new value>"}]}
```
No `meta_description`, `focus_keyphrase`, `social_title`,
`social_description`, or `content_type` is ever included. If Yoast's
endpoint rejects this minimal shape, the tool stops and reports the exact
response — it does not retry with an enriched payload, and does not fall
back to any other write mechanism (no `PATCH /wp/v2/pages`, no direct
meta write, no wp-cli, no direct database access).

## Gate sequence

1. **READ** — core page object (`GET /wp/v2/pages/{id}?context=edit`),
   the Yoast bulk-editor row for that page, and the live public frontend
   HTML — all before any write.
2. **VERIFY EXPECTED BEFORE VALUE** — the observed `seo_title` must equal
   the caller-supplied `expected_current_value` exactly. Any mismatch:
   **STOP, no write attempted.**
3. **BACKUP** — full pre-write state (core object + Yoast row + frontend
   HTML) written to a timestamped JSON file, unconditionally, before the
   write call.
4. **WRITE ONE FIELD** — the single write call in the entire script:
   `POST /yoast/v1/bulk_editor/update_search` with the minimal payload
   above. Any HTTP error or exception here: **STOP, report the exact
   response, no retry, no alternate payload.**
5. **READ BACK** — re-fetch the core object, the Yoast row, and the live
   frontend HTML.
6. **VERIFY** — `seo_title` now equals the new value, AND every other
   Yoast-row field (`meta_description`, `focus_keyphrase`, `social_title`,
   `social_description`, `status`) is byte-identical to the pre-write
   backup, AND the core object's `slug`/`status`/content hash are
   byte-identical. Any divergence: **STOP, report exactly what changed.**
7. **FRONTEND CHECK** — an independent, unauthenticated GET of the live
   URL: HTTP 200; canonical tags, robots meta, meta description tag, H1
   count/text, and a hash of everything from `</head>` onward all
   compared byte-for-byte to the pre-write frontend snapshot and expected
   **unchanged**. The rendered `<title>` is the one thing expected to
   change — its new value is reported, never assumed to match a specific
   format. An HTTP 200 from the write call is never, by itself, treated
   as proof of success.

Exits 0 only if every gate passes. Any single gate failure exits non-zero
with the full diagnostic dump attached to the workflow run's artifact —
nothing is silently declared successful.

## Scope limits (hard, by construction)

- One page per run. No batch input is accepted anywhere in the script.
- The only write-capable HTTP call in the file is the single
  `POST /yoast/v1/bulk_editor/update_search` described above.
- Never touches: WordPress core `title`, `slug`, `status`, `excerpt`,
  `content`, canonical, robots, schema, author, template, featured image,
  date, or any Yoast field other than `seo_title`.

## Rollback procedure (documented, not executed as part of any run)

To revert a completed write, re-run the same tool with:
- `expected_current_value` = the `new_seo_title` that was just written
  (the tool's own gate 2 will refuse to run otherwise)
- `new_seo_title` = the original value captured in that page's
  `page_{id}_yoast_title_BEFORE.json` backup artifact from the original
  run

The same 8-gate sequence runs symmetrically in reverse. There is no
separate "undo" code path — the tool is reversible by construction, not
by a special case.
