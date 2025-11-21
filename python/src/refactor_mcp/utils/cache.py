"""
Cache manager with TTL and LRU eviction.

Provides in-memory caching for expensive operations like diagnostics and symbol lookups.
"""

import asyncio
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with TTL."""

    value: Any
    expires_at: float
    namespace: str


class CacheManager:
    """
    In-memory cache with TTL and LRU eviction.

    Features:
    - Time-to-live (TTL) expiration
    - LRU eviction when max size reached
    - Namespace support for organized clearing
    - Thread-safe async operations
    """

    def __init__(self, max_size_mb: int = 256):
        """
        Initialize cache manager.

        Args:
            max_size_mb: Maximum cache size in MB (default 256MB)
        """
        self.max_size = max_size_mb * 1024 * 1024  # Convert to bytes
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
        self._current_size = 0

        logger.info(f"Cache manager initialized with max size: {max_size_mb}MB")

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        async with self._lock:
            entry = self._cache.get(key)
            if not entry:
                return None

            # Check if expired
            if time.time() > entry.expires_at:
                logger.debug(f"Cache expired: {key}")
                del self._cache[key]
                return None

            # Move to end (LRU)
            self._cache.move_to_end(key)
            logger.debug(f"Cache hit: {key}")
            return entry.value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 300,
        namespace: str = "default",
    ) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (default 300)
            namespace: Namespace for organized clearing
        """
        async with self._lock:
            expires_at = time.time() + ttl

            # Remove old entry if exists
            if key in self._cache:
                del self._cache[key]

            # Create new entry
            entry = CacheEntry(
                value=value,
                expires_at=expires_at,
                namespace=namespace,
            )

            self._cache[key] = entry
            self._cache.move_to_end(key)

            # Evict if over size (simple approximation)
            await self._evict_if_needed()

            logger.debug(f"Cache set: {key} (TTL: {ttl}s, namespace: {namespace})")

    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache delete: {key}")
                return True
            return False

    async def clear_namespace(self, namespace: str) -> int:
        """
        Clear all entries in a namespace.

        Args:
            namespace: Namespace to clear

        Returns:
            Number of entries cleared
        """
        async with self._lock:
            keys_to_delete = [
                key
                for key, entry in self._cache.items()
                if entry.namespace == namespace
            ]

            for key in keys_to_delete:
                del self._cache[key]

            logger.info(f"Cleared {len(keys_to_delete)} entries from namespace: {namespace}")
            return len(keys_to_delete)

    async def clear(self) -> None:
        """Clear entire cache."""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._current_size = 0
            logger.info(f"Cache cleared: {count} entries")

    async def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        async with self._lock:
            # Count by namespace
            namespaces: dict[str, int] = {}
            for entry in self._cache.values():
                namespaces[entry.namespace] = namespaces.get(entry.namespace, 0) + 1

            return {
                "total_entries": len(self._cache),
                "max_size_mb": self.max_size / (1024 * 1024),
                "namespaces": namespaces,
            }

    async def _evict_if_needed(self) -> None:
        """Evict oldest entries if cache is too large."""
        # Simple approximation: evict if too many entries
        max_entries = 1000  # Reasonable limit

        if len(self._cache) > max_entries:
            # Remove oldest 10%
            to_remove = max_entries // 10
            for _ in range(to_remove):
                if self._cache:
                    key, _ = self._cache.popitem(last=False)
                    logger.debug(f"Cache evicted (LRU): {key}")

    async def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        async with self._lock:
            now = time.time()
            expired_keys = [
                key for key, entry in self._cache.items() if now > entry.expires_at
            ]

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

            return len(expired_keys)
