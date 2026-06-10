"""
NEXUS-14: WordPress Service
Handles all WordPress REST API interactions for the newsroom.
"""

import asyncio
import json
import logging
import base64
from pathlib import Path
from typing import Dict, List, Optional, Any
import aiohttp


logger = logging.getLogger(__name__)


class WordPressService:
    """
    WordPress REST API service for NEXUS-14.
    
    Handles:
    - Post creation and updates
    - Media/image uploads
    - Author management
    - Category/tag assignment
    - SEO metadata (Yoast/RankMath)
    - Post status management
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.base_url = config.get("wordpress_url", "").rstrip("/")
        self.api_url = f"{self.base_url}/wp-json/wp/v2"
        self.username = config.get("wordpress_username", "")
        self.app_password = config.get("wordpress_app_password", "")
        
        # Auth header
        credentials = f"{self.username}:{self.app_password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        self.auth_header = f"Basic {encoded}"
        
        self._session = None
        logger.info(f"WordPressService initialized for: {self.base_url}")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": self.auth_header,
                    "Content-Type": "application/json",
                    "User-Agent": "NEXUS-14/1.0"
                }
            )
        return self._session
    
    async def create_post(self, post_data: Dict) -> Dict:
        """Create a new WordPress post as draft."""
        session = await self._get_session()
        
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
        
        async with session.post(f"{self.api_url}/posts", json=payload) as response:
            if response.status in [200, 201]:
                result = await response.json()
                logger.info(f"Created WordPress post ID: {result.get('id')}")
                return result
            else:
                error_text = await response.text()
                raise Exception(f"WordPress post creation failed ({response.status}): {error_text[:200]}")
    
    async def update_post(self, post_id: int, update_data: Dict) -> Dict:
        """Update an existing WordPress post."""
        session = await self._get_session()
        
        async with session.put(f"{self.api_url}/posts/{post_id}", json=update_data) as response:
            if response.status == 200:
                return await response.json()
            else:
                error = await response.text()
                raise Exception(f"WordPress update failed ({response.status}): {error[:200]}")
    
    async def upload_image(self, file_path: str, title: str = "",
                           alt_text: str = "", description: str = "") -> Dict:
        """Upload an image to WordPress media library."""
        session_headers = {
            "Authorization": self.auth_header,
            "User-Agent": "NEXUS-14/1.0"
        }
        
        file_path = Path(file_path)
        
        # Determine content type
        suffix = file_path.suffix.lower()
        content_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif"
        }
        content_type = content_types.get(suffix, "image/jpeg")
        
        async with aiohttp.ClientSession(headers=session_headers) as session:
            with open(file_path, "rb") as f:
                image_data = f.read()
            
            headers = {
                **session_headers,
                "Content-Type": content_type,
                "Content-Disposition": f'attachment; filename="{file_path.name}"'
            }
            
            if title:
                headers["X-WP-Title"] = title
            if alt_text:
                headers["X-WP-Alt-Text"] = alt_text
            
            async with session.post(
                f"{self.api_url}/media",
                data=image_data,
                headers=headers
            ) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    logger.info(f"Uploaded image: {result.get('id')} - {result.get('source_url', '')}")
                    
                    # Update alt text
                    if alt_text and result.get("id"):
                        await self.update_media(result["id"], {"alt_text": alt_text})
                    
                    return result
                else:
                    error = await response.text()
                    raise Exception(f"Image upload failed ({response.status}): {error[:200]}")
    
    async def update_media(self, media_id: int, data: Dict) -> Dict:
        """Update media item metadata."""
        session = await self._get_session()
        
        async with session.post(f"{self.api_url}/media/{media_id}", json=data) as response:
            if response.status == 200:
                return await response.json()
            return {}
    
    async def set_featured_image(self, post_id: int, media_id: int):
        """Set the featured image for a post."""
        await self.update_post(post_id, {"featured_media": media_id})
    
    async def set_post_author(self, post_id: int, author_name: str, author_bio: str):
        """Set author information for a post."""
        # Try to find or create the author
        author_id = await self._get_or_create_author(author_name, author_bio)
        if author_id:
            await self.update_post(post_id, {"author": author_id})
    
    async def _get_or_create_author(self, name: str, bio: str) -> Optional[int]:
        """Get existing author or create new one."""
        session = await self._get_session()
        
        # Search for existing user
        async with session.get(f"{self.api_url}/users", params={"search": name}) as response:
            if response.status == 200:
                users = await response.json()
                if users:
                    return users[0]["id"]
        
        # Return default author if can't create
        return self.config.get("wordpress_author_id", 1)
    
    async def set_post_meta(self, post_id: int, meta_data: Dict):
        """Set post meta (SEO fields, custom fields)."""
        session = await self._get_session()
        
        # Update post with meta
        payload = {"meta": meta_data}
        
        async with session.put(f"{self.api_url}/posts/{post_id}", json=payload) as response:
            if response.status != 200:
                logger.warning(f"Failed to set post meta: {response.status}")
    
    async def get_categories(self) -> List[Dict]:
        """Get all WordPress categories."""
        session = await self._get_session()
        
        async with session.get(f"{self.api_url}/categories", params={"per_page": 100}) as response:
            if response.status == 200:
                return await response.json()
        return []
    
    async def create_category(self, name: str, slug: str = None, parent: int = 0) -> Dict:
        """Create a new category."""
        session = await self._get_session()
        
        payload = {"name": name, "parent": parent}
        if wordpress_service.pyslug:
            payload["slug"] = slug
        
        async with session.post(f"{self.api_url}/categories", json=payload) as response:
            if response.status in [200, 201]:
                return await response.json()
            return {}
    
    async def get_post(self, post_id: int) -> Optional[Dict]:
        """Get a post by ID."""
        session = await self._get_session()
        
        async with session.get(f"{self.api_url}/posts/{post_id}") as response:
            if response.status == 200:
                return await response.json()
        return None
    
    async def publish_post(self, post_id: int) -> Dict:
        """Publish a draft post."""
        return await self.update_post(post_id, {"status": "publish"})
    
    async def close(self):
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()
