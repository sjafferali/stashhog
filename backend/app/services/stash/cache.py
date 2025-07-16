"""Simple in-memory cache for Stash API data."""

import threading
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional


class StashCache:
    """TTL-based in-memory cache for frequently accessed Stash data."""

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Initialize cache.

        Args:
            max_size: Maximum number of items to cache
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]
            if time.time() > entry["expires_at"]:
                # Entry expired, remove it
                del self._cache[key]
                return None

            # Move to end to maintain LRU order
            self._cache.move_to_end(key)
            return entry["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL."""
        with self._lock:
            expires_at = time.time() + (ttl or self.default_ttl)

            # Remove oldest items if at capacity
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)

            self._cache[key] = {"value": value, "expires_at": expires_at}

    def delete(self, key: str) -> None:
        """Delete key from cache."""
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()

    def invalidate_pattern(self, pattern: str) -> None:
        """Invalidate all keys matching pattern."""
        with self._lock:
            keys_to_delete = [key for key in self._cache.keys() if pattern in key]
            for key in keys_to_delete:
                del self._cache[key]

    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)


class StashEntityCache:
    """Specialized cache for Stash entities (performers, tags, studios)."""

    def __init__(self, cache: StashCache):
        self.cache = cache
        self.entity_ttl = 3600  # 1 hour for entities

    def get_performers(self) -> Optional[List[Dict]]:
        """Get cached performers list."""
        return self.cache.get("entities:performers:all")

    def set_performers(self, performers: List[Dict]) -> None:
        """Cache performers list."""
        self.cache.set("entities:performers:all", performers, self.entity_ttl)
        # Also cache individual performers by ID and name
        for performer in performers:
            performer_id = performer.get("stash_id") or performer.get("id")
            if performer_id:
                self.cache.set(
                    f"entities:performers:id:{performer_id}", performer, self.entity_ttl
                )
            if performer.get("name"):
                self.cache.set(
                    f"entities:performers:name:{performer['name'].lower()}",
                    performer,
                    self.entity_ttl,
                )

    def get_performer_by_name(self, name: str) -> Optional[Dict]:
        """Get cached performer by name."""
        return self.cache.get(f"entities:performers:name:{name.lower()}")

    def get_tags(self) -> Optional[List[Dict]]:
        """Get cached tags list."""
        return self.cache.get("entities:tags:all")

    def set_tags(self, tags: List[Dict]) -> None:
        """Cache tags list."""
        self.cache.set("entities:tags:all", tags, self.entity_ttl)
        # Also cache individual tags by ID and name
        for tag in tags:
            tag_id = tag.get("stash_id") or tag.get("id")
            if tag_id:
                self.cache.set(f"entities:tags:id:{tag_id}", tag, self.entity_ttl)
            if tag.get("name"):
                self.cache.set(
                    f"entities:tags:name:{tag['name'].lower()}", tag, self.entity_ttl
                )

    def get_tag_by_name(self, name: str) -> Optional[Dict]:
        """Get cached tag by name."""
        return self.cache.get(f"entities:tags:name:{name.lower()}")

    def get_studios(self) -> Optional[List[Dict]]:
        """Get cached studios list."""
        return self.cache.get("entities:studios:all")

    def set_studios(self, studios: List[Dict]) -> None:
        """Cache studios list."""
        self.cache.set("entities:studios:all", studios, self.entity_ttl)
        # Also cache individual studios by ID and name
        for studio in studios:
            studio_id = studio.get("stash_id") or studio.get("id")
            if studio_id:
                self.cache.set(
                    f"entities:studios:id:{studio_id}", studio, self.entity_ttl
                )
            if studio.get("name"):
                self.cache.set(
                    f"entities:studios:name:{studio['name'].lower()}",
                    studio,
                    self.entity_ttl,
                )

    def get_studio_by_name(self, name: str) -> Optional[Dict]:
        """Get cached studio by name."""
        return self.cache.get(f"entities:studios:name:{name.lower()}")

    def invalidate_performers(self) -> None:
        """Invalidate all performer cache entries."""
        self.cache.invalidate_pattern("entities:performers:")

    def invalidate_tags(self) -> None:
        """Invalidate all tag cache entries."""
        self.cache.invalidate_pattern("entities:tags:")

    def invalidate_studios(self) -> None:
        """Invalidate all studio cache entries."""
        self.cache.invalidate_pattern("entities:studios:")

    def invalidate_all(self) -> None:
        """Invalidate all entity cache entries."""
        self.cache.invalidate_pattern("entities:")
