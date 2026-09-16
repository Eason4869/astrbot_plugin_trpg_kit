from __future__ import annotations

from pathlib import Path

from jinja2 import Template

from character.models import ATTR_KEYS, CharacterCard

TEMPLATE_PATH = Path(__file__).parent / "templates" / "character.html"


def render_character_html(card: CharacterCard, san_now: int | None = None) -> str:
    tmpl = Template(TEMPLATE_PATH.read_text(encoding="utf-8"))
    san = san_now if san_now is not None else int(card.derived.get("SAN", card.attrs.get("POW", 0)))
    return tmpl.render(card=card, attrs=list(ATTR_KEYS), san_now=san)
