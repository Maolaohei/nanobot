from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ErrorInfo:
    code: str
    message: str
    details: Optional[dict[str, Any]] = None


class ErrorCodes:
    # Generic
    INVALID_PARAMS = "ERR_INVALID_PARAMS"
    RUNTIME_ERROR = "ERR_RUNTIME"

    # HTTP / Web
    HTTP_PROXY = "ERR_HTTP_PROXY"
    HTTP_TIMEOUT = "ERR_HTTP_TIMEOUT"
    HTTP_STATUS = "ERR_HTTP_STATUS"

    # Tools
    TOOL_VALIDATE = "ERR_TOOL_VALIDATE"


class ToolError(Exception):
    def __init__(self, info: ErrorInfo):
        self.info = info
        super().__init__(f"{info.code}: {info.message}")

    def to_json(self) -> str:
        import json

        payload = {"error": self.info.code, "message": self.info.message}
        if self.info.details:
            payload["details"] = self.info.details
        return json.dumps(payload, ensure_ascii=False)


def error_json(code: str, message: str, details: Optional[dict[str, Any]] = None) -> str:
    """Serialize an error payload to JSON using the unified shape."""
    return ToolError(ErrorInfo(code=code, message=message, details=details)).to_json()


def map_exception(exc: Exception) -> ErrorInfo:
    """Map common exceptions into unified ErrorInfo.

    - httpx.ProxyError      -> ERR_HTTP_PROXY
    - httpx.TimeoutException-> ERR_HTTP_TIMEOUT
    - httpx.HTTPStatusError -> ERR_HTTP_STATUS (details: status, url)
    - ToolError             -> passthrough
    - otherwise             -> ERR_RUNTIME
    """
    # Avoid importing heavy deps at module import time
    try:
        import httpx  # type: ignore
    except Exception:  # pragma: no cover
        httpx = None  # type: ignore

    if isinstance(exc, ToolError):
        return exc.info

    if httpx is not None:
        if isinstance(exc, getattr(httpx, "ProxyError", tuple())):
            return ErrorInfo(code=ErrorCodes.HTTP_PROXY, message=str(exc))
        if isinstance(exc, getattr(httpx, "TimeoutException", tuple())):
            return ErrorInfo(code=ErrorCodes.HTTP_TIMEOUT, message=str(exc))
        if isinstance(exc, getattr(httpx, "HTTPStatusError", tuple())):
            status = getattr(getattr(exc, "response", None), "status_code", None)
            url = None
            try:
                if getattr(exc, "request", None) is not None:
                    url = str(exc.request.url)  # type: ignore[attr-defined]
                elif getattr(exc, "response", None) is not None:
                    url = str(exc.response.request.url)  # type: ignore[attr-defined]
            except Exception:
                url = None
            details = {"status": status}
            if url:
                details["url"] = url
            return ErrorInfo(code=ErrorCodes.HTTP_STATUS, message=str(exc), details=details)

    return ErrorInfo(code=ErrorCodes.RUNTIME_ERROR, message=str(exc) or exc.__class__.__name__)
