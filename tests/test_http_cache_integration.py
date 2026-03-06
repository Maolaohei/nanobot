import os
import json
import asyncio
from pathlib import Path

import httpx
import pytest

from nanobot.utils.http import request as http_request


@pytest.mark.asyncio
async def test_http_global_cache_env_enabled(tmp_path, monkeypatch):
    # enable cache
    monkeypatch.setenv("NANOBOT_CACHE_ENABLED", "true")
    # First request — go to network (use httpbin.org/json which is stable JSON)
    r1 = await http_request("GET", "https://httpbin.org/json")
    assert r1.status_code == 200
    data1 = r1.json()
    # Second request — should hit cache path (still status 200, content equal)
    r2 = await http_request("GET", "https://httpbin.org/json")
    assert r2.status_code == 200
    data2 = r2.json()
    assert data1 == data2


@pytest.mark.asyncio
async def test_http_global_cache_disable(monkeypatch):
    # disable cache, ensure request still works
    monkeypatch.setenv("NANOBOT_CACHE_ENABLED", "false")
    r = await http_request("GET", "https://httpbin.org/headers")
    assert r.status_code == 200
