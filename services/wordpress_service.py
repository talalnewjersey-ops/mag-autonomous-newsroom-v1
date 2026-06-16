"""
NEXUS-14: WordPress Service v2.1 - FIX: per-request sessions (no unclosed session errors)
"""
import json
import logging
import base64
from pathlib import Path
from typing import Dict, List, Optional, Any
import aiohttp

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

                    async with aiohttp.ClientSession() as session:
                                    async with session.post(
                                                        f"{self.api_url}/posts",
                                                        json=payload,
                                                        headers=self._get_headers(),
                                                        timeout=aiohttp.ClientTimeout(total=60),
                                    ) as response:
                                                        if response.status in [200, 201]:
                                                                                result = await response.json()
                                                                                logger.info(f"Created WordPress post ID: {result.get('id')}")
                                                                                return result
else:
                    error_text = await response.text()
                        raise Exception(f"WordPress post creation failed ({response.status}): {error_text[:300]}")

    async def update_post(self, post_id: int, update_data: Dict) -> Dict:
                async with aiohttp.ClientSession() as session:
                                async with session.post(
                                                    f"{self.api_url}/posts/{post_id}",
                                                    json=update_data,
                                                    headers=self._get_headers(),
                                                    timeout=aiohttp.ClientTimeout(total=60),
                                ) as response:
                                                    if response.status == 200:
                                                                            return await response.json()
else:
                    error = await response.text()
                    raise Exception(f"WordPress update failed ({response.status}): {error[:200]}")

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

        async with aiohttp.ClientSession() as session:
                        async with session.post(
                                            f"{self.api_url}/media",
                                            data=image_data,
                                            headers=headers,
                                            timeout=aiohttp.ClientTimeout(total=120),
                        ) as response:
                                            if response.status in [200, 201]:
                                                                    result = await response.json()
                    logger.info(f"Uploaded image: {result.get('id')} - {result.get('source_url', '')}")
                    return result
else:
                    error = await response.text()
                    raise Exception(f"Image upload failed ({response.status}): {error[:200]}")

    async def update_media(self, media_id: int, data: Dict) -> Dict:
                async with aiohttp.ClientSession() as session:
                                async with session.post(
                                                    f"{self.api_url}/media/{media_id}",
                                                    json=data,
                                                    headers=self._get_headers(),
                                                    timeout=aiohttp.ClientTimeout(total=30),
                                ) as response:
                                                    if response.status == 200:
                                                                            return await response.json()
                                                                        return {}

    async def set_featured_image(self, post_id: int, media_id: int):
                await self.update_post(post_id, {"featured_media": media_id})

    async def _get_or_create_author(self, name: str, bio: str) -> Optional[int]:
                async with aiohttp.ClientSession() as session:
                                async with session.get(
                                                    f"{self.api_url}/users",
                                                    params={"search": name},
                                                    headers=self._get_headers(),
                                                    timeout=aiohttp.ClientTimeout(total=30),
                                ) as response:
                                                    if response.status == 200:
                                                                            users = await response.json()
                                                                            if users:
                                                                                                        return users[0]["id"]
                                                                                        return self.config.get("wordpress_author_id", 1)

    async def get_categories(self) -> List[Dict]:
                async with aiohttp.ClientSession() as session:
                                async with session.get(
                                                                        f"{self.api_url}/categories",
                                                    params={"per_page": 100},
                                                    headers=self._get_headers(),
                                                    timeout=aiohttp.ClientTimeout(total=30),
                                ) as response:
                                                    if response.status == 200:
                                                                            return await response.json()
                return []

    async def get_post(self, post_id: int) -> Optional[Dict]:
                async with aiohttp.ClientSession() as session:
                                async with session.get(
                                                    f"{self.api_url}/posts/{post_id}",
                                                    headers=self._get_headers(),
                                                    timeout=aiohttp.ClientTimeout(total=30),
                                ) as response:
                                                    if response.status == 200:
                                                                            return await response.json()
                return None

    async def publish_post(self, post_id: int) -> Dict:
                return await self.update_post(post_id, {"status": "publish"})

    async def close(self):
                pass  # No persistent session to close in v2.1
