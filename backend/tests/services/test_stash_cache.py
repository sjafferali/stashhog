"""Tests for Stash cache implementation."""

import threading
import time
from unittest.mock import patch

import pytest

from app.services.stash.cache import StashCache, StashEntityCache


class TestStashCache:
    """Test basic cache functionality."""

    @pytest.fixture
    def cache(self):
        """Create a cache instance for testing."""
        return StashCache(max_size=5, default_ttl=1)

    def test_cache_initialization(self):
        """Test cache initialization with custom parameters."""
        cache = StashCache(max_size=100, default_ttl=600)
        assert cache.max_size == 100
        assert cache.default_ttl == 600
        assert cache.size() == 0

    def test_set_and_get(self, cache):
        """Test basic set and get operations."""
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        assert cache.size() == 1

    def test_get_nonexistent_key(self, cache):
        """Test getting a key that doesn't exist."""
        assert cache.get("nonexistent") is None

    def test_ttl_expiration(self, cache):
        """Test that items expire after TTL."""
        cache.set("key1", "value1", ttl=0.1)  # 100ms TTL
        assert cache.get("key1") == "value1"

        time.sleep(0.2)  # Wait for expiration
        assert cache.get("key1") is None
        assert cache.size() == 0  # Should be removed from cache

    def test_custom_ttl(self, cache):
        """Test setting custom TTL for individual items."""
        cache.set("key1", "value1", ttl=2)  # 2 second TTL
        cache.set("key2", "value2", ttl=0.1)  # 100ms TTL

        time.sleep(0.2)  # Wait for key2 to expire
        assert cache.get("key1") == "value1"  # Should still be valid
        assert cache.get("key2") is None  # Should be expired

    def test_lru_eviction(self, cache):
        """Test LRU eviction when cache is full."""
        # Fill cache to capacity
        for i in range(5):
            cache.set(f"key{i}", f"value{i}")

        assert cache.size() == 5

        # Access key0 to make it recently used
        cache.get("key0")

        # Add new item, should evict key1 (least recently used)
        cache.set("key5", "value5")

        assert cache.size() == 5
        assert cache.get("key0") == "value0"  # Still in cache
        assert cache.get("key1") is None  # Evicted
        assert cache.get("key5") == "value5"  # New item

    def test_delete(self, cache):
        """Test deleting items from cache."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.delete("key1")
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.size() == 1

    def test_delete_nonexistent_key(self, cache):
        """Test deleting a key that doesn't exist."""
        cache.delete("nonexistent")  # Should not raise an error
        assert cache.size() == 0

    def test_clear(self, cache):
        """Test clearing all cache entries."""
        for i in range(3):
            cache.set(f"key{i}", f"value{i}")

        assert cache.size() == 3
        cache.clear()
        assert cache.size() == 0

        # All items should be gone
        for i in range(3):
            assert cache.get(f"key{i}") is None

    def test_invalidate_pattern(self, cache):
        """Test invalidating keys by pattern."""
        cache.set("user:1", "data1")
        cache.set("user:2", "data2")
        cache.set("post:1", "data3")
        cache.set("post:2", "data4")

        cache.invalidate_pattern("user:")

        assert cache.get("user:1") is None
        assert cache.get("user:2") is None
        assert cache.get("post:1") == "data3"
        assert cache.get("post:2") == "data4"
        assert cache.size() == 2

    def test_thread_safety(self, cache):
        """Test cache operations are thread-safe."""
        errors = []

        def create_worker(operation, errors_list):
            """Create a worker function for thread testing."""

            def worker():
                try:
                    for i in range(100):
                        if operation == "write":
                            cache.set(f"key{i % 10}", f"value{i}")
                        else:  # read
                            cache.get(f"key{i % 10}")
                except Exception as e:
                    errors_list.append(e)

            return worker

        # Create and start threads
        threads = []
        for _ in range(5):
            threads.extend(
                [
                    threading.Thread(target=create_worker("write", errors)),
                    threading.Thread(target=create_worker("read", errors)),
                ]
            )

        # Run all threads
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(errors) == 0

    def test_move_to_end_on_access(self, cache):
        """Test that accessing an item moves it to end (most recently used)."""
        # Fill cache
        for i in range(5):
            cache.set(f"key{i}", f"value{i}")

        # Access key0 multiple times
        for _ in range(3):
            cache.get("key0")

        # Add new item - should evict key1 not key0
        cache.set("key5", "value5")

        assert cache.get("key0") == "value0"  # Still there
        assert cache.get("key1") is None  # Evicted

    def test_complex_data_types(self, cache):
        """Test caching complex data types."""
        # List
        cache.set("list", [1, 2, 3])
        assert cache.get("list") == [1, 2, 3]

        # Dict
        cache.set("dict", {"a": 1, "b": 2})
        assert cache.get("dict") == {"a": 1, "b": 2}

        # Nested structures
        complex_data = {
            "users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
            "count": 2,
            "metadata": {"version": "1.0"},
        }
        cache.set("complex", complex_data)
        assert cache.get("complex") == complex_data


class TestStashEntityCache:
    """Test entity-specific cache functionality."""

    @pytest.fixture
    def cache(self):
        """Create cache instances for testing."""
        base_cache = StashCache(max_size=100, default_ttl=300)
        return StashEntityCache(base_cache)

    def test_performers_cache(self, cache):
        """Test caching performers."""
        performers = [
            {"id": "1", "name": "Performer One"},
            {"id": "2", "name": "Performer Two"},
        ]

        cache.set_performers(performers)

        # Check list is cached
        assert cache.get_performers() == performers

        # Check individual performers are cached by name
        assert cache.get_performer_by_name("Performer One")["id"] == "1"
        assert (
            cache.get_performer_by_name("performer one")["id"] == "1"
        )  # Case insensitive

        # Check cache keys
        assert cache.cache.get("entities:performers:id:1")["name"] == "Performer One"
        assert cache.cache.get("entities:performers:id:2")["name"] == "Performer Two"

    def test_tags_cache(self, cache):
        """Test caching tags."""
        tags = [
            {"id": "t1", "name": "Tag One", "aliases": []},
            {"id": "t2", "name": "Tag Two", "aliases": ["tag2"]},
        ]

        cache.set_tags(tags)

        # Check list is cached
        assert cache.get_tags() == tags

        # Check individual tags are cached by name
        assert cache.get_tag_by_name("Tag One")["id"] == "t1"
        assert cache.get_tag_by_name("tag one")["id"] == "t1"  # Case insensitive

    def test_studios_cache(self, cache):
        """Test caching studios."""
        studios = [
            {"id": "s1", "name": "Studio One", "url": "http://studio1.com"},
            {"id": "s2", "name": "Studio Two", "url": "http://studio2.com"},
        ]

        cache.set_studios(studios)

        # Check list is cached
        assert cache.get_studios() == studios

        # Check individual studios are cached by name
        assert cache.get_studio_by_name("Studio One")["id"] == "s1"
        assert cache.get_studio_by_name("studio one")["id"] == "s1"  # Case insensitive

    def test_invalidate_performers(self, cache):
        """Test invalidating performer cache."""
        performers = [{"id": "1", "name": "Performer One"}]
        cache.set_performers(performers)

        cache.invalidate_performers()

        assert cache.get_performers() is None
        assert cache.get_performer_by_name("Performer One") is None
        assert cache.cache.get("entities:performers:id:1") is None

    def test_invalidate_tags(self, cache):
        """Test invalidating tag cache."""
        tags = [{"id": "t1", "name": "Tag One"}]
        cache.set_tags(tags)

        cache.invalidate_tags()

        assert cache.get_tags() is None
        assert cache.get_tag_by_name("Tag One") is None

    def test_invalidate_studios(self, cache):
        """Test invalidating studio cache."""
        studios = [{"id": "s1", "name": "Studio One"}]
        cache.set_studios(studios)

        cache.invalidate_studios()

        assert cache.get_studios() is None
        assert cache.get_studio_by_name("Studio One") is None

    def test_invalidate_all(self, cache):
        """Test invalidating all entity caches."""
        # Set data for all entity types
        cache.set_performers([{"id": "1", "name": "Performer"}])
        cache.set_tags([{"id": "t1", "name": "Tag"}])
        cache.set_studios([{"id": "s1", "name": "Studio"}])

        cache.invalidate_all()

        # All should be gone
        assert cache.get_performers() is None
        assert cache.get_tags() is None
        assert cache.get_studios() is None

    def test_entity_ttl(self, cache):
        """Test that entity TTL is used correctly."""
        # Mock time to test TTL
        with patch("time.time") as mock_time:
            mock_time.return_value = 1000

            performers = [{"id": "1", "name": "Performer"}]
            cache.set_performers(performers)

            # Check TTL was set to 1 hour (3600 seconds)
            entry = cache.cache._cache["entities:performers:all"]
            assert entry["expires_at"] == 1000 + 3600

    def test_missing_fields(self, cache):
        """Test handling entities with missing fields."""
        # Performers without IDs or names
        performers = [
            {"id": "1"},  # No name
            {"name": "No ID"},  # No ID
            {"id": "3", "name": "Complete"},
        ]

        cache.set_performers(performers)

        # Should handle missing fields gracefully
        assert cache.get_performers() == performers
        assert cache.cache.get("entities:performers:id:1") is not None
        assert cache.get_performer_by_name("No ID") is not None
        assert cache.get_performer_by_name("Complete") is not None

    def test_empty_lists(self, cache):
        """Test caching empty lists."""
        cache.set_performers([])
        cache.set_tags([])
        cache.set_studios([])

        assert cache.get_performers() == []
        assert cache.get_tags() == []
        assert cache.get_studios() == []

    def test_case_sensitivity(self, cache):
        """Test case sensitivity in lookups."""
        performers = [
            {"id": "1", "name": "MiXeD CaSe NaMe"},
            {"id": "2", "name": "UPPERCASE NAME"},
            {"id": "3", "name": "lowercase name"},
        ]

        cache.set_performers(performers)

        # All lookups should work regardless of case
        assert cache.get_performer_by_name("mixed case name")["id"] == "1"
        assert cache.get_performer_by_name("MIXED CASE NAME")["id"] == "1"
        assert cache.get_performer_by_name("uppercase name")["id"] == "2"
        assert cache.get_performer_by_name("LOWERCASE NAME")["id"] == "3"


class TestCacheIntegration:
    """Test cache integration scenarios."""

    def test_cache_size_limits(self):
        """Test that cache respects size limits with entity cache."""
        base_cache = StashCache(max_size=10, default_ttl=300)
        entity_cache = StashEntityCache(base_cache)

        # Add 5 performers (will create 11 cache entries: 1 list + 5 by ID + 5 by name)
        # This exceeds max_size of 10
        performers = [{"id": str(i), "name": f"Performer {i}"} for i in range(5)]
        entity_cache.set_performers(performers)

        # Cache should have evicted oldest entries to stay within limit
        assert base_cache.size() <= 10

    def _run_entity_updates(self, entity_cache, errors_list):
        """Helper to run entity update operations."""
        try:
            for i in range(50):
                performers = [
                    {"id": str(j), "name": f"Performer {j}"} for j in range(i, i + 5)
                ]
                entity_cache.set_performers(performers)
        except Exception as e:
            errors_list.append(e)

    def _run_entity_reads(self, entity_cache, errors_list):
        """Helper to run entity read operations."""
        try:
            for _ in range(100):
                entity_cache.get_performers()
                entity_cache.get_performer_by_name("Performer 10")
        except Exception as e:
            errors_list.append(e)

    def test_concurrent_entity_operations(self):
        """Test concurrent operations on entity cache."""
        base_cache = StashCache(max_size=1000, default_ttl=300)
        entity_cache = StashEntityCache(base_cache)
        errors = []

        # Create threads for concurrent operations
        threads = []
        for _ in range(3):
            threads.append(
                threading.Thread(
                    target=self._run_entity_updates, args=(entity_cache, errors)
                )
            )
            threads.append(
                threading.Thread(
                    target=self._run_entity_reads, args=(entity_cache, errors)
                )
            )

        # Execute all threads
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(errors) == 0

    @pytest.mark.parametrize(
        "pattern,expected_remaining",
        [
            ("entities:performers:", ["entities:tags:all", "entities:studios:all"]),
            ("entities:tags:", ["entities:performers:all", "entities:studios:all"]),
            ("entities:", []),  # Should clear all
            (
                "nonexistent:",
                [
                    "entities:performers:all",
                    "entities:tags:all",
                    "entities:studios:all",
                ],
            ),
        ],
    )
    def test_pattern_invalidation(self, pattern, expected_remaining):
        """Test pattern-based cache invalidation."""
        base_cache = StashCache()

        # Set some test data
        base_cache.set("entities:performers:all", [])
        base_cache.set("entities:tags:all", [])
        base_cache.set("entities:studios:all", [])

        base_cache.invalidate_pattern(pattern)

        # Check what remains
        remaining_keys = []
        for key in [
            "entities:performers:all",
            "entities:tags:all",
            "entities:studios:all",
        ]:
            if base_cache.get(key) is not None:
                remaining_keys.append(key)

        assert sorted(remaining_keys) == sorted(expected_remaining)
