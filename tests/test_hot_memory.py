import json
from pathlib import Path

from nanobot.agent.hot_memory import HotMemoryStore


def test_hot_memory_roundtrip(tmp_path: Path):
    store = HotMemoryStore(tmp_path)
    key = "cli:direct"

    # Initially empty brief
    assert store.get_brief(key) == []

    store.set_goal(key, "Finish MVP")
    store.add_fact(key, "Repo", "Maolaohei/nanobot")
    store.add_fact(key, "Token", "sk-1234567890abcdef")  # should redact
    store.add_todo(key, "Write docs")

    brief = store.get_brief(key)
    joined = "\n".join(brief)
    assert "Finish MVP" in joined
    assert "Maolaohei/nanobot" in joined
    assert "[REDACTED]" in joined

    # Persistence
    p = tmp_path / "sessions" / "hot" / "cli_direct.json"
    assert p.exists()
    data = json.loads(p.read_text(encoding="utf-8"))
    assert isinstance(data.get("facts"), list)
