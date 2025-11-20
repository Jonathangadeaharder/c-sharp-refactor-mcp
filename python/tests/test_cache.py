"""
Tests for cache manager.
"""

import asyncio
import pytest
from refactor_mcp.utils.cache import CacheManager


class TestCacheManager:
    """Test cache manager functionality."""

    @pytest.mark.asyncio
    async def test_cache_init(self):
        """Test cache manager initialization."""
        cache = CacheManager(max_size_mb=10)
        assert cache.max_size == 10 * 1024 * 1024

        stats = await cache.get_stats()
        assert stats["total_entries"] == 0
        assert stats["max_size_mb"] == 10.0

    @pytest.mark.asyncio
    async def test_cache_set_get(self):
        """Test basic cache set and get operations."""
        cache = CacheManager(max_size_mb=1)

        # Set a value
        await cache.set("test_key", {"data": "value"}, ttl=10)

        # Get the value
        result = await cache.get("test_key")
        assert result == {"data": "value"}

    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss returns None."""
        cache = CacheManager(max_size_mb=1)

        result = await cache.get("nonexistent_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_expiration(self):
        """Test that cache entries expire after TTL."""
        cache = CacheManager(max_size_mb=1)

        # Set a value with 1 second TTL
        await cache.set("test_key", {"data": "value"}, ttl=1)

        # Should exist immediately
        result = await cache.get("test_key")
        assert result == {"data": "value"}

        # Wait for expiration
        await asyncio.sleep(1.5)

        # Should be expired
        result = await cache.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_update(self):
        """Test updating an existing cache entry."""
        cache = CacheManager(max_size_mb=1)

        # Set initial value
        await cache.set("test_key", {"data": "value1"}, ttl=10)

        # Update value
        await cache.set("test_key", {"data": "value2"}, ttl=10)

        # Should get updated value
        result = await cache.get("test_key")
        assert result == {"data": "value2"}

    @pytest.mark.asyncio
    async def test_cache_delete(self):
        """Test deleting cache entries."""
        cache = CacheManager(max_size_mb=1)

        # Set a value
        await cache.set("test_key", {"data": "value"}, ttl=10)

        # Delete it
        deleted = await cache.delete("test_key")
        assert deleted is True

        # Should not exist
        result = await cache.get("test_key")
        assert result is None

        # Deleting again should return False
        deleted = await cache.delete("test_key")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_cache_namespaces(self):
        """Test namespace support for organized clearing."""
        cache = CacheManager(max_size_mb=1)

        # Set values in different namespaces
        await cache.set("key1", {"data": "ns1_value"}, ttl=10, namespace="ns1")
        await cache.set("key2", {"data": "ns2_value"}, ttl=10, namespace="ns2")
        await cache.set("key3", {"data": "ns1_value2"}, ttl=10, namespace="ns1")

        # Clear ns1
        cleared = await cache.clear_namespace("ns1")
        assert cleared == 2

        # ns1 keys should be gone
        result1 = await cache.get("key1")
        assert result1 is None
        result3 = await cache.get("key3")
        assert result3 is None

        # ns2 key should still exist
        result2 = await cache.get("key2")
        assert result2 == {"data": "ns2_value"}

    @pytest.mark.asyncio
    async def test_cache_clear(self):
        """Test clearing entire cache."""
        cache = CacheManager(max_size_mb=1)

        # Set multiple values
        await cache.set("key1", {"data": "value1"}, ttl=10)
        await cache.set("key2", {"data": "value2"}, ttl=10)
        await cache.set("key3", {"data": "value3"}, ttl=10)

        # Verify they exist
        stats = await cache.get_stats()
        assert stats["total_entries"] == 3

        # Clear all
        await cache.clear()

        # Should be empty
        stats = await cache.get_stats()
        assert stats["total_entries"] == 0

    @pytest.mark.asyncio
    async def test_cache_stats(self):
        """Test cache statistics."""
        cache = CacheManager(max_size_mb=5)

        # Add entries in different namespaces
        await cache.set("key1", {"data": "value"}, ttl=10, namespace="diagnostics")
        await cache.set("key2", {"data": "value"}, ttl=10, namespace="diagnostics")
        await cache.set("key3", {"data": "value"}, ttl=10, namespace="symbols")

        stats = await cache.get_stats()

        assert stats["total_entries"] == 3
        assert stats["max_size_mb"] == 5.0
        assert stats["namespaces"]["diagnostics"] == 2
        assert stats["namespaces"]["symbols"] == 1

    @pytest.mark.asyncio
    async def test_cache_cleanup_expired(self):
        """Test manual cleanup of expired entries."""
        cache = CacheManager(max_size_mb=1)

        # Set entries with short TTL
        await cache.set("key1", {"data": "value1"}, ttl=1)
        await cache.set("key2", {"data": "value2"}, ttl=1)
        await cache.set("key3", {"data": "value3"}, ttl=10)  # Not expired

        # Wait for expiration
        await asyncio.sleep(1.5)

        # Clean up expired
        cleaned = await cache.cleanup_expired()
        assert cleaned == 2

        # Verify counts
        stats = await cache.get_stats()
        assert stats["total_entries"] == 1

    @pytest.mark.asyncio
    async def test_cache_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = CacheManager(max_size_mb=1)

        # Add many entries to trigger eviction
        for i in range(1500):
            await cache.set(f"key{i}", {"data": f"value{i}"}, ttl=60)

        # Should have evicted some entries
        stats = await cache.get_stats()
        assert stats["total_entries"] <= 1000  # Max entries threshold

    @pytest.mark.asyncio
    async def test_cache_concurrent_access(self):
        """Test concurrent access to cache."""
        cache = CacheManager(max_size_mb=1)

        async def set_value(key: str, value: str):
            await cache.set(key, {"data": value}, ttl=10)

        async def get_value(key: str):
            return await cache.get(key)

        # Concurrent sets
        await asyncio.gather(
            set_value("key1", "value1"),
            set_value("key2", "value2"),
            set_value("key3", "value3"),
        )

        # Concurrent gets
        results = await asyncio.gather(
            get_value("key1"),
            get_value("key2"),
            get_value("key3"),
        )

        assert results[0] == {"data": "value1"}
        assert results[1] == {"data": "value2"}
        assert results[2] == {"data": "value3"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
