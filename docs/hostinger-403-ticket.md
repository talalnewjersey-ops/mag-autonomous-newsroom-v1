# Support ticket: intermittent HTTP 403 on moneyabroadguide.com from GitHub Actions CI (Hostinger hCDN)

## Domain
moneyabroadguide.com

## Summary

Our GitHub Actions CI pipeline hits **HTTP 403** on the large majority of requests to moneyabroadguide.com during full production runs — both **read** (public REST API GET requests) and **write** (authenticated media upload / post creation) — while the same site works normally for regular visitor traffic. The response is not a WordPress error; it is an **HTML interstitial page** served by your edge (`server: hcdn`).

**Important update from our own investigation**: we checked hPanel and the CDN "Security Level" is already set to "Essentially off" with no IPs blocked — so this is **not** a manually-configured, always-on IP block. We also just ran a lightweight, single-shot diagnostic (3 requests: unauthenticated GET, authenticated GET, authenticated POST creating a real draft) from an actual GitHub Actions runner, at 2026-07-11 14:45-14:46 UTC, and **all 3 succeeded** (200, 200, 201) — including successfully creating and us deleting a real draft post. So the block is **not a blanket, always-on block on GitHub Actions' IP ranges either** — this appears to be an **intermittent or volume/pattern-dependent** protection layer that isn't reflected in the account-level "CDN Security Level" toggle. See the "Light diagnostic vs. full production run" comparison below — this is the key data point we need your help interpreting from your side (edge/WAF logs), since we can't see what triggers it from ours.

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

All in the format `<hash>-phx-edge{N}` — spread across edge6, edge8, edge9. As the comparison below shows, these SAME edge nodes also served our successful diagnostic minutes later, so this isn't one misbehaving node either; whatever triggers the block is evidently per-request/per-session, not tied to a specific edge server.

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

## Light diagnostic vs. full production run: the key contrast

| | Light diagnostic | Full production run |
|---|---|---|
| When | 2026-07-11 14:45-14:46 UTC | 2026-07-11 13:49-14:08 UTC (and earlier, 10:14-10:37 UTC) |
| Requests | 3 total (1 GET unauth, 1 GET auth, 1 POST auth) in ~20 seconds | ~15-20+ requests (GET posts/pages x2 per article, GET homepage, POST media x5 + POST post creation for at least one article) spread across ~20 minutes |
| Result | **100% success** (200, 200, 201 — draft created and cleaned up) | **Near-100% failure** — every GET on posts/pages hit 403; every image upload and the one post-creation attempt that got that far also hit 403 |
| Edge nodes hit | phx-edge5, phx-edge6, phx-edge8, phx-edge9 | phx-edge6, phx-edge8, phx-edge9 |

The overlapping edge-node set on both sides rules out "one bad edge node" as the explanation — the SAME edge pool serves both a clean success and a near-total failure depending on which run it's part of. This is why we suspect a **request-volume or request-pattern-based** trigger (e.g., an automatic rate-limit/bot-abuse heuristic tied to request frequency or count from the same source over a rolling window) rather than a static rule — since hPanel's manual "Security Level" toggle is off and doesn't explain this pattern.

## REST API namespaces registered (for ruling out a WordPress security plugin)

The diagnostic's successful `GET /wp-json/` call returned this site's registered REST namespaces: `oembed/1.0`, `code-snippets/v1`, `litespeed/v1`, `litespeed/v3`, `redirection/v1`. No `wordfence/v1`, no `ithemes-security/v1`, no other security-plugin-registered namespace is present — combined with every blocked response also carrying `server: hcdn` / `platform: hostinger` / `panel: hpanel` (the same markers present on successful responses), this points to the block happening at **your hCDN edge**, not inside WordPress or a security plugin at the origin. We were unable to query `/wp-json/wp/v2/plugins` directly to get a full plugin list (it correctly requires elevated auth we didn't attempt), but the namespace list plus the consistent `hcdn`-branded interstitial on every failure is reasonably strong evidence this isn't a WordPress-side plugin decision.

## Known gaps in our own evidence (for transparency)

- **GitHub Actions runner source IP**: not currently captured by our pipeline. GitHub-hosted runners use dynamic/ephemeral IPs drawn from Microsoft Azure's published ranges (`https://api.github.com/meta`, `actions` key) — we do not pin or log the specific IP per run today. If Hostinger's WAF logs can be searched by timestamp + `x-hcdn-request-id` instead of source IP, that should be sufficient to locate the exact block decision; otherwise we can add an IP-logging step to a future run if it would help your investigation.
- **Request-id on the write path** (image upload / post creation, `agent_10`/`agent_11`): these use a different, older HTTP client that does not yet capture response headers on error (unlike the read path, fixed 2026-07-11). We can add the same header capture there if a request-id is needed for the specific write-path 403s (timestamps above are solid; exact request-ids for the 5 image uploads + 1 post-creation call in this run are not available).
- **User-Agent strings sent by our CI** (in case it helps you search WAF logs by UA instead of IP):
  - Read path (posts/pages fetch): `NEXUS-14-agent04/1.0`
  - Write path (media upload, post creation): `NEXUS-14/3.0`

## What we're asking

1. Please check your hCDN edge logs for the specific request-IDs above (or the time ranges 2026-07-11 10:14-10:37 UTC and 13:49-14:09 UTC) and tell us what triggered the block on those requests specifically — since the account's "CDN Security Level" is already off and a lighter same-day diagnostic from the same class of source succeeded cleanly, we suspect an automatic rate-limiting or abuse-pattern heuristic that operates independently of that toggle, but we'd like your confirmation rather than guessing further from our side.
2. If it is a rate/volume-based heuristic: what's the threshold (requests per minute/hour, or a burst pattern), and is there a way to allowlist or raise the threshold for our authenticated Application-Password traffic (identifiable by the `Authorization: Basic` header on the write-path requests) or for a specific User-Agent we control (`NEXUS-14-agent04/1.0` on reads, `NEXUS-14/3.0` on writes)?
3. If it's something else entirely (not rate-based) — happy to hear what your logs show; we don't have visibility into your edge from our side beyond what's captured above.
4. This has been recurring on 2026-07-11 across two full production runs, roughly 3 hours apart, both almost entirely blocked, while a lightweight same-day diagnostic succeeded — so it's tied to something about the full run's request pattern/volume, not a one-off fluke.

Happy to provide the full raw CI logs for any of the runs referenced above if useful.
