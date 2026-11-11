from __future__ import annotations

import hashlib
import json
import logging

from redis import Redis

logger = logging.getLogger(__name__)


class ResponseCache:
    def __init__(self, url: str, enabled: bool = False, ttl_seconds: int = 300):
        self.enabled = enabled
        self.ttl_seconds = ttl_seconds
        self.client = Redis.from_url(url, decode_responses=True) if enabled else None

    @staticmethod
    def key(query: str, top_k: int, prompt_version: str, provider: str = "mock") -> str:
        raw = f"{provider}:{prompt_version}:{top_k}:{query.strip()}".encode()
        return "rag:v2:" + hashlib.sha256(raw).hexdigest()

    def get(self, query: str, top_k: int, prompt_version: str, provider: str = "mock"):
        if not self.enabled or self.client is None:
            return None
        try:
            value = self.client.get(self.key(query, top_k, prompt_version, provider))
            return json.loads(value) if value else None
        except Exception:
            logger.warning("Redis cache read failed; continuing without cache.", exc_info=True)
            return None

    def set(self, query: str, top_k: int, prompt_version: str, value: dict,
            provider: str = "mock") -> None:
        if not self.enabled or self.client is None:
            return
        try:
            self.client.setex(
                self.key(query, top_k, prompt_version, provider),
                self.ttl_seconds,
                json.dumps(value),
            )
        except Exception:
            logger.warning("Redis cache write failed; continuing without cache.", exc_info=True)
