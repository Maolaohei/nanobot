from __future__ import annotations

import contextvars
import json
import time
import uuid
from typing import Any, Awaitable, Callable

from loguru import logger

# Request-scoped context
_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)


def set_request_id(value: str | None) -> None:
    _request_id.set(value)


def get_request_id() -> str | None:
    return _request_id.get()


class JsonLogSink:
    """Structured JSON logging sink for loguru.

    Usage:
        logger.remove()
        logger.add(JsonLogSink().write, level="INFO")
    """

    def __init__(self) -> None:
        self._write = logger._core.emit  # type: ignore[attr-defined]

    def write(self, message):  # loguru supplies a Message object
        record = message.record
        payload = {
            "ts": record["time"].timestamp(),
            "level": record["level"].name,
            "msg": record["message"],
            "module": record["name"],
            "file": record["file"].name,
            "line": record["line"],
            "function": record["function"],
            "request_id": get_request_id(),
        }
        # Attach extra dict if present (safe-merge)
        extra = record.get("extra") or {}
        if isinstance(extra, dict):
            for k, v in extra.items():
                if k not in payload:
                    payload[k] = v
        print(json.dumps(payload, ensure_ascii=False))


async def with_request_ctx(coro: Callable[[], Awaitable[Any]]) -> Any:
    rid = str(uuid.uuid4())
    token = _request_id.set(rid)
    try:
        start = time.perf_counter()
        try:
            return await coro()
        finally:
            dur_ms = int((time.perf_counter() - start) * 1000)
            logger.bind(request_id=rid).info("request_done {}ms", dur_ms)
    finally:
        _request_id.reset(token)
