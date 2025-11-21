"""
Caching system for API responses and metadata.

This module provides a simple file-based caching mechanism to reduce
redundant API calls and improve performance.
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from . import config
from .logger import logger


class Cache:
    """Simple file-based cache with TTL support."""

    def __init__(self, cache_dir: Optional[str] = None, default_ttl: int = 3600):
        """
        Initialize the cache.

        Args:
            cache_dir: Directory to store cache files. Defaults to app data dir.
            default_ttl: Default time-to-live in seconds (default: 1 hour).
        """
        self.cache_dir = Path(cache_dir or config.BASE_DATA_DIR) / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl

    def _get_cache_path(self, key: str) -> Path:
        """Get the file path for a cache key."""
        # Sanitize key for filesystem
        safe_key = "".join(c if c.isalnum() or c in "._-" else "_" for c in key)
        return self.cache_dir / f"{safe_key}.json"

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a value from cache.

        Args:
            key: Cache key.
            default: Default value if key not found or expired.

        Returns:
            Cached value or default.
        """
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return default

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            # Check if expired
            if cache_data.get("expires_at", 0) < time.time():
                cache_path.unlink()
                return default

            return cache_data.get("value", default)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read cache for key '{key}': {e}")
            return default

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Store a value in cache.

        Args:
            key: Cache key.
            value: Value to cache (must be JSON serializable).
            ttl: Time-to-live in seconds. Uses default_ttl if None.

        Returns:
            True if successful, False otherwise.
        """
        cache_path = self._get_cache_path(key)
        ttl = ttl if ttl is not None else self.default_ttl

        cache_data = {"value": value, "expires_at": time.time() + ttl, "created_at": time.time()}

        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)
            return True
        except (OSError, TypeError) as e:
            logger.warning(f"Failed to write cache for key '{key}': {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete a cache entry.

        Args:
            key: Cache key to delete.

        Returns:
            True if deleted, False if not found.
        """
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            try:
                cache_path.unlink()
                return True
            except OSError as e:
                logger.warning(f"Failed to delete cache for key '{key}': {e}")
        return False

    def clear(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries cleared.
        """
        count = 0
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
                count += 1
        except OSError as e:
            logger.warning(f"Failed to clear cache: {e}")
        return count

    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.

        Returns:
            Number of entries removed.
        """
        count = 0
        current_time = time.time()

        try:
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        cache_data = json.load(f)

                    if cache_data.get("expires_at", 0) < current_time:
                        cache_file.unlink()
                        count += 1
                except (json.JSONDecodeError, OSError):
                    # Remove corrupted cache files
                    cache_file.unlink()
                    count += 1
        except OSError as e:
            logger.warning(f"Failed to cleanup expired cache: {e}")

        return count


# Global cache instance
_cache_instance: Optional[Cache] = None


def get_cache() -> Cache:
    """Get or create the global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = Cache()
    return _cache_instance
