"""
NEXUS-14: Search Service
Provides SEO keyword research and trending search data.
Uses SerpAPI and SemRush for data when available, with graceful fallback.
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, Any

import aiohttp

logger = logging.getLogger(__name__)


class SearchService:
    """
    Search and SEO data service for NEXUS-14.
    
    Integrates with:
    - SerpAPI for SERP data and trending searches
    - SemRush API for keyword metrics
    - Fallback to simulated data when APIs unavailable
    """

    def __init__(self, config: Dict):
        self.config = config
        self.serpapi_key = os.environ.get("SERPAPI_KEY", "")
        self.semrush_key = os.environ.get("SEMRUSH_API_KEY", "")
        self.serpapi_base = "https://serpapi.com/search"
        self.semrush_base = "https://api.semrush.com"

    async def get_trending_searches(self, query: str) -> List[str]:
        """Get trending searches related to a query."""
        try:
            if self.serpapi_key:
                return await self._serpapi_related_searches(query)
        except Exception as e:
            logger.warning(f"SerpAPI trending search failed for '{query}': {e}")
        
        # Fallback: return query-based expansions
        return self._generate_related_queries(query)

    async def get_keyword_data(self, keyword: str, country: str = "US") -> List[Dict]:
        """Get keyword metrics for a given keyword."""
        try:
            if self.semrush_key:
                return await self._semrush_keyword_data(keyword, country)
        except Exception as e:
            logger.warning(f"SemRush keyword data failed for '{keyword}': {e}")

        try:
            if self.serpapi_key:
                return await self._serpapi_keyword_data(keyword, country)
        except Exception as e:
            logger.warning(f"SerpAPI keyword data failed for '{keyword}': {e}")

        # Fallback: return simulated data for pipeline testing
        return self._generate_fallback_keyword_data(keyword, country)

    async def _serpapi_related_searches(self, query: str) -> List[str]:
        """Fetch related searches from SerpAPI."""
        params = {
            "q": query,
            "api_key": self.serpapi_key,
            "engine": "google",
            "num": 10,
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(
                self.serpapi_base,
                params=params,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                data = await resp.json()
                related = data.get("related_searches", [])
                return [r.get("query", "") for r in related if r.get("query")]

    async def _serpapi_keyword_data(self, keyword: str, country: str) -> List[Dict]:
        """Fetch keyword data from SerpAPI."""
        gl = "us" if country == "US" else "ca"
        params = {
            "q": keyword,
            "api_key": self.serpapi_key,
            "engine": "google",
            "gl": gl,
            "num": 10,
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(
                self.serpapi_base,
                params=params,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                data = await resp.json()
                results = data.get("organic_results", [])
                if results:
                    return [{
                        "keyword": keyword,
                        "search_volume": 1000,  # SerpAPI doesn't provide volume directly
                        "keyword_difficulty": 50,
                        "cpc": 2.0,
                        "intent": "informational",
                        "serp_features": [],
                        "country": country,
                    }]
        return []

    async def _semrush_keyword_data(self, keyword: str, country: str) -> List[Dict]:
        """Fetch keyword metrics from SemRush API."""
        database = "us" if country == "US" else "ca"
        params = {
            "type": "phrase_this",
            "key": self.semrush_key,
            "phrase": keyword,
            "export_columns": "Ph,Nq,Cp,Co,Nr,Td",
            "database": database,
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.semrush_base}/",
                params=params,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                text = await resp.text()
                rows = text.strip().split("\n")
                results = []
                if len(rows) > 1:
                    for row in rows[1:]:
                        cols = row.split(";")
                        if len(cols) >= 4:
                            try:
                                results.append({
                                    "keyword": cols[0].strip(),
                                    "search_volume": int(cols[1]) if cols[1].strip().isdigit() else 0,
                                    "cpc": float(cols[2]) if cols[2].strip() else 0.0,
                                    "keyword_difficulty": int(float(cols[3])) if cols[3].strip() else 50,
                                    "intent": "informational",
                                    "serp_features": [],
                                    "country": country,
                                })
                            except (ValueError, IndexError):
                                pass
                return results

    def _generate_related_queries(self, query: str) -> List[str]:
        """Generate related queries as fallback."""
        base_terms = query.split()[:3]
        variations = [
            f"{query} guide",
            f"{query} 2026",
            f"best {query}",
            f"{query} tips",
            f"how to {query}",
        ]
        return [v for v in variations if v != query][:5]

    def _generate_fallback_keyword_data(self, keyword: str, country: str) -> List[Dict]:
        """Generate fallback keyword data for pipeline testing."""
        import hashlib
        # Deterministic but varied data based on keyword
        hash_val = int(hashlib.md5(keyword.encode()).hexdigest()[:8], 16)
        
        return [{
            "keyword": keyword,
            "search_volume": 500 + (hash_val % 5000),
            "keyword_difficulty": 20 + (hash_val % 50),
            "cpc": round(0.5 + (hash_val % 100) / 20, 2),
            "intent": "informational",
            "serp_features": ["featured_snippet"] if hash_val % 3 == 0 else [],
            "country": country,
            "source": "fallback",
        }]
