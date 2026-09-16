from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dice.engine import (  # noqa: E402
    DiceError,
    format_d100,
    parse_and_roll,
    parse_bonus_penalty_suffix,
    roll_d100,
)


def test_d100_zero_zero_is_100():
    r = random.Random(0)

    class Fixed(random.Random):
        def randint(self, a, b):
            return 0

    d = roll_d100(Fixed(), bonus=0, penalty=0)
    assert d.value == 100


def test_d100_basic_value():
    # force tens=3 ones=7
    seq = iter([3, 7])

    class Fixed(random.Random):
        def randint(self, a, b):
            return next(seq)

    d = roll_d100(Fixed())
    assert d.value == 37


def test_bonus_takes_min_tens():
    # tens: main=8, bonus=1, bonus=2 → chosen=1; ones=5 → 15
    seq = iter([8, 1, 2, 5])

    class Fixed(random.Random):
        def randint(self, a, b):
            return next(seq)

    d = roll_d100(Fixed(), bonus=2)
    assert d.chosen_tens == 1
    assert d.value == 15


def test_penalty_takes_max_tens():
    seq = iter([1, 9, 5])

    class Fixed(random.Random):
        def randint(self, a, b):
            return next(seq)

    d = roll_d100(Fixed(), penalty=1)
    assert d.chosen_tens == 9
    assert d.value == 90 + 5


def test_parse_1d100():
    res = parse_and_roll("1d100", rng=random.Random(1))
    assert res.is_d100
    assert 1 <= res.total <= 100


def test_parse_2d6_plus():
    res = parse_and_roll("2d6+3", rng=random.Random(1))
    assert res.total == sum(res.terms[0].rolls) + 3


def test_parse_bonus_suffix():
    rest, b, p = parse_bonus_penalty_suffix(["1d100", "bb", "p"])
    assert rest == ["1d100"]
    assert b == 2
    assert p == 1


def test_invalid_expr():
    try:
        parse_and_roll("foo", rng=random.Random(0))
        assert False
    except DiceError:
        pass


def test_format_d100_contains_arrow():
    seq = iter([1, 2])

    class Fixed(random.Random):
        def randint(self, a, b):
            return next(seq)

    text = format_d100(roll_d100(Fixed()))
    assert "→" in text
