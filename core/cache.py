"""Simple in-memory cache with TTL support for node type information."""
from __future__ import annotations

import time
from typing import Any, Dict, Optional, TypeVar

T = TypeVar("T")


class CacheEntry:
    """A cache entry with expiration time."""

    def __init__(self, value: Any, ttl: float):
        self.value = value
        self.expiry = time.time() + ttl

    def is_expired(self) -> bool:
        """Check if this cache entry has expired."""
        return time.time() > self.expiry


class SimpleCache:
    """Simple in-memory cache with TTL support."""

    def __init__(self, default_ttl: float = 3600.0):
        """
        Initialize the cache.

        Args:
            default_ttl: Default time-to-live for cache entries in seconds (default: 1 hour)
        """
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.

        Args:
            key: The cache key

        Returns:
            The cached value if it exists and hasn't expired, None otherwise
        """
        entry = self._cache.get(key)
        if entry is None:
            return None

        if entry.is_expired():
            # Clean up expired entry
            del self._cache[key]
            return None

        return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """
        Set a value in the cache.

        Args:
            key: The cache key
            value: The value to cache
            ttl: Time-to-live in seconds (uses default_ttl if not specified)
        """
        if ttl is None:
            ttl = self.default_ttl

        self._cache[key] = CacheEntry(value, ttl)

    def delete(self, key: str) -> None:
        """
        Delete a value from the cache.

        Args:
            key: The cache key to delete
        """
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all entries from the cache."""
        self._cache.clear()

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from the cache.

        Returns:
            Number of entries removed
        """
        expired_keys = [
            key for key, entry in self._cache.items() if entry.is_expired()
        ]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)

    def size(self) -> int:
        """Get the number of entries in the cache."""
        return len(self._cache)


# Global cache instance for node types
# Cache for 1 hour (3600 seconds) - node types rarely change
node_type_cache = SimpleCache(default_ttl=3600.0)
