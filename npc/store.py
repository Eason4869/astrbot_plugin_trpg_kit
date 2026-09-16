"""Global NPC template store."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from character.models import CharacterCard


class NpcStore:
    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "npcs.json"

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            try:
                shutil.copy2(self.path, self.path.with_suffix(".json.bak"))
            except OSError:
                pass
            return {}

    def _save(self, data: dict[str, Any]) -> None:
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def list_names(self) -> list[str]:
        return sorted(self._load().keys())

    def get(self, name: str) -> CharacterCard | None:
        raw = self._load().get(name)
        if not raw:
            return None
        return CharacterCard.from_dict(raw)

    def save(self, card: CharacterCard) -> None:
        data = self._load()
        card.touch()
        data[card.name] = card.to_dict()
        self._save(data)

    def delete(self, name: str) -> bool:
        data = self._load()
        if name not in data:
            return False
        del data[name]
        self._save(data)
        return True
