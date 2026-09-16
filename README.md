# CoC TRPG KP 工具（AstrBot 插件）

AstrBot ≥4.x 插件：CoC 跑团常用 —— 掷骰、车卡、SAN 检定、战斗轮、NPC 模板。

## 安装

将本仓库放入 AstrBot 的 `data/plugins/astrbot_plugin_trpg_kit`，或在 WebUI 插件市场/本地安装。无强制第三方运行时依赖（测试需 `requirements-dev.txt`）。

## 指令

| 指令 | 说明 |
|------|------|
| `/r [表达式] [b\|p]…` | 掷骰，默认 `1d100`（内部 2×d10，支持奖惩骰） |
| `/ra 技能值\|技能名 [n\|h\|e\|c] [b\|p]` | 技能检定 |
| `/sc [SAN] [成功损失上限]` | SAN 检定并可写回角色 |
| `/set STR=70 侦查=65` | 设置属性/技能 |
| `/cq [职业]` | 快速车卡 |
| `/cc` | 引导车卡（`/cc cancel` 取消） |
| `/pc` `/pcs` `/use 名` `/del 名 !` | 角色卡 / 列表 / 切换 / 删除 |
| `/init 名 分数 …` / `clear` | 战斗轮 |
| `/npcc 名` `/npcs` `/npr 名` `/npcd 名` | NPC 模板 |
| `/help` | 帮助 |

## 开发

```bash
python -m pytest tests -q
```

数据存放于插件 data 目录下 `trpg_kit/`（`characters.json` 等）。

灵感参考社区 CoC 骑士/骰子插件，但指令集刻意精简。License: AGPL-3.0（与 AstrBot 生态一致，发布前可再确认）。
