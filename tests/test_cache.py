"""Test caching functionality."""
import pytest
import time
from core.cache import SimpleCache, CacheEntry


def test_cache_entry_creation():
    """Test cache entry creation with expiration."""
    entry = CacheEntry("test_value", ttl=10.0)
    assert entry.value == "test_value"
    assert not entry.is_expired()


def test_cache_entry_expiration():
    """Test cache entry expiration after TTL."""
    entry = CacheEntry("test_value", ttl=0.1)  # 100ms TTL
    assert not entry.is_expired()

    time.sleep(0.15)  # Wait for expiration
    assert entry.is_expired()


def test_cache_set_and_get():
    """Test basic cache set and get operations."""
    cache = SimpleCache()

    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"


def test_cache_get_nonexistent_key():
    """Test getting a key that doesn't exist."""
    cache = SimpleCache()
    assert cache.get("nonexistent") is None


def test_cache_get_expired_key():
    """Test that expired keys return None."""
    cache = SimpleCache(default_ttl=0.1)  # 100ms default TTL

    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"

    time.sleep(0.15)  # Wait for expiration
    assert cache.get("key1") is None  # Should return None and auto-clean


def test_cache_custom_ttl():
    """Test setting custom TTL for specific keys."""
    cache = SimpleCache(default_ttl=10.0)

    cache.set("short_lived", "value1", ttl=0.1)  # Custom 100ms TTL
    cache.set("long_lived", "value2")  # Uses default 10s TTL

    time.sleep(0.15)

    assert cache.get("short_lived") is None  # Expired
    assert cache.get("long_lived") == "value2"  # Still valid


def test_cache_overwrite():
    """Test overwriting an existing cache entry."""
    cache = SimpleCache()

    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"

    cache.set("key1", "value2")
    assert cache.get("key1") == "value2"


def test_cache_delete():
    """Test deleting a cache entry."""
    cache = SimpleCache()

    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"

    cache.delete("key1")
    assert cache.get("key1") is None


def test_cache_delete_nonexistent():
    """Test deleting a nonexistent key (should not raise error)."""
    cache = SimpleCache()
    cache.delete("nonexistent")  # Should not raise


def test_cache_clear():
    """Test clearing all cache entries."""
    cache = SimpleCache()

    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")

    assert cache.size() == 3

    cache.clear()

    assert cache.size() == 0
    assert cache.get("key1") is None
    assert cache.get("key2") is None
    assert cache.get("key3") is None


def test_cache_cleanup_expired():
    """Test cleanup of expired entries."""
    cache = SimpleCache(default_ttl=0.1)

    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3", ttl=10.0)  # Long TTL

    assert cache.size() == 3

    time.sleep(0.15)  # Wait for key1 and key2 to expire

    removed = cache.cleanup_expired()

    assert removed == 2  # key1 and key2 expired
    assert cache.size() == 1  # Only key3 remains
    assert cache.get("key3") == "value3"


def test_cache_size():
    """Test cache size tracking."""
    cache = SimpleCache()

    assert cache.size() == 0

    cache.set("key1", "value1")
    assert cache.size() == 1

    cache.set("key2", "value2")
    assert cache.size() == 2

    cache.delete("key1")
    assert cache.size() == 1

    cache.clear()
    assert cache.size() == 0


def test_cache_different_data_types():
    """Test caching different data types."""
    cache = SimpleCache()

    # String
    cache.set("str", "hello")
    assert cache.get("str") == "hello"

    # Integer
    cache.set("int", 42)
    assert cache.get("int") == 42

    # List
    cache.set("list", [1, 2, 3])
    assert cache.get("list") == [1, 2, 3]

    # Dict
    cache.set("dict", {"a": 1, "b": 2})
    assert cache.get("dict") == {"a": 1, "b": 2}

    # None
    cache.set("none", None)
    assert cache.get("none") is None  # Can't distinguish from missing key


def test_cache_large_values():
    """Test caching large values."""
    cache = SimpleCache()

    large_list = list(range(10000))
    cache.set("large", large_list)

    retrieved = cache.get("large")
    assert retrieved == large_list
    assert len(retrieved) == 10000


def test_node_type_cache_global():
    """Test that the global node_type_cache instance exists."""
    from core.cache import node_type_cache

    assert node_type_cache is not None
    assert isinstance(node_type_cache, SimpleCache)
    # Default TTL should be 1 hour (3600 seconds)
    assert node_type_cache.default_ttl == 3600.0
