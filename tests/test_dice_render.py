from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dice.engine import D100Roll, ExprResult, format_d100, parse_and_roll  # noqa: E402
from render.dice_card import render_dice_html  # noqa: E402


def test_render_dice_html_contains_total():
    res = parse_and_roll("1d100", rng=random.Random(1))
    d100 = res.d100
    assert d100 is not None
    html = render_dice_html(
        {
            "title": "掷骰 1d100",
            "dice": [
                {
                    "sides": 10,
                    "value": d100.chosen_tens,
                    "display": str(d100.chosen_tens),
                    "label": "十位",
                    "chosen": True,
                    "tag": "",
                },
                {
                    "sides": 10,
                    "value": d100.ones,
                    "display": str(d100.ones),
                    "label": "个位",
                    "chosen": True,
                    "tag": "",
                },
            ],
            "total": d100.value,
            "text": format_d100(d100),
            "bonus": 0,
            "penalty": 0,
        }
    )
    assert str(d100.value) in html
    assert "RESULT" in html
    assert "die" in html


def test_d6_render():
    res = parse_and_roll("2d6", rng=random.Random(2))
    dice = []
    for term in res.terms:
        for v in term.rolls:
            dice.append(
                {
                    "sides": term.sides,
                    "value": v,
                    "display": str(v),
                    "label": "2d6",
                    "chosen": True,
                    "tag": "",
                }
            )
    html = render_dice_html(
        {"title": "掷骰 2d6", "dice": dice, "total": res.total, "text": res.text}
    )
    assert "d6" in html
    assert str(res.total) in html
