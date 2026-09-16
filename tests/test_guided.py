from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from character.guided import advance, is_active, start_cc  # noqa: E402
from character.store import CharacterStore  # noqa: E402


def test_full_happy_path(tmp_path):
    store = CharacterStore(tmp_path)
    s = start_cc()
    assert is_active(s)
    s = advance(s, "侦探", store, "u1")
    assert s.step == 2
    s = advance(s, "记者 3d6", store, "u1")
    assert s.step == 3
    assert s.job == "记者"
    assert s.method == "3d6x5"
    s = advance(s, "r", store, "u1")
    assert s.step == 3
    s = advance(s, "ok", store, "u1")
    assert s.step == 4
    assert not is_active(s)
    assert store.get("u1", "侦探") is not None
    assert store.get_current("u1") == "侦探"


def test_duplicate_name_rejected(tmp_path):
    store = CharacterStore(tmp_path)
    s = start_cc()
    s = advance(s, "已有", store, "u1")
    from character.creator import quick_create

    store.save(quick_create("已有", "u1", rng=random.Random(1)))
    s = start_cc()
    s = advance(s, "已有", store, "u1")
    assert s.step == 1
    assert "已有" in s.message
