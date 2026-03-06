import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

import httpx

from nanobot.utils.http import HttpClientFactory, request as http_request


@dataclass
class HttpRequest:
    method: str
    url: str
    headers: dict[str, str] | None = None
    params: dict[str, Any] | None = None
    json: Any | None = None
    data: Any | None = None


@dataclass
class HttpResponse:
    status: int
    headers: dict[str, str]
    text: str


class HttpAdapter:
    """Thin adapter over httpx with factory integration.

    This allows swapping transport, injecting retries, caching, etc.
    """

    def __init__(self, proxy: str | None = None, rate_limit: int | None = None):
        self._factory = HttpClientFactory(proxy=proxy, rate_limit=rate_limit)

    async def send(self, req: HttpRequest) -> HttpResponse:
        client = self._factory.create()
        r = await http_request(
            req.method,
            req.url,
            client=client,
            headers=req.headers,
            params=req.params,
            json=req.json,
            data=req.data,
        )
        return HttpResponse(status=r.status_code, headers=dict(r.headers), text=r.text)
