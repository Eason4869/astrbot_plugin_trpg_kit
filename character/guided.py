"""Guided character creation session state machine (pure, testable)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from character.creator import quick_create
from character.models import ATTR_KEYS, CharacterCard, apply_attrs
from character.store import CharacterStore


@dataclass
class CcSession:
    step: int = 1  # 1=name, 2=job+method, 3=confirm, 4=done
    name: str = ""
    job: str = ""
    method: str = "3d6x5"
    attrs: dict[str, int] = field(default_factory=dict)
    message: str = ""


def start_cc() -> CcSession:
    return CcSession(step=1, message="【引导车卡 1/3】请回复角色名。\n（/cc cancel 取消）")


def advance(session: CcSession, text: str, store: CharacterStore, owner: str) -> CcSession:
    """Advance one step with user text. Returns updated session (may be done)."""
    text = (text or "").strip()
    if not text:
        session.message = "内容为空，请重试。"
        return session
    if session.step == 1:
        if len(text) > 24:
            session.message = "角色名过长（≤24）。"
            return session
        if store.get(owner, text):
            session.message = f"已有角色「{text}」，换一个名。"
            return session
        session.name = text
        session.step = 2
        session.message = (
            "【引导车卡 2/3】请回复职业，或留空用「调查员」。\n"
            "属性生成：回复 `3d6` 或 `2d6`"
        )
        return session
    if session.step == 2:
        # parse "职业 3d6" or "3d6" or "记者" or "记者 2d6"
        method = session.method
        job = text
        for tok in text.split():
            tl = tok.lower()
            if tl in ("3d6", "3d6x5"):
                method = "3d6x5"
                job = job.replace(tok, "").strip()
            elif tl in ("2d6", "2d6+6+30"):
                method = "2d6+6+30"
                job = job.replace(tok, "").strip()
        session.job = job or "调查员"
        session.method = method
        draft = quick_create(session.name, owner, job=session.job, method=method)
        session.attrs = dict(draft.attrs)
        session.step = 3
        attrs_line = " ".join(f"{k}{session.attrs.get(k,0)}" for k in ATTR_KEYS)
        session.message = (
            f"【引导车卡 3/3】预览 {session.name}（{session.job}）\n"
            f"{attrs_line}\n"
            f"回复 `ok` 保存，或回复 `r` 重随。"
        )
        return session
    if session.step == 3:
        low = text.lower()
        if low in ("r", "re", "重随", "重roll"):
            draft = quick_create(session.name, owner, job=session.job, method=session.method)
            session.attrs = dict(draft.attrs)
            attrs_line = " ".join(f"{k}{session.attrs.get(k,0)}" for k in ATTR_KEYS)
            session.message = f"已重随：{attrs_line}\n回复 `ok` 保存，或 `r` 重随。"
            return session
        if low in ("ok", "y", "yes", "保存", "确定"):
            card = quick_create(session.name, owner, job=session.job, method=session.method)
            card.attrs = dict(session.attrs)
            apply_attrs(card, session.attrs, recompute=True)
            card.meta["job"] = session.job
            store.save(card)
            store.set_current(owner, card.name)
            session.step = 4
            session.message = f"已保存并设为当前角色：{card.name}。查看 /pc"
            return session
        session.message = "请回复 `ok` 保存或 `r` 重随。"
        return session
    session.message = "车卡已结束。/cc 可重新开始。"
    return session


def is_active(session: CcSession | None) -> bool:
    return session is not None and session.step in (1, 2, 3)
