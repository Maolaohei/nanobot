import os
import tempfile
from pathlib import Path

import pytest

from nanobot.utils.cache import SimpleCache, DEFAULT_TTL


def test_simple_cache_put_get_and_expiry():
    with tempfile.TemporaryDirectory() as td:
        cache = SimpleCache(root=td)
        url = "https://example.com/article"
        entry = cache.put(url, 200, {"Cache-Control": "max-age=1", "ETag": "abc"}, "hello")
        assert entry.url == url
        got = cache.get(url)
        assert got is not None
        assert got.status == 200
        assert got.headers.get("etag") == "abc"
        assert got.expired() is False


def test_simple_cache_refresh_on_304_updates_time_and_headers():
    with tempfile.TemporaryDirectory() as td:
        cache = SimpleCache(root=td)
        url = "https://example.com/json"
        cache.put(url, 200, {"Cache-Control": "max-age=1"}, "{}")
        before = cache.get(url)
        assert before is not None
        # simulate 304 revalidation response headers
        cache.refresh(url, {"ETag": "xyz", "Cache-Control": "max-age=60"})
        after = cache.get(url)
        assert after is not None
        assert after.headers.get("etag") == "xyz"
        assert after.ttl == 60
