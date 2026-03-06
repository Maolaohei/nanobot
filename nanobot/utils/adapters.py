"""Adapter architecture: Provider, Channel, Skill.

This module defines thin adapter interfaces and a minimal wiring point
that can be incrementally adopted without breaking existing modules.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable, Optional

from loguru import logger


@runtime_checkable
class SkillAdapter(Protocol):
    async def validate(self, params: dict[str, Any]) -> None: ...
    async def run(self, params: dict[str, Any]) -> Any: ...
    async def postrun(self, result: Any) -> Any: ...


@runtime_checkable
class ProviderAdapter(Protocol):
    async def before_call(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    async def after_call(self, response: Any) -> Any: ...


@runtime_checkable
class ChannelAdapter(Protocol):
    async def on_inbound(self, message: dict[str, Any]) -> dict[str, Any]: ...
    async def on_outbound(self, message: dict[str, Any]) -> dict[str, Any]: ...


@dataclass
class AdapterContext:
    request_id: str
    trace_id: Optional[str] = None
    extra: dict[str, Any] = None


class AdapterHub:
    """Registry and lightweight dispatcher for adapters.

    - Allows multiple adapters per type
    - Preserves order of registration
    - No hard dependency from existing code; can be injected gradually
    """

    def __init__(self) -> None:
        self._skills: list[SkillAdapter] = []
        self._providers: list[ProviderAdapter] = []
        self._channels: list[ChannelAdapter] = []

    def register_skill(self, adapter: SkillAdapter) -> None:
        self._skills.append(adapter)

    def register_provider(self, adapter: ProviderAdapter) -> None:
        self._providers.append(adapter)

    def register_channel(self, adapter: ChannelAdapter) -> None:
        self._channels.append(adapter)

    async def skill_validate(self, params: dict[str, Any]) -> None:
        for a in self._skills:
            await a.validate(params)

    async def skill_run(self, params: dict[str, Any]) -> Any:
        result: Any = None
        for a in self._skills:
            result = await a.run(params)
        return result

    async def skill_postrun(self, result: Any) -> Any:
        for a in self._skills:
            result = await a.postrun(result)
        return result

    async def provider_before(self, payload: dict[str, Any]) -> dict[str, Any]:
        for a in self._providers:
            payload = await a.before_call(payload)
        return payload

    async def provider_after(self, response: Any) -> Any:
        for a in self._providers:
            response = await a.after_call(response)
        return response

    async def channel_inbound(self, message: dict[str, Any]) -> dict[str, Any]:
        for a in self._channels:
            message = await a.on_inbound(message)
        return message

    async def channel_outbound(self, message: dict[str, Any]) -> dict[str, Any]:
        for a in self._channels:
            message = await a.on_outbound(message)
        return message
