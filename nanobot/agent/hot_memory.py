"""Session Hot Memory store for goals, key facts, constraints, and todos.

MVP design:
- Per-session JSON file stored under ~/.nanobot/workspace/sessions/hot/{safe_key}.json
- Public API: load(), save(), get_brief() for compact injection
- Sanitization: redact sensitive tokens/passwords/keys
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from nanobot.utils.helpers import ensure_dir, safe_filename

_SENSITIVE_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"api[_-]?key\s*[:=]", r"secret\s*[:=]", r"token\s*[:=]", r"password\s*[:=]",
        r"sk-[A-Za-z0-9]{16,}", r"ghp_[A-Za-z0-9]{20,}", r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.",
    )
]


def _redact(v: str) -> str:
    t = v
    for pat in _SENSITIVE_PATTERNS:
        if pat.search(t):
            return "[REDACTED]"
    return t


@dataclass
class HotMemory:
    goals: list[str] = field(default_factory=list)
    facts: list[dict[str, Any]] = field(default_factory=list)  # {"k": str, "v": str, "ts": str}
    constraints: list[str] = field(default_factory=list)
    todos: list[str] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "goals": self.goals,
            "facts": self.facts,
            "constraints": self.constraints,
            "todos": self.todos,
            "updated_at": self.updated_at,
        }


class HotMemoryStore:
    def __init__(self, base_dir: Path):
        self.dir = ensure_dir(base_dir / "sessions" / "hot")

    def _path(self, session_key: str) -> Path:
        return self.dir / f"{safe_filename(session_key.replace(':', '_'))}.json"

    def load(self, session_key: str) -> HotMemory:
        p = self._path(session_key)
        if not p.exists():
            return HotMemory()
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            hm = HotMemory(
                goals=list(map(str, data.get("goals", []))),
                facts=list(data.get("facts", [])),
                constraints=list(map(str, data.get("constraints", []))),
                todos=list(map(str, data.get("todos", []))),
                updated_at=str(data.get("updated_at") or datetime.now().isoformat()),
            )
            return hm
        except Exception:
            return HotMemory()

    def save(self, session_key: str, mem: HotMemory) -> None:
        mem.updated_at = datetime.now().isoformat()
        p = self._path(session_key)
        p.write_text(json.dumps(mem.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def add_fact(self, session_key: str, k: str, v: str) -> None:
        hm = self.load(session_key)
        hm.facts = [f for f in hm.facts if f.get("k") != k]
        hm.facts.append({"k": k, "v": _redact(v), "ts": datetime.now().isoformat()})
        self.save(session_key, hm)

    def set_goal(self, session_key: str, goal: str) -> None:
        hm = self.load(session_key)
        if goal not in hm.goals:
            hm.goals.append(goal)
        self.save(session_key, hm)

    def add_todo(self, session_key: str, todo: str) -> None:
        hm = self.load(session_key)
        hm.todos.append(todo)
        self.save(session_key, hm)

    def get_brief(self, session_key: str, max_facts: int = 5) -> list[str]:
        hm = self.load(session_key)
        lines: list[str] = []
        if hm.goals:
            lines.append("Goal: " + "; ".join(hm.goals[:2]))
        # Newest facts last appended — take latest N
        facts = sorted(hm.facts, key=lambda f: f.get("ts", ""))[-max_facts:]
        for f in facts:
            lines.append(f"{f.get('k')}: {f.get('v')}")
        if hm.constraints:
            lines.append("Constraints: " + "; ".join(hm.constraints[:2]))
        if hm.todos:
            lines.append("Next: " + "; ".join(hm.todos[:2]))
        return lines
