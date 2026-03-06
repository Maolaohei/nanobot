import json
import os
import time
from pathlib import Path

import pytest

from nanobot.utils.cache import SimpleCache
from nanobot.utils.http import request as http_request


@pytest.mark.asyncio
async def test_http_cache_304_revalidation(monkeypatch):
    # Ensure cache is enabled
    monkeypatch.setenv("NANOBOT_CACHE_ENABLED", "true")

    url = "https://httpbin.org/etag/nanobot-cache-test"

    # First request populates cache
    r1 = await http_request("GET", url)
    assert r1.status_code == 200
    body1 = r1.text

    # Force the cache entry to be stale to trigger validators on next request
    cache = SimpleCache()  # uses default ~/.nanobot/cache
    entry = cache.get(url)
    assert entry is not None

    meta_path = Path(entry.body_path).with_name("meta.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["stored_at"] = time.time() - 3600 * 24  # stale
    meta["ttl"] = 0
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # Second request should send If-None-Match and receive 304 from httpbin,
    # then serve cached body transparently (status remains 200 from cached entry)
    r2 = await http_request("GET", url)
    assert r2.status_code == 200
    assert r2.text == body1
