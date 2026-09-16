"""CoC 7 success levels and SAN check rules."""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

from dice.engine import D100Roll, roll_d100


class Level(str, Enum):
    CRITICAL = "大成功"
    HARD = "困难成功"
    REGULAR = "成功"
    FAILURE = "失败"
    FUMBLE = "大失败"


@dataclass
class CheckResult:
    roll: int
    skill: int
    level: Level


def coc7_level(roll: int, skill: int) -> Level:
    """Classify roll against skill (CoC7 CN community table).

    - Fumble: 100 always, or 96-100 when skill < 50
    - Critical: <= skill//5 (at least 1)
    - Hard: <= skill//2
    - Regular: <= skill
    - else Failure
    """
    skill = max(0, min(int(skill), 999))
    if roll == 100 or (skill < 50 and roll >= 96):
        return Level.FUMBLE
    crit = max(1, skill // 5)
    half = max(1, skill // 2)
    if roll <= crit:
        return Level.CRITICAL
    if roll <= half:
        return Level.HARD
    if roll <= skill:
        return Level.REGULAR
    return Level.FAILURE


def check_vs_skill(d100: D100Roll, skill: int, difficulty: str = "n") -> CheckResult:
    """Evaluate with optional difficulty gate: n|h|e|c (e treated as hard band)."""
    roll = d100.value
    skill = max(0, min(int(skill), 999))
    level = coc7_level(roll, skill)
    difficulty = (difficulty or "n").strip().lower()
    need = {
        "n": Level.REGULAR,
        "": Level.REGULAR,
        "normal": Level.REGULAR,
        "h": Level.HARD,
        "hard": Level.HARD,
        "困难": Level.HARD,
        "e": Level.HARD,
        "extreme": Level.HARD,
        "极难": Level.HARD,
        "c": Level.CRITICAL,
        "crit": Level.CRITICAL,
        "大成功": Level.CRITICAL,
    }.get(difficulty, Level.REGULAR)
    if level == Level.FUMBLE:
        return CheckResult(roll=roll, skill=skill, level=Level.FUMBLE)
    rank = {
        Level.FAILURE: 0,
        Level.REGULAR: 1,
        Level.HARD: 2,
        Level.CRITICAL: 3,
    }
    if rank[level] < rank[need]:
        return CheckResult(roll=roll, skill=skill, level=Level.FAILURE)
    return CheckResult(roll=roll, skill=skill, level=level)


@dataclass
class SanResult:
    roll: int
    san: int
    success: bool
    loss: int
    new_san: int


def san_check(
    san: int,
    rng: random.Random | None = None,
    success_loss_cap: int | None = None,
    extra_d100: D100Roll | None = None,
) -> SanResult:
    """CoC7 SAN: roll <= san → lose 1d4; else lose 1d6+1."""
    r = rng or random.Random()
    san = max(0, min(int(san), 99))
    d = extra_d100 or roll_d100(r)
    roll = d.value
    success = roll <= san
    if success:
        loss = r.randint(1, 4)
        if success_loss_cap is not None:
            loss = min(loss, max(0, int(success_loss_cap)))
    else:
        loss = r.randint(1, 6) + 1
    new_san = max(0, san - loss)
    return SanResult(roll=roll, san=san, success=success, loss=loss, new_san=new_san)
