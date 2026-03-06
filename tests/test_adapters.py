from __future__ import annotations

import asyncio
from typing import Any

import pytest

from nanobot.utils.adapters import AdapterHub


class DummySkill:
    def __init__(self):
        self.validated = False
        self.ran = False
        self.post = False

    async def validate(self, params: dict[str, Any]) -> None:
        self.validated = True

    async def run(self, params: dict[str, Any]) -> Any:
        self.ran = True
        return {"ok": True}

    async def postrun(self, result: Any) -> Any:
        self.post = True
        result["post"] = True
        return result


class DummyProvider:
    async def before_call(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload["before"] = True
        return payload

    async def after_call(self, response: Any) -> Any:
        response["after"] = True
        return response


class DummyChannel:
    async def on_inbound(self, message: dict[str, Any]) -> dict[str, Any]:
        message["in"] = True
        return message

    async def on_outbound(self, message: dict[str, Any]) -> dict[str, Any]:
        message["out"] = True
        return message


@pytest.mark.asyncio
async def test_adapter_hub_flow():
    hub = AdapterHub()
    s = DummySkill()
    p = DummyProvider()
    c = DummyChannel()

    hub.register_skill(s)
    hub.register_provider(p)
    hub.register_channel(c)

    await hub.skill_validate({})
    result = await hub.skill_run({})
    result = await hub.skill_postrun(result)
    assert s.validated and s.ran and s.post
    assert result["post"] is True

    payload = await hub.provider_before({})
    assert payload["before"] is True
    resp = await hub.provider_after({})
    assert resp["after"] is True

    msg = await hub.channel_inbound({})
    assert msg["in"] is True
    msg = await hub.channel_outbound(msg)
    assert msg["out"] is True
