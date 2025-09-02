import hashlib
import json
import time
from pathlib import Path
from typing import Optional
from utils.logger import logger


class Cache:
    """
    A simple file-based cache for storing LLM responses.
    """

    def __init__(self, cache_dir: str, ttl_sec: int):
        """
        Initializes the cache.

        Args:
            cache_dir: The directory to store cache files.
            ttl_sec: The time-to-live for cache entries in seconds. If <= 0, cache is disabled.
        """
        self.cache_dir = Path(cache_dir).expanduser()
        self.ttl_sec = ttl_sec
        if self.is_enabled():
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
            except (IOError, OSError) as e:
                logger.warning(f"Could not create cache directory at {self.cache_dir}: {e}. Caching will be disabled.")
                self.ttl_sec = 0 # Disable cache if dir creation fails

    def is_enabled(self) -> bool:
        """Checks if the cache is enabled."""
        return self.ttl_sec > 0

    def _get_key(self, content: str) -> str:
        """Generates a SHA256 hash for the given content to use as a cache key."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def get(self, content: str) -> Optional[str]:
        """
        Retrieves an item from the cache if it exists and is not expired.
        The key is the hash of the content itself.

        Args:
            content: The content whose response may be cached.

        Returns:
            The cached response string, or None if not found or expired.
        """
        if not self.is_enabled():
            return None

        key = self._get_key(content)
        cache_file = self.cache_dir / key
        if not cache_file.exists():
            logger.debug(f"Cache miss (key not found): {key}")
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            timestamp = data.get("timestamp", 0)
            if time.time() - timestamp > self.ttl_sec:
                logger.debug(f"Cache miss (expired): {key}")
                cache_file.unlink()  # Delete expired cache file
                return None

            logger.debug(f"Cache hit: {key}")
            return data.get("value")
        except (IOError, json.JSONDecodeError, OSError) as e:
            logger.warning(f"Could not read or decode cache file {cache_file}: {e}")
            return None

    def set(self, content: str, value: str):
        """
        Saves an item to the cache. The key is the hash of the content.

        Args:
            content: The content to use for the key.
            value: The response to store in the cache.
        """
        if not self.is_enabled():
            return

        key = self._get_key(content)
        cache_file = self.cache_dir / key
        data = {
            "timestamp": time.time(),
            "value": value
        }
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Cached new item with key: {key}")
        except (IOError, OSError) as e:
            logger.warning(f"Could not write to cache file {cache_file}: {e}")
