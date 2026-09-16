from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from character.creator import quick_create, roll_attrs  # noqa: E402
from character.models import ATTR_KEYS, CharacterCard, compute_derived  # noqa: E402
from character.store import CharacterStore  # noqa: E402


def test_derived_values():
    attrs = {k: 50 for k in ATTR_KEYS}
    d = compute_derived(attrs)
    assert d["HP"] == 10
    assert d["MP"] == 5
    assert d["SAN"] == 50
    assert d["MOV"] == 7
    assert d["DB"] == "0"


def test_attrs_methods():
    a = roll_attrs("3d6x5", random.Random(1))
    for k, v in a.items():
        assert 15 <= v <= 90
        assert v % 5 == 0
    b = roll_attrs("2d6+6+30", random.Random(1))
    for v in b.values():
        assert 32 <= v <= 54


def test_store_multi_char(tmp_path):
    store = CharacterStore(tmp_path)
    c1 = quick_create("张三", "u1", rng=random.Random(1))
    c2 = quick_create("李四", "u1", rng=random.Random(2))
    store.save(c1)
    store.save(c2)
    store.set_current("u1", "李四")
    assert store.list_names("u1") == ["李四", "张三"] or set(store.list_names("u1")) == {"张三", "李四"}
    assert store.resolve("u1").name == "李四"
    assert store.resolve("u1", "张三").name == "张三"
    assert store.delete("u1", "张三")
    assert store.get("u1", "张三") is None
    # current cleared when deleting current
    store.set_current("u1", "李四")
    assert store.delete("u1", "李四")
    assert store.get_current("u1") == ""


def test_corrupt_json_recovers(tmp_path):
    store = CharacterStore(tmp_path)
    store.chars_path.write_text("{not json", encoding="utf-8")
    c = quick_create("A", "u1", rng=random.Random(3))
    store.save(c)
    assert store.get("u1", "A") is not None
