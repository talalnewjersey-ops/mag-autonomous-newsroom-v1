# Support ticket: HTTP 403 on moneyabroadguide.com from GitHub Actions CI (Hostinger hCDN/WAF)

## Domain
moneyabroadguide.com

## Summary

Our GitHub Actions CI pipeline is being blocked with **HTTP 403** on every request to moneyabroadguide.com — both **read** (public REST API GET requests) and **write** (authenticated media upload / post creation) — while the same site works normally for regular visitor traffic. The response is not a WordPress error; it is an **HTML interstitial/challenge page** served by your edge (`server: hcdn`), which strongly suggests your WAF/CDN layer is blocking our CI's outbound IP range, not WordPress itself rejecting the request.

## Evidence: this is an edge/WAF response, not a WordPress application error

Every blocked response body starts with:

```html
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta http-equiv="X-UA-Compatible" content="IE=Edge">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex,nofollow">
<meta http-equiv="refresh" content="30">
<link rel="preconnect" href="https://fonts.googleapis.com">
...
```

This is an interstitial page (`refresh: 30s`, `noindex,nofollow`) — a normal WordPress REST error would instead return clean JSON like `{"code":"rest_forbidden","message":"..."}`. Every blocked response also carries `server: hcdn` and an `x-hcdn-request-id` header, confirming it's served by Hostinger's edge/CDN layer before reaching the origin.

**The block is not limited to REST API endpoints.** During the same run, our fact-checking step attempted to verify the plain homepage URL `https://moneyabroadguide.com` (no REST path at all) and received the same 403 — indicating the block applies to the CI's IP/traffic pattern broadly, not to a specific endpoint or REST route.

## Blocked endpoints (both read and write)

| Direction | Method | Endpoint | Purpose |
|---|---|---|---|
| Read | GET | `/wp-json/wp/v2/posts` | Fetch published/draft posts (internal linking, cannibalization check) |
| Read | GET | `/wp-json/wp/v2/pages` | Fetch methodology pages (EEAT internal links) |
| Read | GET | `/` (homepage, no path) | Fact-check URL liveness check |
| Write | POST | `/wp-json/wp/v2/media` | Upload generated article images (authenticated, `WORDPRESS_APP_PASSWORD`) |
| Write | POST | `/wp-json/wp/v2/posts` | Create draft post (authenticated, `WORDPRESS_APP_PASSWORD`) |

## Affected time range (most recent occurrence)

**2026-07-11, 13:49:18 UTC -- 14:08:49 UTC** (run duration ~20 minutes, GitHub Actions run ID `29154971226`, workflow `production_v2.yml`, job "Production Batch -- 3 Articles"). This is a **recurring** condition, not a one-off: the same 403 pattern first appeared earlier the same day in run `29149027820` (2026-07-11, 10:14:28 -- 10:37:45 UTC) — two independent CI runs, roughly 3 hours apart, both fully blocked.

## Captured request-IDs / ray-IDs (this occurrence)

All in the format `<hash>-phx-edge{N}` — note **multiple distinct edge nodes** (edge6, edge8, edge9) all returning the same block, suggesting this is applied consistently across your Phoenix (phx) edge pool, not one misbehaving node.

| Timestamp (UTC) | Endpoint | x-hcdn-request-id |
|---|---|---|
| 2026-07-11T13:49:59 | GET /wp-json/wp/v2/posts | `05c57c75f4a26b646124059f9df7b998-phx-edge9` |
| 2026-07-11T13:52:48 | GET /wp-json/wp/v2/pages | `8c54e9e6d7a522b0334a69b2783e93d7-phx-edge6` |
| 2026-07-11T13:53:02 -- 13:53:34 | POST /wp-json/wp/v2/media (x5) + POST /wp-json/wp/v2/posts | *(request-id not yet captured on this write-path client -- see "Known gaps" below)* |
| 2026-07-11T13:54:13 | GET /wp-json/wp/v2/posts | `e0965c93578d28b583e48d1297a0d678-phx-edge9` |
| 2026-07-11T13:57:35 | GET /wp-json/wp/v2/pages | `fa387a1d26485be81d1ca5e92e38e596-phx-edge6` |
| 2026-07-11T13:57:36 | GET /wp-json/wp/v2/posts | `4f9b8c62239c1ec3d64aedefb675509c-phx-edge8` |
| 2026-07-11T14:00:47 | GET /wp-json/wp/v2/pages | `8a080066b3fe803ab7d3268f9e269da0-phx-edge6` |
| 2026-07-11T14:01:20 | GET /wp-json/wp/v2/posts | `a7b56b963cfc0880e6b34c29660f1b42-phx-edge6` |
| 2026-07-11T14:05:19 | GET /wp-json/wp/v2/pages | `9696af53020405aa3ec984b65245ea24-phx-edge9` |
| 2026-07-11T14:05:19 | GET /wp-json/wp/v2/posts | `40beea016123bf722b3d8d9dc223438f-phx-edge9` |
| 2026-07-11T14:08:48 | GET /wp-json/wp/v2/pages | `301f2279dc08d987bcbfd877a9c55ede-phx-edge9` |

Also observed via a separate client in both affected runs (`agent_17_cannibalization`, using the `requests` library, not the client that was just fixed to capture headers): repeated `403 Client Error: Forbidden` on `GET /wp-json/wp/v2/posts?status=publish` and `?status=draft`, at 10:15:08/10:15:10 UTC (run `29149027820`) and 13:49:21/13:53:36/14:00:50 UTC (run `29154971226`, this occurrence) — this client does not currently capture headers, so no request-id is available for these specific hits, but the timing and endpoint match the pattern above exactly.

## Known gaps in our own evidence (for transparency)

- **GitHub Actions runner source IP**: not currently captured by our pipeline. GitHub-hosted runners use dynamic/ephemeral IPs drawn from Microsoft Azure's published ranges (`https://api.github.com/meta`, `actions` key) — we do not pin or log the specific IP per run today. If Hostinger's WAF logs can be searched by timestamp + `x-hcdn-request-id` instead of source IP, that should be sufficient to locate the exact block decision; otherwise we can add an IP-logging step to a future run if it would help your investigation.
- **Request-id on the write path** (image upload / post creation, `agent_10`/`agent_11`): these use a different, older HTTP client that does not yet capture response headers on error (unlike the read path, fixed 2026-07-11). We can add the same header capture there if a request-id is needed for the specific write-path 403s (timestamps above are solid; exact request-ids for the 5 image uploads + 1 post-creation call in this run are not available).
- **User-Agent strings sent by our CI** (in case it helps you search WAF logs by UA instead of IP):
  - Read path (posts/pages fetch): `NEXUS-14-agent04/1.0`
  - Write path (media upload, post creation): `NEXUS-14/3.0`

## What we're asking

1. Please check your WAF/hCDN edge logs for the request-IDs above (or the time range 2026-07-11 13:49-14:09 UTC) and confirm whether GitHub Actions CI traffic to this domain is being blocked by a rule (bot protection, rate limiting, geo/ASN block, etc.).
2. If confirmed, please advise on the correct way to allowlist this legitimate automated traffic (a dedicated API user-agent allowlist, an ASN/IP-range allowlist for GitHub Actions, a WAF rule exception for the `/wp-json/` path with valid Application Password auth, or another mechanism you'd recommend).
3. This has been recurring across multiple CI runs on 2026-07-11 (not a one-off blip) and is currently blocking our editorial pipeline's normal WordPress draft-creation and image-upload workflow entirely.

Happy to provide the full raw CI logs for any of the runs referenced above if useful.
