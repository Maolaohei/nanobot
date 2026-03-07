from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

from nanobot.utils.cache import SimpleCache, CACHEABLE_CT
from nanobot.utils.rate_limiter import PerDomainLimiter
from nanobot.metrics import inc

SAFE_STATUS_NO_RETRY = {401, 403, 404, 412}
DEFAULT_TIMEOUT = httpx.Timeout(30.0)
DEFAULT_LIMITS = httpx.Limits(max_keepalive_connections=20, max_connections=100)
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/537.36",
}

# Global cache (enabled by default). Toggle via env NANOBOT_CACHE_ENABLED=false
_GLOBAL_CACHE: SimpleCache | None = None

# Global per-domain limiter (lazy init)
_LIMITER: PerDomainLimiter | None = None


def _rate_limit_enabled_env() -> bool:
    # Default ON in minimal runtime policy; can be disabled by env
    v = os.environ.get("NANOBOT_HTTP_RATE_LIMIT_ENABLED", "true").lower()
    return v not in {"0", "false", "no"}


def _get_limiter() -> PerDomainLimiter | None:
    global _LIMITER
    if _LIMITER is not None:
        return _LIMITER
    try:
        if _rate_limit_enabled_env():
            _LIMITER = PerDomainLimiter(1.0, 5)
        else:
            _LIMITER = None
    except Exception:
        _LIMITER = PerDomainLimiter(1.0, 5) if _rate_limit_enabled_env() else None
    return _LIMITER


- def _limiter_hook(request: httpx.Request):
-    lim = _get_limiter()
-    if lim is None:
-        return
-    try:
-        host = request.url.host or ""
-        lim.throttle(host)
-    except Exception:
-        return
+ async def _limiter_hook(request: httpx.Request) -> None:
+    """Async event hook for httpx to enforce per-domain rate limits."""
+    lim = _get_limiter()
+    if lim is None:
+        return None
+    try:
+        host = request.url.host or ""
+        lim.throttle(host)
+    except Exception:
+        return None


def _cache_enabled_env() -> bool:
    return os.environ.get("NANOBOT_CACHE_ENABLED", "true").lower() not in {"0", "false", "no"}


def _get_global_cache() -> SimpleCache | None:
    global _GLOBAL_CACHE
    enabled = _cache_enabled_env()
    if enabled and _GLOBAL_CACHE is None:
        _GLOBAL_CACHE = SimpleCache()
    if not enabled and _GLOBAL_CACHE is not None:
        _GLOBAL_CACHE = None
    return _GLOBAL_CACHE


class HttpClientFactory:
    """Create opinionated httpx clients with sane defaults.

    - Timeouts, connection limits, UA header
    - No-retry list (401/403/404/412)
    - Optional rate limiting via asyncio.Semaphore
    """

    def __init__(self, proxy: str | None = None, rate_limit: int | None = None):
        self.proxy = proxy
        self._sem = asyncio.Semaphore(rate_limit) if rate_limit and rate_limit > 0 else None

    def _wrap(self, client: httpx.AsyncClient):
        if not self._sem:
            return client

        class _Wrapper:
            def __init__(self, c: httpx.AsyncClient, sem: asyncio.Semaphore):
                self._c, self._s = c, sem

            async def get(self, *a, **kw):
                async with self._s:
                    return await self._c.get(*a, **kw)

            async def post(self, *a, **kw):
                async with self._s:
                    return await self._c.post(*a, **kw)

            async def request(self, *a, **kw):
                async with self._s:
                    return await self._c.request(*a, **kw)

            async def aclose(self):
                await self._c.aclose()

            @property
            def headers(self):
                return self._c.headers

        return _Wrapper(client, self._sem)

    def create(self) -> Any:
        client = httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT,
            limits=DEFAULT_LIMITS,
            headers=DEFAULT_HEADERS.copy(),
            proxy=self.proxy,
            follow_redirects=True,
            event_hooks={"request": [_limiter_hook]},
        )
        return self._wrap(client)


def _cached_response(url: str, entry, text: str) -> httpx.Response:
    req = httpx.Request("GET", url)
    resp = httpx.Response(status_code=entry.status, headers=entry.headers, request=req, content=text.encode("utf-8"))
    resp.encoding = "utf-8"
    return resp


async def request(
    method: str,
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    proxy: str | None = None,
    headers: dict[str, str] | None = None,
    **kwargs: Any,
) -> httpx.Response:
    """Perform an HTTP request with unified behavior.

    - Adds default headers
    - Applies proxy if provided
    - Honors SAFE_STATUS_NO_RETRY by not retrying
    - Logs failures with method/url/status
    - Global cache for GET text/html/json/plain is enabled by default
    """
    owns_client = client is None
    headers = headers.copy() if headers else {}

    # Global cache: fresh-hit short circuit or add validators for revalidation
    cache_entry = None
    _GLOBAL = _get_global_cache()
    if _GLOBAL and method.upper() == "GET" and headers.get("Cache-Control", "").lower() != "no-cache":
        cache_entry = _GLOBAL.get(url)
        if cache_entry and not cache_entry.expired():
            try:
                text = Path(cache_entry.body_path).read_text(encoding="utf-8", errors="ignore")
                inc("http_cache_hit")
                logger.debug("HTTP cache hit fresh: {}", url)
                return _cached_response(url, cache_entry, text)
            except Exception as ce:
                logger.debug("HTTP cache read failed for {}: {}", url, ce)
        elif cache_entry:
            # stale: add validators
            validators = {}
            if et := cache_entry.headers.get("etag"):
                validators["If-None-Match"] = et
            if lm := cache_entry.headers.get("last-modified"):
                validators["If-Modified-Since"] = lm
            headers.update({k: v for k, v in validators.items() if k not in headers})

    if client is None:
        client = httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT,
            limits=DEFAULT_LIMITS,
            headers={**DEFAULT_HEADERS, **headers},
            proxy=proxy,
            follow_redirects=True,
            event_hooks={"request": [_limiter_hook]},
        )
        # Note: headers passed to request() still apply below
    try:
        inc("http_external_calls")
        r = await client.request(method.upper(), url, headers=headers, **kwargs)

        # Revalidation: 304 => serve cached entity and refresh metadata
        if r.status_code == 304 and cache_entry and _GLOBAL:
            try:
                _GLOBAL.refresh(url, dict(r.headers))
                text = Path(cache_entry.body_path).read_text(encoding="utf-8", errors="ignore")
                inc("http_cache_revalidated")
                logger.debug("HTTP cache revalidated (304): {}", url)
                return _cached_response(url, cache_entry, text)
            except Exception as ce:
                logger.debug("HTTP cache 304 handling failed for {}: {}", url, ce)

        # No-retry statuses return directly
        if r.status_code in SAFE_STATUS_NO_RETRY:
            logger.warning("HTTP no-retry {} {} -> {}", method, url, r.status_code)
            return r

        r.raise_for_status()

        # Store cacheable content
        if _GLOBAL and method.upper() == "GET":
            ctype = r.headers.get("content-type", "")
            if any(t in ctype for t in CACHEABLE_CT) or ctype.startswith("text/"):
                try:
                    text = r.text
                    _GLOBAL.put(url, r.status_code, {k.lower(): v for k, v in r.headers.items()}, text)
                except Exception as ce:
                    logger.debug("HTTP cache put failed for {}: {}", url, ce)

        return r
    except httpx.ProxyError as e:
        logger.error("HTTP proxy error for {} {}: {}", method, url, e)
        raise
    except httpx.TimeoutException as e:
        logger.error("HTTP timeout for {} {}: {}", method, url, e)
        raise
    except httpx.HTTPStatusError as e:
        logger.error("HTTP error for {} {}: {}", method, url, e)
        raise
    finally:
        if owns_client:
            await client.aclose()
