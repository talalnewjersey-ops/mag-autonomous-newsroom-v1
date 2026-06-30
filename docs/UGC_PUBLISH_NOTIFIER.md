# UGC Publish Notifier (NEXUS-14 → UGC handoff)

When NEXUS-14 publishes a long-form article, the `nexus-ugc-enterprise` engine
wants to spin up short-form promotional content that drives traffic to the new
article. The two systems stay decoupled and communicate **only** through a
GitHub [`repository_dispatch`](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event)
event. This document covers the **sender** side, which lives in this repo.

## Why a separate notifier (not a step in `production_v2.yml`)

The production pipeline (`agent_11_wordpress_integration`) creates a WordPress
**draft** (`status: draft`) — a human reviews and publishes it later. There is
no automated "article is live" moment inside the pipeline, and a draft has no
public canonical URL. So firing the event from the batch loop would announce an
unpublished draft with a non-live URL.

Instead, [`.github/workflows/ugc-publish-notifier.yml`](../.github/workflows/ugc-publish-notifier.yml)
runs on a schedule, asks WordPress which posts are actually `status=publish`, and
announces each newly-live article with its **real** permalink and publish time.
The article pipeline is left untouched.

## What it sends

`event_type`: `nexus14_article_published`
`repository`: `talalnewjersey-ops/nexus-ugc-enterprise`

`client_payload` (validated by the receiver's `ArticlePublishedPayload`):

| Field | Source (WordPress REST) | Example |
|---|---|---|
| `source_system` | constant | `nexus-14` |
| `article_id` | `wp-<post.id>` | `wp-1842` |
| `canonical_url` | `post.link` (live permalink) | `https://moneyabroadguide.com/usa-banking-newcomers` |
| `article_ref` | `/wp-json/wp/v2/posts/<id>` | traceability ref |
| `published_at` | `post.date_gmt` + `Z` | `2026-06-30T06:00:00Z` |

## Idempotency

`scripts/ugc_publish_notifier.py` records announced post ids in a small JSON
state file (`.ugc_notified_ids.json`) that is persisted between runs by the
workflow's `actions/cache` step (rolling key + `restore-keys`). A post is never
announced twice. No WordPress plugin or post meta is required.

> **Known limitation:** if the Actions cache is evicted (≈7 days of inactivity)
> the state resets and the notifier could re-announce posts still returned by the
> WordPress query (most-recent 100 published). With hourly runs the cache stays
> warm, so this is unlikely. For a stronger guarantee, persist the state file via
> a committed file or a registered WordPress post meta — see TODO in the script.

## Required GitHub secret

Add **one** new secret (the WordPress secrets already exist for the pipeline):

| Secret | Status | Value |
|---|---|---|
| `UGC_DISPATCH_TOKEN` | **REQUIRED (new)** | Fine-grained PAT, repository access limited to **`talalnewjersey-ops/nexus-ugc-enterprise`**, permission **Contents: Read and write**. Use a dedicated bot account. |
| `WORDPRESS_URL` | existing | reused |
| `WORDPRESS_USERNAME` | existing | reused |
| `WORDPRESS_APP_PASSWORD` | existing | reused |

> The default `GITHUB_TOKEN` cannot dispatch to another repository, which is why
> a PAT with `contents:write` on the receiver repo is required.

## Manual test

1. Add the `UGC_DISPATCH_TOKEN` secret (above).
2. Ensure at least one article is `status=publish` in WordPress.
3. Run **UGC Publish Notifier** via *workflow_dispatch* (Actions tab).
4. Confirm the **NEXUS-14 Article Receiver** workflow runs and passes in
   `nexus-ugc-enterprise` (`[ACCEPTED]`).
5. Re-run the notifier → it should announce **0** posts (idempotency holds).
6. Run the offline tests: `pytest -v tests/test_ugc_publish_notifier.py`.
