from __future__ import annotations

from typing import Any, Dict

from nanobot.utils.adapters import AdapterHub
from nanobot.config.schema import AppSettings

ExecutionContext = Dict[str, Any]


def build_adapter_hub(settings: AppSettings) -> AdapterHub:
    hub = AdapterHub()

    # Example: feature flags adapter injects flags into context for downstream consumers
    async def feature_flags_adapter(ctx: ExecutionContext) -> ExecutionContext:  # type: ignore[override]
        ctx["feature_flags"] = getattr(settings, "features", None).model_dump() if hasattr(settings, "features") else {}
        return ctx

    # Example: logging adapter attaches request_id into log extras if present
    async def logging_adapter(ctx: ExecutionContext) -> ExecutionContext:  # type: ignore[override]
        rid = ctx.get("request_id")
        if rid:
            ctx.setdefault("log_extra", {})["request_id"] = rid
        return ctx

    # Register as provider adapters by reusing the ChannelAdapter-style signature
    class _ContextInlet:
        async def on_inbound(self, message: dict[str, Any]) -> dict[str, Any]:
            return await feature_flags_adapter(message)

        async def on_outbound(self, message: dict[str, Any]) -> dict[str, Any]:
            return await logging_adapter(message)

    hub.register_channel(_ContextInlet())
    return hub
