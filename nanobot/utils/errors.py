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
