"""
NEXUS-14 V4 - services/embeddings_service.py  (M3/M4 support)

Provider-agnostic text-embedding service used by:
  * Agent 17 (semantic cannibalization)
  * Agent 19 (originality engine)

Design goals
  * Deterministic, fully offline-testable similarity math (cosine).
  * A clean, stable interface (embed_text / embed_batch / cosine_similarity).
  * A pluggable provider backend selected by EMBEDDINGS_PROVIDER:
        - "openai"  -> text-embedding-3-small / -large  (requires OPENAI_API_KEY)
        - "voyage"  -> voyage-3                          (requires VOYAGE_API_KEY)
        - "hashing" -> deterministic local hashing vectorizer (NO network, default)

The "hashing" backend is a real, deterministic feature-hashing vectorizer. It is
NOT a semantic model, but it lets the entire pipeline + tests run with zero
external dependencies or cost. Swapping to a true semantic provider is a one-line
env change; the integration point is documented in _embed_remote().

NOTE (integration point): _embed_remote() contains the exact request shape for
each supported provider but performs the network call only when the relevant API
key is configured. If the key is absent we fall back to the hashing backend so
the system remains runnable. This is an explicit, documented degradation -- not a
silent stub.
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
import re
from typing import List, Sequence

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]+")
DEFAULT_DIM = 256


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall((text or "").lower())


class EmbeddingsService:
    def __init__(self, provider: str = None, dim: int = DEFAULT_DIM):
        self.provider = (provider or os.environ.get("EMBEDDINGS_PROVIDER", "hashing")).lower()
        self.dim = dim
        self._openai_key = os.environ.get("OPENAI_API_KEY")
        self._voyage_key = os.environ.get("VOYAGE_API_KEY")

    # ---- public API -------------------------------------------------------
    def embed_text(self, text: str) -> List[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: Sequence[str]) -> List[List[float]]:
        if self.provider in ("openai", "voyage"):
            remote = self._embed_remote(list(texts))
            if remote is not None:
                return remote
            logger.warning(
                "Embeddings provider '%s' unavailable (missing key/network); "
                "falling back to deterministic hashing vectorizer.",
                self.provider,
            )
        return [self._hash_embed(t) for t in texts]

    @staticmethod
    def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
        if not a or not b:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    # ---- backends ---------------------------------------------------------
    def _hash_embed(self, text: str) -> List[float]:
        """Deterministic feature-hashing vectorizer (L2-normalized)."""
        vec = [0.0] * self.dim
        for tok in _tokenize(text):
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 8) & 1 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def _embed_remote(self, texts: List[str]):
        """INTEGRATION POINT: real semantic provider call.

        Returns a list of vectors, or None if the provider cannot be used (so the
        caller falls back to hashing). Network call only happens when configured.
        """
        try:
            if self.provider == "openai" and self._openai_key:
                import requests
                resp = requests.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {self._openai_key}"},
                    json={"model": os.environ.get("OPENAI_EMBED_MODEL",
                                                   "text-embedding-3-small"),
                          "input": texts},
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()["data"]
                return [d["embedding"] for d in data]
            if self.provider == "voyage" and self._voyage_key:
                import requests
                resp = requests.post(
                    "https://api.voyageai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {self._voyage_key}"},
                    json={"model": os.environ.get("VOYAGE_EMBED_MODEL", "voyage-3"),
                          "input": texts},
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()["data"]
                return [d["embedding"] for d in data]
        except Exception as e:  # pragma: no cover - network dependent
            logger.warning("Remote embedding failed: %s", e)
        return None


# Module-level convenience singleton (lazy).
_default_service: EmbeddingsService = None


def get_embeddings_service() -> EmbeddingsService:
    global _default_service
    if _default_service is None:
        _default_service = EmbeddingsService()
    return _default_service
