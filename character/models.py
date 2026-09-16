"""Character data model and derived values (CoC7)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


ATTR_KEYS = ("STR", "CON", "POW", "DEX", "APP", "SIZ", "INT", "EDU")


@dataclass
class CharacterCard:
    name: str
    owner_user_id: str = ""
    attrs: dict[str, int] = field(default_factory=dict)
    derived: dict[str, Any] = field(default_factory=dict)
    skills: dict[str, int] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)
    updated_at: str = ""

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CharacterCard":
        return cls(
            name=str(data.get("name", "")),
            owner_user_id=str(data.get("owner_user_id", "")),
            attrs={str(k): int(v) for k, v in dict(data.get("attrs") or {}).items()},
            derived=dict(data.get("derived") or {}),
            skills={str(k): int(v) for k, v in dict(data.get("skills") or {}).items()},
            meta=dict(data.get("meta") or {}),
            updated_at=str(data.get("updated_at", "")),
        )


def compute_derived(attrs: dict[str, int]) -> dict[str, Any]:
    """CoC7 derived values from attributes."""
    a = {k: int(attrs.get(k, 0)) for k in ATTR_KEYS}
    hp = a["CON"] // 10 + a["SIZ"] // 10
    mp = a["POW"] // 10
    san = a["POW"]
    # MOV: compare STR/DEX/CON to 50
    above = sum(1 for k in ("STR", "DEX", "CON") if a[k] > 50)
    below = sum(1 for k in ("STR", "DEX", "CON") if a[k] < 50)
    mov = 7
    if above >= 2:
        mov = 8
    if below >= 2:
        mov = 6
    # DB / build from STR+SIZ
    ss = a["STR"] + a["SIZ"]
    if ss <= 64:
        db, build = "-2", -2
    elif ss <= 84:
        db, build = "-1", -1
    elif ss <= 124:
        db, build = "0", 0
    elif ss <= 164:
        db, build = "+1d4", 1
    elif ss <= 204:
        db, build = "+1d6", 2
    else:
        db, build = "+2d6", 3
    luck = a["POW"]  # initial luck often rolled separately; default POW-like placeholder
    return {
        "HP": hp,
        "MP": mp,
        "SAN": san,
        "MOV": mov,
        "DB": db,
        "build": build,
        "luck": luck,
    }


def apply_attrs(card: CharacterCard, attrs: dict[str, int], recompute: bool = True) -> None:
    for k in ATTR_KEYS:
        if k in attrs:
            card.attrs[k] = int(attrs[k])
    if recompute:
        card.derived = compute_derived(card.attrs)
        if "SAN" not in card.derived:
            card.derived["SAN"] = card.attrs.get("POW", 0)
