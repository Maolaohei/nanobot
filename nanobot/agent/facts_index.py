from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from nanobot.utils.helpers import ensure_dir

_SENSITIVE_KEYS = {
    "password",
    "token",
    "api_key",
    "apikey",
    "secret",
}


@dataclass
class Fact:
    k: str
    v: str
    tags: list[str]

    def to_json(self) -> str:
        return json.dumps({"k": self.k, "v": self.v, "tags": self.tags}, ensure_ascii=False)


_LINE_KV = re.compile(r"^[\s\-*+\d\.]*([A-Za-z0-9_\-一-龥/\.]+)\s*[:：]\s*(.+)$")
_CODE_FENCE = re.compile(r"^\s*```")


def _iter_kv_from_markdown(md: str) -> Iterable[Fact]:
    in_code = False
    for raw in md.splitlines():
        line = raw.rstrip()
        if _CODE_FENCE.match(line):
            in_code = not in_code
            continue
        if in_code or not line:
            continue
        m = _LINE_KV.match(line)
        if not m:
            continue
        k, v = m.group(1).strip(), m.group(2).strip()
        if k.lower() in _SENSITIVE_KEYS:
            continue
        tags: list[str] = []
        # lightweight tagging
        lk = k.lower()
        if any(t in lk for t in ("preference", "偏好")):
            tags.append("preference")
        if any(t in lk for t in ("project", "仓库", "repo")):
            tags.append("project")
        yield Fact(k=k, v=v, tags=tags)


def build_index(memory_md: str) -> list[Fact]:
    return list(_iter_kv_from_markdown(memory_md))


def save_index(workspace: Path, facts: list[Fact]) -> Path:
    out_dir = ensure_dir(workspace / "memory" / "index")
    out = out_dir / "facts.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for fact in facts:
            f.write(fact.to_json() + "\n")
    return out


def load_index(workspace: Path) -> list[Fact]:
    path = workspace / "memory" / "index" / "facts.jsonl"
    if not path.exists():
        return []
    facts: list[Fact] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            obj = json.loads(line)
            facts.append(Fact(k=str(obj.get("k", "")), v=str(obj.get("v", "")), tags=list(obj.get("tags", []))))
        except Exception:
            continue
    return facts


def select_relevant_facts(message: str, facts: list[Fact], limit: int = 5) -> list[Fact]:
    if not facts:
        return []
    msg = (message or "").strip()
    if not msg:
        # default: prefer preference/project tags, keep first N
        tagged = [f for f in facts if ("preference" in f.tags or "project" in f.tags)]
        base = tagged or facts
        return base[:limit]

    # simple scoring: substring matches of >=2 chars from message
    tokens: list[str] = []
    # split on spaces/punct, keep chinese chunks as-is
    cur = []
    for ch in msg:
        if ch.isalnum() or ("\u4e00" <= ch <= "\u9fff"):
            cur.append(ch)
        else:
            if len(cur) >= 2:
                tokens.append("".join(cur))
            cur = []
    if len(cur) >= 2:
        tokens.append("".join(cur))

    def score(f: Fact) -> int:
        s = 0
        base = (f.k + " " + f.v)
        for t in tokens:
            if t and t in base:
                s += 2 if len(t) > 3 else 1
        if "preference" in f.tags:
            s += 1
        if "project" in f.tags:
            s += 1
        return s

    ranked = sorted(facts, key=score, reverse=True)
    head = [f for f in ranked if score(f) > 0][:limit]
    return head or ranked[:limit]
