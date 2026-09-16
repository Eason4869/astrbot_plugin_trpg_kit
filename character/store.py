"""JSON multi-character store with current-character pointer."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from character.models import CharacterCard


class CharacterStore:
    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.chars_path = self.data_dir / "characters.json"
        self.current_path = self.data_dir / "current.json"

    def _load_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("root must be object")
            return data
        except (json.JSONDecodeError, ValueError, OSError):
            bak = path.with_suffix(path.suffix + ".bak")
            try:
                shutil.copy2(path, bak)
            except OSError:
                pass
            return {}

    def _save_json(self, path: Path, data: dict[str, Any]) -> None:
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

    def list_names(self, owner: str) -> list[str]:
        data = self._load_json(self.chars_path)
        owner_map = data.get(owner) or {}
        return sorted(owner_map.keys())

    def get(self, owner: str, name: str) -> CharacterCard | None:
        data = self._load_json(self.chars_path)
        raw = (data.get(owner) or {}).get(name)
        if not raw:
            return None
        return CharacterCard.from_dict(raw)

    def save(self, card: CharacterCard) -> None:
        if not card.owner_user_id:
            raise ValueError("owner_user_id required")
        if not card.name:
            raise ValueError("name required")
        card.touch()
        data = self._load_json(self.chars_path)
        data.setdefault(card.owner_user_id, {})[card.name] = card.to_dict()
        self._save_json(self.chars_path, data)

    def delete(self, owner: str, name: str) -> bool:
        data = self._load_json(self.chars_path)
        if name not in (data.get(owner) or {}):
            return False
        del data[owner][name]
        self._save_json(self.chars_path, data)
        cur = self.get_current(owner)
        if cur == name:
            self.set_current(owner, "")
        return True

    def get_current(self, owner: str) -> str:
        data = self._load_json(self.current_path)
        return str(data.get(owner) or "")

    def set_current(self, owner: str, name: str) -> None:
        data = self._load_json(self.current_path)
        data[owner] = name
        self._save_json(self.current_path, data)

    def resolve(self, owner: str, name: str | None = None) -> CharacterCard | None:
        target = name or self.get_current(owner)
        if not target:
            return None
        return self.get(owner, target)
