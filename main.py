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
from dice.engine import DiceError, D100Roll, ExprResult, format_d100, parse_and_roll, parse_bonus_penalty_suffix, roll_d100
from npc.store import NpcStore
from render.dice_card import render_dice_html

HELP_TEXT = """【TRPG助手 · 帮助】
指令带 trpg 前缀，避免与其它插件冲突。

/trpgroll [表达式] [b|p]…
  掷骰，默认 1d100；b 奖励 / p 惩罚
  例：/trpgroll 1d100 b

/trpgcheck 技能值|技能名 [n|h|e|c] [b|p]…
  技能检定；n常规 h/e困难 c大成功
  例：/trpgcheck 50 h

/trpgsan [SAN] [成功损失上限]
  SAN 检定并写回当前角色

/trpg设置 字段=值 …
  例：/trpg设置 STR=70 侦查=65 SAN=55

/trpgquick [职业]   快速车卡
/trpgcc             引导车卡（取消：/trpgcc cancel）
/trpgpc [角色名]    角色卡（图）
/trpgpcs            角色列表
/trpguse 角色名     切换当前角色
/trpgdel 角色名 !   确认删除

/trpginit [名 分数 …] 战斗轮 / 无参查看 / clear
  例：/trpginit 张三 1d100 李四 80

/trpgnpcc 名 | /trpgnpcs | /trpgnpr 名 | /trpgnpcd 名

/trpg帮助            本说明（纯文本）"""


def _plugin_data_dir(context: Context) -> Path:
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

    def _uid(self, event: AstrMessageEvent) -> str:
        try:
            return str(event.get_sender_id())
        except Exception:
            return str(event.message_obj.sender.id)

    def _resolve_card(self, event: AstrMessageEvent, name: str | None = None) -> CharacterCard | None:
        return self.characters.resolve(self._uid(event), name)

    # --- dice / check ---

    @filter.command("trpgroll")
    async def cmd_roll(self, event: AstrMessageEvent, *args: str):
        """TRPG助手掷骰：图 + 文"""
        try:
            rest, bonus, penalty = parse_bonus_penalty_suffix(list(args))
            expr = rest[0] if rest else "1d100"
            result = parse_and_roll(expr, bonus=bonus, penalty=penalty, rng=self._rng)
            extra = f" 奖励×{bonus} 惩罚×{penalty}" if bonus or penalty else ""
            text = f"掷骰 {expr}{extra}\n{result.text}"
            payload = self._dice_payload(expr, result, bonus, penalty)
            sent_img = False
            try:
                html = render_dice_html(payload)
                url = await self.html_render("{{ html|safe }}", {"html": html})
                yield event.image_result(url)
                sent_img = True
            except Exception as e:
                logger.warning(f"dice image failed, text only: {e}")
            # always send text summary (image + text)
            yield event.plain_result(text)
            _ = sent_img
        except DiceError as e:
            yield event.plain_result(f"表达式错误：{e}\n例：/trpgroll 1d100 b 或 /trpgroll 2d6+3")

    def _dice_payload(
        self, expr: str, result: ExprResult, bonus: int, penalty: int
    ) -> dict[str, Any]:
        dice: list[dict[str, Any]] = []
        if result.is_d100 and result.d100 is not None:
            d100: D100Roll = result.d100
            for i, t in enumerate(d100.tens_pool):
                tag = d100.marked[i] if i < len(d100.marked) else ""
                chosen = t == d100.chosen_tens
                role = "十位"
                if tag == "b":
                    role = "奖励"
                elif tag == "p":
                    role = "惩罚"
                dice.append(
                    {
                        "sides": 10,
                        "value": t,
                        "display": str(t),
                        "label": role,
                        "chosen": chosen,
                        "tag": tag,
                    }
                )
            dice.append(
                {
                    "sides": 10,
                    "value": d100.ones,
                    "display": str(d100.ones),
                    "label": "个位",
                    "chosen": True,
                    "tag": "",
                }
            )
            total = d100.value
        else:
            for term in result.terms:
                for v in term.rolls:
                    dice.append(
                        {
                            "sides": term.sides,
                            "value": v,
                            "display": str(v),
                            "label": f"{term.n}d{term.sides}",
                            "chosen": True,
                            "tag": "",
                        }
                    )
            total = result.total
        return {
            "title": f"掷骰 {expr}",
            "dice": dice[:12],
            "total": total,
            "text": result.text,
            "bonus": bonus,
            "penalty": penalty,
        }

    @filter.command("trpgcheck")
    async def cmd_check(self, event: AstrMessageEvent, *args: str):
        """TRPG助手技能检定"""
        try:
            rest, bonus, penalty = parse_bonus_penalty_suffix(list(args))
            if not rest:
                yield event.plain_result("用法：/trpgcheck 侦查  或  /trpgcheck 50 h b")
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
                    yield event.plain_result(f"未找到角色技能「{token}」，请先 /trpgquick 或 /trpg设置 {token}=值")
                    return
                if token not in card.skills:
                    if token.upper() in ATTR_KEYS:
                        skill = int(card.attrs.get(token.upper(), 0))
                    else:
                        yield event.plain_result(f"角色没有技能「{token}」，可用 /trpg设置 {token}=值 写入")
                        return
                else:
                    skill = int(card.skills[token])
            d100 = roll_d100(self._rng, bonus=bonus, penalty=penalty)
            result = check_vs_skill(d100, skill, difficulty=difficulty or "n")
            expr = "1d100"
            fake = ExprResult(
                terms=[],
                total=d100.value,
                is_d100=True,
                d100=d100,
                text=format_d100(d100),
            )
            payload = self._dice_payload(expr, fake, bonus, penalty)
            payload["title"] = f"检定[{label}]={skill}"
            payload["subtitle"] = result.level.value
            try:
                html = render_dice_html(payload)
                url = await self.html_render("{{ html|safe }}", {"html": html})
                yield event.image_result(url)
            except Exception as e:
                logger.warning(f"check dice image failed: {e}")
            yield event.plain_result(
                f"检定[{label}]={skill} {format_d100(d100)}\n{result.level.value}"
            )
        except DiceError as e:
            yield event.plain_result(f"检定失败：{e}")

    @filter.command("trpgsan")
    async def cmd_sanity(self, event: AstrMessageEvent, *args: str):
        """TRPG助手 SAN 检定"""
        san = None
        cap = None
        if args and args[0].isdigit():
            san = int(args[0])
        if len(args) > 1 and args[1].isdigit():
            cap = int(args[1])
        card = self._resolve_card(event)
        if san is None:
            if not card:
                yield event.plain_result("无当前角色。用法：/trpgsan 50 或先 /trpgquick 建卡")
                return
            san = int(card.derived.get("SAN", card.attrs.get("POW", 0)))
        res = san_check(san, rng=self._rng, success_loss_cap=cap)
        # rebuild d100 visual from roll value
        if res.roll == 100:
            tens, ones = 0, 0
        else:
            tens, ones = divmod(res.roll, 10)
        d100 = D100Roll(tens_pool=[tens], ones=ones, chosen_tens=tens, marked=[""])
        fake = ExprResult(terms=[], total=res.roll, is_d100=True, d100=d100, text=format_d100(d100))
        payload = self._dice_payload("1d100", fake, 0, 0)
        payload["title"] = "SAN 检定"
        payload["subtitle"] = f"{'成功' if res.success else '失败'} · 损失{res.loss} · 剩{res.new_san}"
        try:
            html = render_dice_html(payload)
            url = await self.html_render("{{ html|safe }}", {"html": html})
            yield event.image_result(url)
        except Exception as e:
            logger.warning(f"san dice image failed: {e}")
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

    @filter.command("trpg设置")
    async def cmd_set(self, event: AstrMessageEvent, *args: str):
        """TRPG助手设置属性技能"""
        if not args:
            yield event.plain_result("用法：/trpg设置 STR=70 SAN=55 侦查=40")
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
        for k, v in derived_over.items():
            card.derived[k] = v
        card.skills.update(skills)
        self.characters.save(card)
        yield event.plain_result(
            f"已更新角色「{card.name}」：属性{attrs or '无'} 派生{derived_over or '无'} 技能{skills or '无'}"
        )

    @filter.command("trpgquick")
    async def cmd_quick(self, event: AstrMessageEvent, *args: str):
        """TRPG助手快速车卡"""
        name = f"P{self._uid(event)[-4:]}"
        job = args[0] if args else "调查员"
        card = quick_create(name=name, owner=self._uid(event), job=job, method=self._attr_method, rng=self._rng)
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
            f"已设为当前角色。查看：/trpgpc"
        )

    @filter.command("trpgcc")
    async def cmd_cc(self, event: AstrMessageEvent, *args: str):
        """TRPG助手引导车卡"""
        uid = self._uid(event)
        if args and args[0].lower() in ("cancel", "取消"):
            self._cc_sessions.pop(uid, None)
            yield event.plain_result("已取消车卡")
            return
        session = start_cc()
        session.message = session.message.replace("/trpg车卡 取消", "/trpgcc cancel")
        self._cc_sessions[uid] = session
        yield event.plain_result(session.message)

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_cc_text(self, event: AstrMessageEvent):
        """引导车卡：非指令纯文本推进"""
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
            yield event.plain_result("引导车卡出错，已结束。可 /trpgcc 重试")

    @filter.command("trpgpc")
    async def cmd_card(self, event: AstrMessageEvent, *args: str):
        """TRPG助手角色卡"""
        name = args[0] if args else None
        card = self._resolve_card(event, name)
        if not card:
            yield event.plain_result("无角色。/trpgquick 快速车卡 或 /trpgpcs 查看列表")
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

    @filter.command("trpgpcs")
    async def cmd_list(self, event: AstrMessageEvent):
        """TRPG助手角色列表"""
        names = self.characters.list_names(self._uid(event))
        cur = self.characters.get_current(self._uid(event))
        if not names:
            yield event.plain_result("你还没有角色，/trpgquick 创建")
            return
        lines = [f"你的角色（当前：{cur or '无'}）："]
        for n in names:
            mark = " *" if n == cur else ""
            lines.append(f"- {n}{mark}")
        yield event.plain_result("\n".join(lines))

    @filter.command("trpguse")
    async def cmd_use(self, event: AstrMessageEvent, name: str):
        """TRPG助手切换当前角色"""
        if not self.characters.get(self._uid(event), name):
            yield event.plain_result(f"没有角色「{name}」")
            return
        self.characters.set_current(self._uid(event), name)
        yield event.plain_result(f"当前角色 → {name}")

    @filter.command("trpgdel")
    async def cmd_del(self, event: AstrMessageEvent, *args: str):
        """TRPG助手删除角色"""
        if not args:
            yield event.plain_result("用法：/trpgdel 角色名  或 /trpgdel 角色名 ! 确认删除")
            return
        name = args[0]
        confirm = len(args) > 1 and args[1] in ("!", "！")
        if not confirm:
            yield event.plain_result(f"确认删除「{name}」？再发 /trpgdel {name} !")
            return
        ok = self.characters.delete(self._uid(event), name)
        yield event.plain_result(f"已删除「{name}」" if ok else f"没有角色「{name}」")

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

    @filter.command("trpginit")
    async def cmd_init(self, event: AstrMessageEvent, *args: str):
        """TRPG助手战斗轮"""
        if args and args[0].lower() in ("clear", "清空"):
            self._save_battle([])
            yield event.plain_result("战斗轮已清空")
            return
        if not args:
            rows = self._load_battle()
            entries = sort_initiative([(str(n), int(s)) for n, s in rows])
            yield event.plain_result(format_initiative(entries))
            return
        pairs: list[tuple[str, int]] = []
        i = 0
        while i < len(args):
            name = args[i]
            if i + 1 >= len(args):
                break
            raw = args[i + 1]
            if "d" in raw.lower():
                r = parse_and_roll(raw, rng=self._rng)
                score = r.total
            elif raw.isdigit():
                score = int(raw)
            else:
                r = parse_and_roll(raw, rng=self._rng)
                score = r.total
            pairs.append((name, score))
            i += 2
        if not pairs:
            yield event.plain_result("用法：/trpginit 张三 1d100 李四 80 ；无参查看；/trpginit clear")
            return
        existing = [(str(n), int(s)) for n, s in self._load_battle()]
        existing.extend(pairs)
        self._save_battle([[n, s] for n, s in existing])
        entries = sort_initiative(existing)
        yield event.plain_result(format_initiative(entries))

    @filter.command("trpgnpcc")
    async def cmd_npc_save(self, event: AstrMessageEvent, name: str):
        """TRPG助手保存 NPC"""
        card = self._resolve_card(event)
        if not card:
            yield event.plain_result("无当前角色可复制，请先建卡")
            return
        npc = CharacterCard.from_dict(card.to_dict())
        npc.name = name
        npc.owner_user_id = "npc"
        self.npcs.save(npc)
        yield event.plain_result(f"已保存 NPC 模板「{name}」")

    @filter.command("trpgnpcs")
    async def cmd_npc_list(self, event: AstrMessageEvent):
        """TRPG助手 NPC 列表"""
        names = self.npcs.list_names()
        if not names:
            yield event.plain_result("NPC 库为空。/trpgnpcc 名字 从当前角色保存")
            return
        yield event.plain_result("NPC：" + "、".join(names))

    @filter.command("trpgnpr")
    async def cmd_npc_read(self, event: AstrMessageEvent, name: str):
        """TRPG助手读取 NPC"""
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

    @filter.command("trpgnpcd")
    async def cmd_npc_del(self, event: AstrMessageEvent, name: str):
        """TRPG助手删除 NPC"""
        ok = self.npcs.delete(name)
        yield event.plain_result(f"已删除 NPC「{name}」" if ok else f"没有 NPC「{name}」")

    @filter.command("trpg帮助")
    async def cmd_help(self, event: AstrMessageEvent):
        """TRPG助手帮助 — 强制纯文本，不做 t2i"""
        # Force plain text only: never call html_render / text_to_image / image_result
        # Long-message auto t2i may still apply at platform layer; keep message compact.
        yield event.plain_result(HELP_TEXT)

    async def terminate(self):
        pass
