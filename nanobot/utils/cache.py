from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from loguru import logger


SAFE_HEADERS = {"etag", "last-modified", "cache-control", "expires"}
CACHEABLE_CT = ("text/html", "application/json", "text/plain")
DEFAULT_TTL = 3600  # seconds, fallback when no cache headers


@dataclass
class CacheEntry:
    url: str
    status: int
    headers: dict[str, str]
    body_path: str  # path to body file (utf-8 text)
    stored_at: float
    ttl: int

    def expired(self) -> bool:
        return (time.time() - self.stored_at) > self.ttl


class SimpleCache:
    """Filesystem-backed HTTP response cache (text-only).

    - Keyed by URL + method (GET only by default)
    - Stores safe headers + text body to files
    - Honors Cache-Control max-age, Expires; falls back to DEFAULT_TTL
    - Provides validators (ETag/If-None-Match, If-Modified-Since)
    """

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root or Path.home() / ".nanobot" / "cache")
        self.root.mkdir(parents=True, exist_ok=True)

    def _key(self, url: str) -> str:
        return hashlib.sha1(url.encode("utf-8")).hexdigest()

    def _dir(self, url: str) -> Path:
        return self.root / self._key(url)

    def _meta_path(self, url: str) -> Path:
        return self._dir(url) / "meta.json"

    def _body_path(self, url: str) -> Path:
        return self._dir(url) / "body.txt"

    def get(self, url: str) -> CacheEntry | None:
        meta_p = self._meta_path(url)
        body_p = self._body_path(url)
        if not meta_p.exists() or not body_p.exists():
            return None
        try:
            meta = json.loads(meta_p.read_text(encoding="utf-8"))
            return CacheEntry(
                url=meta["url"],
                status=meta.get("status", 200),
                headers=meta.get("headers", {}),
                body_path=str(body_p),
                stored_at=meta.get("stored_at", 0),
                ttl=meta.get("ttl", DEFAULT_TTL),
            )
        except Exception as e:
            logger.warning("cache read failed for {}: {}", url, e)
            return None

    def put(self, url: str, status: int, headers: dict[str, str], text: str) -> CacheEntry:
        d = self._dir(url)
        d.mkdir(parents=True, exist_ok=True)
        body_p = self._body_path(url)
        body_p.write_text(text, encoding="utf-8")
        ttl = self._ttl_from_headers(headers)
        meta = {
            "url": url,
            "status": status,
            "headers": {k.lower(): v for k, v in headers.items() if k.lower() in SAFE_HEADERS},
            "stored_at": time.time(),
            "ttl": ttl,
        }
        self._meta_path(url).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return CacheEntry(url=url, status=status, headers=meta["headers"], body_path=str(body_p), stored_at=meta["stored_at"], ttl=ttl)

    def refresh(self, url: str, headers: dict[str, str] | None = None) -> None:
        """Refresh stored_at and optionally safe headers after 304 revalidation."""
        meta_p = self._meta_path(url)
        if not meta_p.exists():
            return
        try:
            meta = json.loads(meta_p.read_text(encoding="utf-8"))
            meta["stored_at"] = time.time()
            if headers:
                safe = {k.lower(): v for k, v in headers.items() if k.lower() in SAFE_HEADERS}
                meta_headers = meta.get("headers", {})
                meta_headers.update(safe)
                meta["headers"] = meta_headers
                meta["ttl"] = self._ttl_from_headers(meta_headers)
            meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug("cache refresh failed for {}: {}", url, e)

    def validators(self, entry: CacheEntry) -> dict[str, str]:
        hdrs: dict[str, str] = {}
        etag = entry.headers.get("etag")
        lastmod = entry.headers.get("last-modified")
        if etag:
            hdrs["If-None-Match"] = etag
        if lastmod:
            hdrs["If-Modified-Since"] = lastmod
        return hdrs

    def _ttl_from_headers(self, headers: dict[str, str]) -> int:
        cc = headers.get("cache-control", "")
        m = re.search(r"max-age=(\d+)", cc)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass
        exp = headers.get("expires")
        if exp:
            # Not parsing HTTP-date; use DEFAULT_TTL when Expires exists
            return DEFAULT_TTL
        return DEFAULT_TTL


def use_cache(
    cache: SimpleCache,
    fetcher: Callable[[dict[str, str]], Any],
    url: str,
    *,
    force_refresh: bool = False,
) -> tuple[bool, CacheEntry | None, str | None, dict[str, str]]:
    """Prepare cache usage.

    Returns: (should_short_circuit, entry, cached_text, request_headers)
    - If should_short_circuit is True, caller can return cached_text directly
    - Otherwise, include request_headers to validate with origin
    """
    if force_refresh:
        return False, None, None, {}
    entry = cache.get(url)
    if not entry:
        return False, None, None, {}
    if not entry.expired():
        text = Path(entry.body_path).read_text(encoding="utf-8", errors="ignore")
        logger.debug("cache hit fresh: {}", url)
        return True, entry, text, {}
    # stale: try validators
    headers = cache.validators(entry)
    logger.debug("cache stale -> revalidate: {}", url)
    return False, entry, None, headers
