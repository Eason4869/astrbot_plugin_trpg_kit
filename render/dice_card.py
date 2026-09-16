"""HTML renderer for realistic-looking dice result cards."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Template

TEMPLATE_PATH = Path(__file__).parent / "templates" / "dice.html"


def _die_class(sides: int) -> str:
    if sides >= 100 or sides == 10:
        return "d10"
    if sides >= 20:
        return "d20"
    if sides >= 12:
        return "d12"
    if sides >= 8:
        return "d8"
    if sides >= 6:
        return "d6"
    return "d4"


def render_dice_html(payload: dict[str, Any]) -> str:
    """Render dice payload to full HTML string for html_render."""
    if not TEMPLATE_PATH.exists():
        # Fallback minimal HTML if template missing
        dice = payload.get("dice") or []
        chips = "".join(
            f'<span class="die {_die_class(int(d.get("sides", 6)))}{" chosen" if d.get("chosen") else ""}">{d.get("display","?")}</span>'
            for d in dice
        )
        return (
            f"<div style='font-family:sans-serif;padding:24px;background:#1a1a2e;color:#eee;"
            f"border-radius:16px;display:inline-block'><h3>{payload.get('title','')}</h3>"
            f"<div style='display:flex;gap:12px;margin:12px 0'>{chips}</div>"
            f"<div style='font-size:28px;font-weight:700'>总计 {payload.get('total')}</div></div>"
        )
    tmpl = Template(TEMPLATE_PATH.read_text(encoding="utf-8"))
    dice = []
    for d in payload.get("dice") or []:
        item = dict(d)
        item["cls"] = _die_class(int(item.get("sides", 6)))
        dice.append(item)
    return tmpl.render(
        title=payload.get("title", "掷骰"),
        subtitle=payload.get("subtitle", ""),
        dice=dice,
        total=payload.get("total"),
        text=payload.get("text", ""),
        bonus=payload.get("bonus", 0),
        penalty=payload.get("penalty", 0),
    )
