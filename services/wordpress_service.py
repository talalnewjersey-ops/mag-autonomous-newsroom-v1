"""
NEXUS-14: WordPress Service v2.1 - FIX: per-request sessions (no unclosed session errors)
"""
import asyncio
import json
import logging
import base64
from pathlib import Path
from typing import Dict, List, Optional, Any
import aiohttp

from agents._wp_challenge import (
    RETRY_DELAYS_SECONDS, INTER_CALL_SPACING_SECONDS, call_with_challenge_retry_async,
)

logger = logging.getLogger(__name__)


class WordPressService:
    def __init__(self, config: Dict):
        self.config = config
        self.base_url = config.get("wordpress_url", "").rstrip("/")
        self.api_url = f"{self.base_url}/wp-json/wp/v2"
        self.username = config.get("wordpress_username", "")
        self.app_password = config.get("wordpress_app_password", "")
        credentials = f"{self.username}:{self.app_password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        self.auth_header = f"Basic {encoded}"
        logger.info(f"WordPressService initialized for: {self.base_url}")

    def _get_headers(self, content_type: str = "application/json") -> Dict:
        return {
            "Authorization": self.auth_header,
            "Content-Type": content_type,
            "User-Agent": "NEXUS-14/2.1",
        }

    async def _request_with_challenge_retry(self, method: str, url: str, **kwargs):
        """Makes ONE aiohttp request (a fresh ClientSession per attempt, matching
        this file's existing per-request-session pattern), retrying with
        backoff if the response is the Hostinger hCDN "please wait" challenge-
        403 interstitial (2026-07-11, PR express -- see
        agents/_wp_challenge.py). A hard 403 (e.g. a clean `rest_forbidden`
        JSON error) or any other status returns immediately, un-retried.

        Returns (status, body_text) -- callers read the status/body directly
        instead of a live response object, since that can't be kept open
        across a retry's fresh session anyway; json.loads(body) on success
        replaces the old `await response.json()`."""
        async def _attempt():
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, **kwargs) as response:
                    return response.status, await response.text(), None

        await asyncio.sleep(INTER_CALL_SPACING_SECONDS)  # light preventive pacing before every WP call
        status, body, _ = await call_with_challenge_retry_async(
            _attempt, asyncio.sleep,
            log_fn=lambda n, d: logger.warning(
                f"WP challenge 403 detected on {method} {url}, retry {n}/{len(RETRY_DELAYS_SECONDS)} in {d}s"),
        )
        return status, body

    async def create_post(self, post_data: Dict) -> Dict:
        payload = {
            "title": post_data.get("title", ""),
            "content": post_data.get("content", ""),
            "status": post_data.get("status", "draft"),
            "slug": post_data.get("slug", ""),
            "author": post_data.get("author", 1),
        }
        if post_data.get("featured_media"):
            payload["featured_media"] = post_data["featured_media"]
        if post_data.get("categories"):
            payload["categories"] = post_data["categories"]
        if post_data.get("tags"):
            payload["tags"] = post_data["tags"]

        status, body = await self._request_with_challenge_retry(
            "POST", f"{self.api_url}/posts", json=payload, headers=self._get_headers(),
            timeout=aiohttp.ClientTimeout(total=60),
        )
        if status in (200, 201):
            result = json.loads(body)
            logger.info(f"Created WordPress post ID: {result.get('id')}")
            return result
        else:
            raise Exception(f"WordPress post creation failed ({status}): {body[:300]}")

    async def update_post(self, post_id: int, update_data: Dict) -> Dict:
        status, body = await self._request_with_challenge_retry(
            "POST", f"{self.api_url}/posts/{post_id}", json=update_data, headers=self._get_headers(),
            timeout=aiohttp.ClientTimeout(total=60),
        )
        if status == 200:
            return json.loads(body)
        else:
            raise Exception(f"WordPress update failed ({status}): {body[:200]}")

    async def upload_image(self, file_path: str, title: str = "",
                           alt_text: str = "", description: str = "") -> Dict:
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()
        content_types = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif",
        }
        content_type = content_types.get(suffix, "image/jpeg")
        headers = {
            "Authorization": self.auth_header,
            "Content-Type": content_type,
            "Content-Disposition": f'attachment; filename="{file_path.name}"',
            "User-Agent": "NEXUS-14/2.1",
        }
        if title:
            headers["X-WP-Title"] = title
        if alt_text:
            headers["X-WP-Alt-Text"] = alt_text

        with open(file_path, "rb") as f:
            image_data = f.read()

        status, body = await self._request_with_challenge_retry(
            "POST", f"{self.api_url}/media", data=image_data, headers=headers,
            timeout=aiohttp.ClientTimeout(total=120),
        )
        if status in (200, 201):
            result = json.loads(body)
            logger.info(f"Uploaded image: {result.get('id')} - {result.get('source_url', '')}")
            return result
        else:
            raise Exception(f"Image upload failed ({status}): {body[:200]}")

    async def update_media(self, media_id: int, data: Dict) -> Dict:
        status, body = await self._request_with_challenge_retry(
            "POST", f"{self.api_url}/media/{media_id}", json=data, headers=self._get_headers(),
            timeout=aiohttp.ClientTimeout(total=30),
        )
        if status == 200:
            return json.loads(body)
        return {}

    async def set_featured_image(self, post_id: int, media_id: int):
        await self.update_post(post_id, {"featured_media": media_id})

    async def _get_or_create_author(self, name: str, bio: str) -> Optional[int]:
        status, body = await self._request_with_challenge_retry(
            "GET", f"{self.api_url}/users", params={"search": name}, headers=self._get_headers(),
            timeout=aiohttp.ClientTimeout(total=30),
        )
        if status == 200:
            users = json.loads(body)
            if users:
                return users[0]["id"]
        return self.config.get("wordpress_author_id", 1)

    async def set_post_author(self, post_id: int, author_name: str = "", author_bio: str = "") -> Optional[int]:
        author_id = await self._get_or_create_author(author_name, author_bio)
        if not author_id:
            return None
        try:
            await self.update_post(post_id, {"author": author_id})
        except Exception as e:
            logger.warning(f"set_post_author: update author failed: {e}")
        if author_bio:
            try:
                status, _body = await self._request_with_challenge_retry(
                    "POST", f"{self.api_url}/users/{author_id}", json={"description": author_bio},
                    headers=self._get_headers(), timeout=aiohttp.ClientTimeout(total=30),
                )
                if status not in (200, 201):
                    logger.warning(f"set_post_author: bio update returned {status}")
            except Exception as e:
                logger.warning(f"set_post_author: bio update failed: {e}")
        logger.info(f"set_post_author: post={post_id} author={author_id}")
        return author_id

    async def set_post_meta(self, post_id: int, meta: Dict) -> bool:
        clean = {k: v for k, v in (meta or {}).items() if v not in (None, "")}
        if not clean:
            return False
        try:
            status, body = await self._request_with_challenge_retry(
                "POST", f"{self.api_url}/posts/{post_id}", json={"meta": clean}, headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=60),
            )
            if status in (200, 201):
                logger.info(f"set_post_meta: post={post_id} keys={list(clean.keys())}")
                return True
            logger.warning(f"set_post_meta: returned {status}: {body[:200]}")
            return False
        except Exception as e:
            logger.warning(f"set_post_meta: failed: {e}")
            return False

    async def get_categories(self) -> List[Dict]:
        status, body = await self._request_with_challenge_retry(
            "GET", f"{self.api_url}/categories", params={"per_page": 100}, headers=self._get_headers(),
            timeout=aiohttp.ClientTimeout(total=30),
        )
        if status == 200:
            return json.loads(body)
        return []

    async def get_post(self, post_id: int) -> Optional[Dict]:
        status, body = await self._request_with_challenge_retry(
            "GET", f"{self.api_url}/posts/{post_id}", headers=self._get_headers(),
            timeout=aiohttp.ClientTimeout(total=30),
        )
        if status == 200:
            return json.loads(body)
        return None

    async def find_posts(self, search: str, per_page: int = 20) -> List[Dict]:
        """Search existing posts (published + drafts) by text -- used for the
        Sprint 9 pre-publish duplicate check. Returns [] on any error."""
        import urllib.parse
        q = urllib.parse.urlencode({"search": search[:120], "status": "publish,draft",
                                    "per_page": per_page, "context": "edit"})
        try:
            status, body = await self._request_with_challenge_retry(
                "GET", f"{self.api_url}/posts?{q}", headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=30),
            )
            if status == 200:
                return json.loads(body)
            return []
        except Exception as e:
            logger.warning(f"find_posts failed for {search!r}: {e}")
            return []

    async def publish_post(self, post_id: int) -> Dict:
        return await self.update_post(post_id, {"status": "publish"})

    async def close(self):
        pass  # No persistent session to close in v2.1
