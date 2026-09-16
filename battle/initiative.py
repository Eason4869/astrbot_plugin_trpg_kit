"""Battle initiative helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class InitEntry:
    name: str
    score: int
    order: int


def sort_initiative(entries: list[tuple[str, int]]) -> list[InitEntry]:
    """Sort by score desc, stable by input order asc on ties."""
    result = [
        InitEntry(name=n, score=int(s), order=i) for i, (n, s) in enumerate(entries)
    ]
    result.sort(key=lambda e: (-e.score, e.order))
    return result


def format_initiative(entries: list[InitEntry]) -> str:
    if not entries:
        return "战斗轮为空。用法：/init 张三 1d100 李四 80"
    lines = ["战斗轮（高→低）："]
    for i, e in enumerate(entries, 1):
        lines.append(f"{i}. {e.name} — {e.score}")
    return "\n".join(lines)
