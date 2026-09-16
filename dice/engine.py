"""Dice expression parsing and d100 (2d10) engine with bonus/penalty dice."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field


class DiceError(ValueError):
    """Invalid dice expression."""


_TERM_RE = re.compile(r"^(?P<n>\d*)d(?P<sides>\d+)$", re.I)
_NUM_RE = re.compile(r"^\d+$")
_EXPR_SPLIT = re.compile(r"([+-])")


@dataclass
class D100Roll:
    tens_pool: list[int]
    ones: int
    bonus: int = 0
    penalty: int = 0
    chosen_tens: int = 0
    marked: list[str] = field(default_factory=list)

    @property
    def value(self) -> int:
        """00+0 → 100; ones digit 0 with nonzero tens → tens*10."""
        if self.chosen_tens == 0 and self.ones == 0:
            return 100
        return self.chosen_tens * 10 + self.ones


def roll_d100(
    rng: random.Random | None = None, bonus: int = 0, penalty: int = 0
) -> D100Roll:
    """Roll d100 as two d10; extra tens from bonus (keep min) / penalty (keep max)."""
    if bonus < 0 or penalty < 0:
        raise DiceError("bonus/penalty must be >= 0")
    r = rng or random.Random()
    n_tens = 1 + bonus + penalty
    tens_pool = [r.randint(0, 9) for _ in range(n_tens)]
    ones = r.randint(0, 9)
    marked: list[str] = [""]
    for i in range(bonus):
        marked.append("b")
    for i in range(penalty):
        marked.append("p")
    chosen = tens_pool[0]
    for i in range(1, 1 + bonus):
        chosen = min(chosen, tens_pool[i])
    for i in range(1 + bonus, n_tens):
        chosen = max(chosen, tens_pool[i])
    return D100Roll(
        tens_pool=tens_pool,
        ones=ones,
        bonus=bonus,
        penalty=penalty,
        chosen_tens=chosen,
        marked=marked,
    )


def format_d100(roll: D100Roll) -> str:
    parts = []
    for i, t in enumerate(roll.tens_pool):
        tag = roll.marked[i] if i < len(roll.marked) and roll.marked[i] else ""
        star = "*" if t == roll.chosen_tens else ""
        parts.append(f"{t}{tag}{star}")
    return f"[{' '.join(parts)}|{roll.ones}] → {roll.value}"


@dataclass
class TermResult:
    n: int
    sides: int
    rolls: list[int]


@dataclass
class ExprResult:
    terms: list[TermResult] = field(default_factory=list)
    total: int = 0
    is_d100: bool = False
    d100: D100Roll | None = None
    text: str = ""


def _roll_term(n: int, sides: int, rng: random.Random) -> TermResult:
    if n < 1 or n > 100:
        raise DiceError("dice count must be 1-100")
    if sides < 2 or sides > 1000:
        raise DiceError("sides must be 2-1000")
    return TermResult(n=n, sides=sides, rolls=[rng.randint(1, sides) for _ in range(n)])


def parse_and_roll(
    expr: str,
    bonus: int = 0,
    penalty: int = 0,
    rng: random.Random | None = None,
) -> ExprResult:
    """Parse NdM(+/-NdM|+/-K)* and roll. d100 uses 2d10 engine."""
    r = rng or random.Random()
    expr = (expr or "").strip().replace(" ", "").lower()
    if not expr:
        expr = "1d100"

    if expr in ("d100", "1d100", "d%", "1d%"):
        d100 = roll_d100(r, bonus=bonus, penalty=penalty)
        return ExprResult(
            terms=[TermResult(n=1, sides=100, rolls=[d100.value])],
            total=d100.value,
            is_d100=True,
            d100=d100,
            text=format_d100(d100),
        )

    raw = expr
    if raw[0] not in "+-":
        raw = "+" + raw
    parts = _EXPR_SPLIT.split(raw)
    sign = 1
    terms: list[TermResult] = []
    total = 0
    chunks: list[str] = []
    for p in parts:
        if p == "+":
            sign = 1
            continue
        if p == "-":
            sign = -1
            continue
        if not p:
            continue
        m = _TERM_RE.match(p)
        if m:
            n = int(m.group("n")) if m.group("n") else 1
            sides = int(m.group("sides"))
            if sides == 100:
                if n != 1:
                    raise DiceError("only 1d100 supported for d100")
                if sign < 0:
                    raise DiceError("negative d100 not supported")
                d100 = roll_d100(r, bonus=bonus, penalty=penalty)
                total += d100.value
                terms.append(TermResult(n=1, sides=100, rolls=[d100.value]))
                chunks.append(format_d100(d100))
                continue
            tr = _roll_term(n, sides, r)
            terms.append(tr)
            s = sum(tr.rolls)
            total += sign * s
            if n > 1:
                body = "+".join(str(x) for x in tr.rolls)
                chunks.append(f"{'-' if sign < 0 else '+'}{n}d{sides}({body}={s})")
            else:
                chunks.append(f"{'-' if sign < 0 else '+'}{n}d{sides}({tr.rolls[0]})")
            continue
        if _NUM_RE.match(p):
            num = int(p)
            total += sign * num
            chunks.append(("+" if sign >= 0 else "-") + str(num))
            continue
        raise DiceError(f"invalid term: {p}")
    return ExprResult(
        terms=terms, total=total, is_d100=False, d100=None, text=" ".join(chunks) + f" = {total}"
    )


def parse_bonus_penalty_suffix(args: list[str]) -> tuple[list[str], int, int]:
    """Split trailing b/p tokens. Returns (rest, bonus, penalty)."""
    bonus = 0
    penalty = 0
    rest: list[str] = []
    for a in args:
        al = a.lower()
        if al == "b":
            bonus += 1
        elif al == "p":
            penalty += 1
        elif al == "bb":
            bonus += 2
        elif al == "pp":
            penalty += 2
        else:
            rest.append(a)
    return rest, bonus, penalty
