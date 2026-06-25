import hashlib
import json
import os
import threading
from typing import Any

_lock = threading.Lock()


class QueryCache:
    def __init__(self, cache_dir: str = "query_cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _key(self, *parts: str) -> str:
        raw = "|".join(parts)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"{key}.json")

    def get(self, namespace: str, *parts: str) -> Any | None:
        key = self._key(namespace, *parts)
        path = self._path(key)
        if not os.path.exists(path):
            return None
        with _lock:
            with open(path) as f:
                return json.load(f)

    def set(self, value: Any, namespace: str, *parts: str) -> None:
        key = self._key(namespace, *parts)
        path = self._path(key)
        with _lock:
            with open(path, "w") as f:
                json.dump(value, f)

    def invalidate(self, namespace: str, *parts: str) -> None:
        key = self._key(namespace, *parts)
        path = self._path(key)
        if os.path.exists(path):
            os.remove(path)

    def clear(self) -> None:
        for fname in os.listdir(self.cache_dir):
            if fname.endswith(".json"):
                os.remove(os.path.join(self.cache_dir, fname))
