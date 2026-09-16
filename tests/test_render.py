from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from character.creator import quick_create  # noqa: E402
from render.card import render_character_html  # noqa: E402


def test_render_contains_name_and_attrs(tmp_path):
    card = quick_create("张三", "u1", job="记者", rng=random.Random(1))
    html = render_character_html(card)
    assert "张三" in html
    assert "STR" in html
    assert str(card.attrs["STR"]) in html
    assert "HP" in html
