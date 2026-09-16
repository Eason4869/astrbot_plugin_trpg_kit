"""Quick character generation."""

from __future__ import annotations

import random

from character.models import ATTR_KEYS, CharacterCard, apply_attrs

DEFAULT_SKILLS = {
    "侦查": 20,
    "聆听": 20,
    "话术": 5,
    "攀爬": 20,
    "图书馆": 20,
    "心理学": 10,
    "急救": 30,
    "斗殴": 25,
    "射击": 20,
    "闪避": 20,
}


def roll_attr_3d6x5(rng: random.Random | None = None) -> int:
    r = rng or random.Random()
    return sum(r.randint(1, 6) for _ in range(3)) * 5


def roll_attr_2d6_6_30(rng: random.Random | None = None) -> int:
    r = rng or random.Random()
    return r.randint(1, 6) + r.randint(1, 6) + 6 + 30


def roll_attrs(method: str = "3d6x5", rng: random.Random | None = None) -> dict[str, int]:
    r = rng or random.Random()
    out = {}
    for k in ATTR_KEYS:
        if method == "2d6+6+30":
            out[k] = roll_attr_2d6_6_30(r)
        else:
            out[k] = roll_attr_3d6x5(r)
    return out


def quick_create(
    name: str,
    owner: str,
    job: str = "",
    method: str = "3d6x5",
    rng: random.Random | None = None,
) -> CharacterCard:
    r = rng or random.Random()
    attrs = roll_attrs(method, r)
    card = CharacterCard(name=name, owner_user_id=owner)
    apply_attrs(card, attrs)
    ed = attrs.get("EDU", 0)
    card.skills = {
        k: max(v, min(90, v + max(0, (ed - 50) // 10)))
        for k, v in DEFAULT_SKILLS.items()
    }
    # EDU*2 credit points left as note; MVP does not allocate full occupation
    card.meta = {
        "job": job or "调查员",
        "age": 20 + r.randint(0, 30),
        "sex": "",
        "notes": f"快速车卡; 属性法={method}; 职业点≈{ed * 2}(未完整分配)",
    }
    return card
