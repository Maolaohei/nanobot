from __future__ import annotations

from pathlib import Path
from typing import Any

from nanobot.agent.context import ContextBuilder


def _make_history(n: int) -> list[dict[str, Any]]:
    hist: list[dict[str, Any]] = []
    for i in range(n):
        hist.append({"role": "user", "content": f"u{i}"})
        hist.append({"role": "assistant", "content": f"a{i}"})
    return hist


def test_history_is_summarized_and_window_kept(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)
    builder = ContextBuilder(workspace)

    history = _make_history(5)  # 10 messages total
    msgs = builder.build_messages(
        history=history,
        current_message="ping",
        channel="cli",
        chat_id="direct",
        keep_recent=4,  # keep last 4 messages
    )

    # layout: [system] + [summary user?] + kept_history(4) + [final user]
    assert msgs[0]["role"] == "system"
    # summary should exist because history > keep_recent
    assert msgs[1]["role"] == "user"
    assert ContextBuilder._RUNTIME_CONTEXT_TAG in msgs[1]["content"]
    assert "Earlier summary:" in msgs[1]["content"]

    # Ensure only last 4 of original history are present (plus summary)
    kept_chunk = msgs[2:-1]
    kept_texts = [m["content"] for m in kept_chunk]
    assert kept_texts == ["u4", "a4", "u5", "a5"]

    # Final user message should contain merged runtime context and text
    assert msgs[-1]["role"] == "user"
    assert ContextBuilder._RUNTIME_CONTEXT_TAG in msgs[-1]["content"]
    assert "ping" in msgs[-1]["content"]
