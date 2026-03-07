from __future__ import annotations

import os
from pathlib import Path

from nanobot.agent.context import ContextBuilder


def test_memory_injection_budget_limits_total_lines(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "memory").mkdir(parents=True)
    # Write MEMORY.md with many kv lines
    mem = workspace / "memory" / "MEMORY.md"
    mem.write_text(
        """
User: Maolaohei
Preference: 草莓味甜甜圈
Project: nanobot
Repo: github.com/Maolaohei/nanobot
Editor: Neovim
Theme: Dark
Skill: pixiv-pro
Limit: no secrets in logs
""".strip(),
        encoding="utf-8",
    )

    # Build index file
    from nanobot.agent.facts_index import build_index, save_index
    facts = build_index(mem.read_text(encoding="utf-8"))
    save_index(workspace, facts)

    # Set env: enable injector with small total budget
    os.environ["NANOBOT_MEMORY_INJECTOR"] = "true"
    os.environ["NANOBOT_MEMORY_BUDGET_MAX_LINES"] = "3"
    os.environ["NANOBOT_MEMORY_FACTS_ENABLED"] = "true"
    os.environ["NANOBOT_MEMORY_FACTS_LIMIT"] = "10"

    builder = ContextBuilder(workspace)
    system = builder.build_system_prompt(user_message="关于 nanobot 的项目细节？", session_key=None)

    # Count lines under Relevant Facts section
    rel_start = system.find("# Relevant Facts")
    assert rel_start != -1
    block = system[rel_start:]
    # lines starting with dash in facts block
    lines = [ln for ln in block.splitlines() if ln.strip().startswith("-")]
    # Should be <= total budget (since hot memory is zero, all budget goes to facts)
    assert len(lines) <= 3

    # Cleanup env
    os.environ.pop("NANOBOT_MEMORY_INJECTOR", None)
    os.environ.pop("NANOBOT_MEMORY_BUDGET_MAX_LINES", None)
    os.environ.pop("NANOBOT_MEMORY_FACTS_ENABLED", None)
    os.environ.pop("NANOBOT_MEMORY_FACTS_LIMIT", None)
