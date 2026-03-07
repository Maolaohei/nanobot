from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Counters:
    data: Dict[str, int] = field(default_factory=dict)

    def inc(self, key: str, n: int = 1) -> None:
        self.data[key] = self.data.get(key, 0) + n

    def get(self, key: str) -> int:
        return self.data.get(key, 0)


_COUNTERS = Counters()


def inc(key: str, n: int = 1) -> None:
    _COUNTERS.inc(key, n)


def snapshot() -> dict[str, int]:
    return dict(_COUNTERS.data)
