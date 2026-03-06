from __future__ import annotations

import asyncio
from typing import Any

import httpx
from loguru import logger

SAFE_STATUS_NO_RETRY = {401, 403, 404, 412}
DEFAULT_TIMEOUT = httpx.Timeout(30.0)
DEFAULT_LIMITS = httpx.Limits(max_keepalive_connections=20, max_connections=100)
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/537.36",
}


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
        )
        return self._wrap(client)


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
    """
    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT,
            limits=DEFAULT_LIMITS,
            headers={**DEFAULT_HEADERS, **(headers or {})},
            proxy=proxy,
            follow_redirects=True,
        )
    try:
        r = await client.request(method.upper(), url, headers=headers, **kwargs)
        if r.status_code in SAFE_STATUS_NO_RETRY:
            logger.warning("HTTP no-retry {} {} -> {}", method, url, r.status_code)
            return r
        r.raise_for_status()
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
