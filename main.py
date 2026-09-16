from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Any

# AstrBot loads the plugin without putting the plugin root on sys.path.
_plugin_root = str(Path(__file__).resolve().parent)
if _plugin_root not in sys.path:
    sys.path.insert(0, _plugin_root)

from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star

from battle.initiative import format_initiative, sort_initiative
from character.creator import quick_create
from character.guided import is_active, start_cc
from character.models import ATTR_KEYS, CharacterCard, apply_attrs
from character.store import CharacterStore
from dice.coc_rules import check_vs_skill, san_check
from dice.engine import DiceError, format_d100, parse_and_roll, parse_bonus_penalty_suffix, roll_d100
from npc.store import NpcStore

HELP_TEXT = """CoC TRPG KP 工具
/r [表达式] [b|p]… — 掷骰（默认 1d100，两 d10）
/ra 技能 [难度 n/h/e/c] [b|p] — 技能检定
/sc [SAN] [成功损失上限] — SAN 检定
/set 字段=值 … — 设置属性/技能
/cq [职业] — 快速车卡
/cc — 引导车卡 | /cc cancel 取消
/pc — 角色图片卡 | /pcs 列表 | /use 名 | /del 名[!]
/init [名 分数 …|clear] — 战斗轮
/npcc 名 | /npcs | /npr 名 | /npcd 名 — NPC
/help — 本帮助"""


def _plugin_data_dir(context: Context) -> Path:
    # Prefer AstrBot plugin data path when available
    try:
        base = getattr(context, "data_dir", None)
        if base:
            p = Path(str(base)) / "trpg_kit"
            p.mkdir(parents=True, exist_ok=True)
            return p
    except Exception:
        pass
    try:
        import astrbot

        root = Path(astrbot.__file__).resolve().parent.parent / "data" / "plugins" / "trpg_kit_data"
        root.mkdir(parents=True, exist_ok=True)
        return root
    except Exception:
        p = Path.cwd() / "data" / "trpg_kit"
        p.mkdir(parents=True, exist_ok=True)
        return p


class TrpgKit(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.data_dir = _plugin_data_dir(context)
        self.characters = CharacterStore(self.data_dir)
        self.npcs = NpcStore(self.data_dir)
        self.battle_path = self.data_dir / "battle.json"
        self._cc_sessions: dict[str, Any] = {}
        self._attr_method = "3d6x5"
        self._rng = random.Random()

    # --- helpers ---

    def _uid(self, event: AstrMessageEvent) -> str:
        try:
            return str(event.get_sender_id())
        except Exception:
            return str(event.message_obj.sender.id)

    def _resolve_card(self, event: AstrMessageEvent, name: str | None = None) -> CharacterCard | None:
        return self.characters.resolve(self._uid(event), name)

    def _text(self, event: AstrMessageEvent, msg: str):
        yield event.plain_result(msg)

    # --- dice / check ---

    @filter.command("r")
    async def cmd_r(self, event: AstrMessageEvent, *args: str):
        """掷骰：/r [NdM+..] [b|p]"""
        try:
            rest, bonus, penalty = parse_bonus_penalty_suffix(list(args))
            expr = rest[0] if rest else "1d100"
            result = parse_and_roll(expr, bonus=bonus, penalty=penalty, rng=self._rng)
            yield event.plain_result(f"掷骰 {expr}" + (f" b×{bonus} p×{penalty}" if bonus or penalty else "") + f"\n{result.text}")
        except DiceError as e:
            yield event.plain_result(f"表达式错误：{e}\n例：/r 1d100 b / /r 2d6+3")

    @filter.command("ra")
    async def cmd_ra(self, event: AstrMessageEvent, *args: str):
        """技能检定：/ra 技能值|技能名 [n|h|e|c] [b|p]"""
        try:
            rest, bonus, penalty = parse_bonus_penalty_suffix(list(args))
            if not rest:
                yield event.plain_result("用法：/ra 侦查 或 /ra 50 h b")
                return
            token = rest[0]
            difficulty = ""
            if len(rest) > 1 and rest[1].lower() in ("n", "h", "e", "c", "困难", "极难", "大成功"):
                difficulty = rest[1]
            skill = 0
            label = token
            if token.isdigit():
                skill = int(token)
            else:
                card = self._resolve_card(event)
                if not card:
                    yield event.plain_result(f"未找到角色技能「{token}」，请先 /cq 或 /set {token}=值")
                    return
                if token not in card.skills:
                    # try attr name
                    if token.upper() in ATTR_KEYS:
                        skill = int(card.attrs.get(token.upper(), 0))
                    else:
                        yield event.plain_result(f"角色没有技能「{token}」，可用 /set {token}=值 写入")
                        return
                else:
                    skill = int(card.skills[token])
            d100 = roll_d100(self._rng, bonus=bonus, penalty=penalty)
            result = check_vs_skill(d100, skill, difficulty=difficulty or "n")
            yield event.plain_result(
                f"检定[{label}]={skill} {d100 and format_d100(d100)}\n{result.level.value}"
            )
        except DiceError as e:
            yield event.plain_result(f"检定失败：{e}")

    @filter.command("sc")
    async def cmd_sc(self, event: AstrMessageEvent, *args: str):
        """SAN 检定：/sc [san] [成功损失上限]"""
        san = None
        cap = None
        if args and args[0].isdigit():
            san = int(args[0])
        if len(args) > 1 and args[1].isdigit():
            cap = int(args[1])
        card = self._resolve_card(event)
        if san is None:
            if not card:
                yield event.plain_result("无当前角色。用法：/sc 50 或先 /cq 建卡")
                return
            san = int(card.derived.get("SAN", card.attrs.get("POW", 0)))
        res = san_check(san, rng=self._rng, success_loss_cap=cap)
        msg = (
            f"SAN检定 当前{res.san} → 掷骰 {res.roll}："
            f"{'成功' if res.success else '失败'}，损失 {res.loss}，"
            f"剩余 {res.new_san}"
        )
        if card is not None:
            cur = card.derived.get("SAN")
            if cur is not None and int(cur) == res.san:
                card.derived["SAN"] = res.new_san
                self.characters.save(card)
                msg += "（已写入角色）"
        yield event.plain_result(msg)

    @filter.command("set")
    async def cmd_set(self, event: AstrMessageEvent, *args: str):
        """设置：/set STR=70 侦查=65"""
        if not args:
            yield event.plain_result("用法：/set STR=70 SAN=55 侦查=40")
            return
        card = self._resolve_card(event)
        if not card:
            card = CharacterCard(name="临时", owner_user_id=self._uid(event))
            self.characters.save(card)
            self.characters.set_current(self._uid(event), card.name)
        attrs: dict[str, int] = {}
        skills: dict[str, int] = {}
        derived_over: dict[str, int] = {}
        for a in args:
            if "=" not in a:
                yield event.plain_result(f"忽略无效项：{a}")
                continue
            k, v = a.split("=", 1)
            k = k.strip()
            if not v.strip().lstrip("-").isdigit():
                yield event.plain_result(f"值必须是整数：{a}")
                continue
            val = int(v)
            if k.upper() in ATTR_KEYS:
                attrs[k.upper()] = val
            elif k in ("SAN", "HP", "MP", "luck"):
                if k == "SAN":
                    derived_over["SAN"] = val
                else:
                    derived_over[k] = val
            else:
                skills[k] = val
        if attrs:
            apply_attrs(card, attrs, recompute=True)
        # apply manual derived after recompute so SAN/HP/MP stick
        for k, v in derived_over.items():
            card.derived[k] = v
        card.skills.update(skills)
        self.characters.save(card)
        yield event.plain_result(
            f"已更新角色「{card.name}」：属性{attrs or '无'} 派生{derived_over or '无'} 技能{skills or '无'}"
        )

    # --- character ---

    @filter.command("cq")
    async def cmd_cq(self, event: AstrMessageEvent, *args: str):
        """快速车卡：/cq [职业]"""
        name = f"P{self._uid(event)[-4:]}"
        job = args[0] if args else "调查员"
        card = quick_create(name=name, owner=self._uid(event), job=job, method=self._attr_method, rng=self._rng)
        # unique name if collision
        base = name
        i = 1
        while self.characters.get(self._uid(event), card.name):
            i += 1
            card.name = f"{base}{i}"
        self.characters.save(card)
        self.characters.set_current(self._uid(event), card.name)
        attrs_line = " ".join(f"{k}{card.attrs.get(k,0)}" for k in ATTR_KEYS)
        yield event.plain_result(
            f"快速车卡完成：{card.name}（{job}）\n{attrs_line}\n"
            f"HP={card.derived['HP']} MP={card.derived['MP']} SAN={card.derived['SAN']} MOV={card.derived['MOV']}\n"
            f"已设为当前角色。查看：/pc"
        )

    @filter.command("cc")
    async def cmd_cc(self, event: AstrMessageEvent, *args: str):
        """引导车卡入口"""
        uid = self._uid(event)
        if args and args[0].lower() == "cancel":
            self._cc_sessions.pop(uid, None)
            yield event.plain_result("已取消车卡")
            return
        from character.guided import start_cc as _start

        session = _start()
        self._cc_sessions[uid] = session
        yield event.plain_result(session.message)

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_cc_text(self, event: AstrMessageEvent):
        """引导车卡：非指令纯文本推进会话"""
        uid = self._uid(event)
        session = self._cc_sessions.get(uid)
        if not is_active(session):
            return
        text = (event.message_str or "").strip()
        if not text or text.startswith("/"):
            return
        from character.guided import advance

        try:
            session = advance(session, text, self.characters, uid)
            self._cc_sessions[uid] = session
            if session.step >= 4:
                self._cc_sessions.pop(uid, None)
            yield event.plain_result(session.message)
        except Exception:
            logger.exception("guided cc failed")
            yield event.plain_result("引导车卡出错，已结束。可 /cc 重试")

    @filter.command("pc")
    async def cmd_pc(self, event: AstrMessageEvent, *args: str):
        """当前角色卡：优先图片卡，失败降级文本"""
        name = args[0] if args else None
        card = self._resolve_card(event, name)
        if not card:
            yield event.plain_result("无角色。/cq 快速车卡 或 /pcs 查看列表")
            return
        self.characters.set_current(self._uid(event), card.name)
        san = int(card.derived.get("SAN", card.attrs.get("POW", 0)))
        try:
            from render.card import render_character_html

            html = render_character_html(card, san_now=san)
            url = await self.html_render("{{ html|safe }}", {"html": html})
            yield event.image_result(url)
            return
        except Exception as e:
            logger.warning(f"html_render failed, fallback text: {e}")
        attrs_line = " ".join(f"{k}={card.attrs.get(k,0)}" for k in ATTR_KEYS)
        skills_line = "、".join(f"{k}={v}" for k, v in list(card.skills.items())[:12])
        yield event.plain_result(
            f"角色卡 · {card.name}\n"
            f"职业：{card.meta.get('job','')} 年龄：{card.meta.get('age','')}\n"
            f"{attrs_line}\n"
            f"HP={card.derived.get('HP')} MP={card.derived.get('MP')} SAN={san} "
            f"MOV={card.derived.get('MOV')} DB={card.derived.get('DB')}\n"
            f"技能：{skills_line or '（无）'}"
        )

    @filter.command("pcs")
    async def cmd_pcs(self, event: AstrMessageEvent):
        names = self.characters.list_names(self._uid(event))
        cur = self.characters.get_current(self._uid(event))
        if not names:
            yield event.plain_result("你还没有角色，/cq 创建")
            return
        lines = [f"你的角色（当前：{cur or '无'}）："]
        for n in names:
            mark = " *" if n == cur else ""
            lines.append(f"- {n}{mark}")
        yield event.plain_result("\n".join(lines))

    @filter.command("use")
    async def cmd_use(self, event: AstrMessageEvent, name: str):
        if not self.characters.get(self._uid(event), name):
            yield event.plain_result(f"没有角色「{name}」")
            return
        self.characters.set_current(self._uid(event), name)
        yield event.plain_result(f"当前角色 → {name}")

    @filter.command("del")
    async def cmd_del(self, event: AstrMessageEvent, *args: str):
        if not args:
            yield event.plain_result("用法：/del 角色名  或 /del 角色名 ! 确认删除")
            return
        name = args[0]
        confirm = len(args) > 1 and args[1] == "!"
        if not confirm:
            yield event.plain_result(f"确认删除「{name}」？再发 /del {name} !")
            return
        ok = self.characters.delete(self._uid(event), name)
        yield event.plain_result(f"已删除「{name}」" if ok else f"没有角色「{name}」")

    # --- battle ---

    def _load_battle(self) -> list[list[Any]]:
        import json

        if not self.battle_path.exists():
            return []
        try:
            data = json.loads(self.battle_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save_battle(self, rows: list[list[Any]]) -> None:
        import json

        self.battle_path.write_text(
            json.dumps(rows, ensure_ascii=False), encoding="utf-8"
        )

    @filter.command("init")
    async def cmd_init(self, event: AstrMessageEvent, *args: str):
        if args and args[0].lower() == "clear":
            self._save_battle([])
            yield event.plain_result("战斗轮已清空")
            return
        if not args:
            rows = self._load_battle()
            entries = sort_initiative([(str(n), int(s)) for n, s in rows])
            yield event.plain_result(format_initiative(entries))
            return
        # pairs: name score|expr
        pairs: list[tuple[str, int]] = []
        i = 0
        while i < len(args):
            name = args[i]
            if i + 1 >= len(args):
                break
            raw = args[i + 1]
            if raw.lower().endswith("d100") or raw.lower().startswith("d") or "d" in raw.lower():
                r = parse_and_roll(raw if "d" in raw.lower() else f"1{raw}", rng=self._rng)
                score = r.total
            elif raw.isdigit():
                score = int(raw)
            else:
                r = parse_and_roll(raw, rng=self._rng)
                score = r.total
            pairs.append((name, score))
            i += 2
        if not pairs:
            yield event.plain_result("用法：/init 张三 1d100 李四 80 ；/init 显示；/init clear")
            return
        # merge with existing
        existing = [(str(n), int(s)) for n, s in self._load_battle()]
        existing.extend(pairs)
        self._save_battle([[n, s] for n, s in existing])
        entries = sort_initiative(existing)
        yield event.plain_result(format_initiative(entries))

    # --- npc ---

    @filter.command("npcc")
    async def cmd_npcc(self, event: AstrMessageEvent, name: str):
        card = self._resolve_card(event)
        if not card:
            yield event.plain_result("无当前角色可复制，请先建卡")
            return
        npc = CharacterCard.from_dict(card.to_dict())
        npc.name = name
        npc.owner_user_id = "npc"
        self.npcs.save(npc)
        yield event.plain_result(f"已保存 NPC 模板「{name}」")

    @filter.command("npcs")
    async def cmd_npcs(self, event: AstrMessageEvent):
        names = self.npcs.list_names()
        if not names:
            yield event.plain_result("NPC 库为空。/npcc 名字 从当前角色保存")
            return
        yield event.plain_result("NPC：" + "、".join(names))

    @filter.command("npr")
    async def cmd_npr(self, event: AstrMessageEvent, name: str):
        npc = self.npcs.get(name)
        if not npc:
            yield event.plain_result(f"没有 NPC「{name}」")
            return
        try:
            from render.card import render_character_html

            san = int(npc.derived.get("SAN", npc.attrs.get("POW", 0)))
            html = render_character_html(npc, san_now=san)
            url = await self.html_render("{{ html|safe }}", {"html": html})
            yield event.image_result(url)
            return
        except Exception as e:
            logger.warning(f"npc html_render failed: {e}")
        attrs_line = " ".join(f"{k}={npc.attrs.get(k,0)}" for k in ATTR_KEYS)
        yield event.plain_result(
            f"NPC · {npc.name}\n{attrs_line}\n"
            f"HP={npc.derived.get('HP')} MP={npc.derived.get('MP')} SAN={npc.derived.get('SAN')}"
        )

    @filter.command("npcd")
    async def cmd_npcd(self, event: AstrMessageEvent, name: str):
        ok = self.npcs.delete(name)
        yield event.plain_result(f"已删除 NPC「{name}」" if ok else f"没有 NPC「{name}」")

    @filter.command("help")
    async def cmd_help(self, event: AstrMessageEvent):
        yield event.plain_result(HELP_TEXT)

    async def terminate(self):
        pass
