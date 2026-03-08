from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from nanobot.agent.context import ContextBuilder
from nanobot.providers.litellm_provider import LiteLLMProvider


class _FakeFunction:
    def __init__(self, name: str, arguments: str):
        self.name = name
        self.arguments = arguments


class _FakeToolCall:
    def __init__(self, id: str, name: str, arguments: str):
        self.id = id
        self.function = _FakeFunction(name, arguments)


def test_litellm_provider_preserves_tool_call_id() -> None:
    provider = LiteLLMProvider(default_model="openai/gpt-4o-mini")
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                finish_reason="tool_calls",
                message=SimpleNamespace(
                    content=None,
                    tool_calls=[_FakeToolCall("call_real_123", "web_search", '{"query":"x"}')],
                    reasoning_content=None,
                    thinking_blocks=None,
                ),
            )
        ],
        usage=None,
    )

    parsed = provider._parse_response(response)

    assert parsed.tool_calls[0].id == "call_real_123"
    assert parsed.tool_calls[0].name == "web_search"
    assert parsed.tool_calls[0].arguments == {"query": "x"}


def test_history_window_repairs_leading_tool_result_boundary(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)
    builder = ContextBuilder(workspace)

    history = [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_abc",
                    "type": "function",
                    "function": {"name": "web_search", "arguments": '{"query":"x"}'},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call_abc", "name": "web_search", "content": "ok"},
        {"role": "assistant", "content": "done"},
    ]

    msgs = builder.build_messages(
        history=history,
        current_message="next",
        channel="cli",
        chat_id="direct",
        keep_recent=2,
    )

    roles = [m["role"] for m in msgs]
    assert roles == ["system", "assistant", "tool", "assistant", "user"]
    assert msgs[1]["tool_calls"][0]["id"] == "call_abc"
    assert msgs[2]["tool_call_id"] == "call_abc"
