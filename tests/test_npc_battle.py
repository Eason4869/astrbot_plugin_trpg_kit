from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from battle.initiative import format_initiative, sort_initiative  # noqa: E402
from npc.store import NpcStore  # noqa: E402
from character.creator import quick_create  # noqa: E402
import random  # noqa: E402


def test_initiative_sort_ties_by_order():
    entries = sort_initiative([("a", 50), ("b", 80), ("c", 80)])
    assert [e.name for e in entries] == ["b", "c", "a"]
    assert "战斗轮" in format_initiative(entries)


def test_npc_store(tmp_path):
    store = NpcStore(tmp_path)
    npc = quick_create("深潜者", "npc", rng=random.Random(1))
    npc.name = "深潜者"
    store.save(npc)
    assert "深潜者" in store.list_names()
    assert store.get("深潜者") is not None
    assert store.delete("深潜者")
    assert store.get("深潜者") is None
