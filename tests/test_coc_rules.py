from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dice.coc_rules import Level, check_vs_skill, coc7_level, san_check  # noqa: E402
from dice.engine import D100Roll  # noqa: E402


def test_critical_at_fifth():
    assert coc7_level(10, 50) == Level.CRITICAL  # 50//5=10


def test_hard_at_half():
    assert coc7_level(25, 50) == Level.HARD
    assert coc7_level(12, 50) == Level.HARD  # 12>crit(10) and <=half(25)
    assert coc7_level(8, 50) == Level.CRITICAL


def test_regular_success():
    assert coc7_level(40, 50) == Level.REGULAR


def test_failure():
    assert coc7_level(80, 50) == Level.FAILURE


def test_fumble_100():
    assert coc7_level(100, 50) == Level.FUMBLE
    assert coc7_level(100, 99) == Level.FUMBLE


def test_fumble_96_when_skill_low():
    assert coc7_level(96, 40) == Level.FUMBLE
    assert coc7_level(96, 60) != Level.FUMBLE  # skill>=50, only 100 fumbles


def test_difficulty_gate():
    d = D100Roll(tens_pool=[2], ones=0, chosen_tens=2, marked=[""])  # 20
    r = check_vs_skill(d, 50, difficulty="h")
    assert r.level in (Level.HARD, Level.CRITICAL)
    r2 = check_vs_skill(d, 50, difficulty="c")
    assert r2.level == Level.FAILURE  # not critical


def test_san_success_loss_bounds():
    class Fixed(random.Random):
        def __init__(self):
            super().__init__(0)
            self._n = 0

        def randint(self, a, b):
            self._n += 1
            if self._n == 1:  # tens
                return 0
            if self._n == 2:  # ones
                return 5  # roll = 5
            return a  # loss min

    res = san_check(99, rng=Fixed())
    assert res.success
    assert res.roll == 5
    assert 1 <= res.loss <= 4
    assert res.new_san == max(0, 99 - res.loss)


def test_san_failure_loss():
    class Fixed(random.Random):
        def randint(self, a, b):
            return b  # max

    res = san_check(10, rng=Fixed(0))
    assert not res.success
    assert res.loss == 7
    assert res.new_san == 3
