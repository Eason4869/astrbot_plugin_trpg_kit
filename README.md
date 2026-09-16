# TRPG助手

<p align="center">
  <img src="logo.png" alt="TRPG助手 Logo" width="128" />
</p>

<p align="center">
  <img src="docs/assets/visit-counter.svg" alt="Visit Counter" />
</p>

<p align="center">
  <a href="https://github.com/Eason4869/astrbot_plugin_trpg_kit"><img src="https://img.shields.io/badge/AstrBot-%3E%3D4.16-blue" alt="AstrBot"/></a>
  <img src="https://img.shields.io/badge/version-0.1.0-green" alt="version"/>
  <img src="https://img.shields.io/badge/rule-CoC%207e-orange" alt="CoC 7e"/>
</p>

[English](#english) · 简体中文

面向 [AstrBot](https://github.com/AstrBotDevs/AstrBot) ≥4.x 的 **TRPG 跑团助手** 插件。当前完整支持 **克苏鲁的呼唤（Call of Cthulhu）第七版**；未来将扩展 DND 等更多规则系统。

**中文名**：TRPG助手  
**包名**：`astrbot_plugin_trpg_kit`  
**设计原则**：指令短、含义单一、好记——拒绝大而全的复杂语法。日常掷骰发文本；角色卡 / NPC 卡优先出图。

| | |
|---|---|
| 插件包名 | `astrbot_plugin_trpg_kit` |
| 显示名称 | **TRPG助手** |
| 版本 | 0.1.0 |
| 运行时 | AstrBot `>=4.16,<5` |
| 当前规则 | CoC 7 版（中文跑团常用判定） |
| 数据 | 插件 data 目录下 `trpg_kit/*.json` |
| 仓库 | https://github.com/Eason4869/astrbot_plugin_trpg_kit |

---

## TODO

未来路线（欢迎 PR / Issue）：

- [ ] **DND 5e**：属性调整值、豁免、优势/劣势、先攻、生命骰
- [ ] **DND 5e 车卡**：种族 / 职业 / 熟练项与完整角色卡
- [ ] 更多规则系统：Pathfinder、COC 6e 变体等
- [ ] 插件 WebUI 配置：默认属性法、指令开关、规则系统切换
- [ ] 完整 CoC7 职业表与技能点分配
- [ ] 战斗轮按会话隔离；先攻表达式与重 roll
- [ ] 引导车卡会话持久化（重启可恢复）
- [ ] 图灵卡 / 身份背景故事模板
- [ ] 更丰富的检定分列展示（奖惩骰过程明细）

---

## 功能一览

- **掷骰**：`NdM` 表达式；`1d100` 内部按 **两个 d10**（十位 + 个位）合成，原生支持奖励骰 / 惩罚骰
- **技能检定**：对照技能值判定大成功 / 困难成功 / 成功 / 失败 / 大失败；可指定难度与奖惩骰
- **SAN 检定**：成功丢 `1d4`，失败丢 `1d6+1`；可选成功损失上限；有当前角色时自动写回 SAN
- **车卡**：`/cq` 一键随机；`/cc` 三步引导（名字 → 职业/属性法 → 预览重随/保存）
- **多角色存档**：每个平台用户可持有多个命名角色，支持切换 / 删除
- **图片卡**：角色与 NPC 默认走 `html_render` 出图，失败自动降级纯文本
- **战斗轮**：多人一次性投先攻并排序
- **NPC 模板**：从当前角色复制进全局库，可读取 / 删除

---

## 安装

### 方式一：WebUI 本地安装（推荐）

1. 在 GitHub 下载本仓库 ZIP，或 `git clone`
2. AstrBot 管理面板 → **插件** → 安装本地插件，指向插件目录
3. 确认 AstrBot 版本满足 `>=4.16`；重载或重启后生效

### 方式二：放入 data/plugins

```text
AstrBot/
  data/
    plugins/
      astrbot_plugin_trpg_kit/   ← 本仓库根目录整体放入
        metadata.yaml
        main.py
        ...
```

重启 AstrBot 或在插件页点击 **重载插件**。

### 依赖

- **运行时**：无必须的第三方 pip 包（图卡依赖 AstrBot 自带的文转图 / Playwright 能力）
- **开发测试**：见下方「开发」

插件数据目录（在 AstrBot 的插件数据根下创建）：

```text
trpg_kit/
  characters.json   # 各用户多角色
  current.json      # 各用户当前角色指针
  npcs.json         # 全局 NPC 模板
  battle.json       # 战斗轮（最近一次）
```

损坏的 JSON 会备份为 `*.bak` 后重建，不会导致插件崩溃。

---

## 快速上手

```text
/trpg帮助
/trpg快车 记者
/trpg角色
/trpg掷骰
/trpg检定 50
/trpg理智
```

1. `/trpg帮助` — 指令总表（**不要用 `/help`**，那是系统指令）
2. `/trpg快车 记者` — 随机属性、默认技能、设为当前角色  
3. `/trpg角色` — 看角色卡（图卡）  
4. `/trpg掷骰` — 默认 `1d100`  
5. `/trpg检定 50` — 对照 50% 技能检定  
6. `/trpg理智` — 用当前角色 SAN 做理智检定并写回  

---

## 指令手册

所有指令均带 **`trpg` 前缀**（中文名），避免与其它插件冲突。  
下表中 `b` = 奖励骰，`p` = 惩罚骰，可连写（`bb`、`bp`）。  
除纯掷骰外，涉及角色的指令默认操作 **当前角色**；可先 `/trpg切换 名` 切换。

### 掷骰与检定

| 指令 | 参数 | 说明 |
|------|------|------|
| `/trpg掷骰` | `[表达式] [b\|p]…` | 掷骰。缺省 `1d100`。表达式：`2d6`、`1d20+3` 等。仅对 `1d100` / `d100` 识别奖惩骰 |
| `/trpg检定` | `技能值\|技能名 [n\|h\|e\|c] [b\|p]…` | 技能检定。难度：`n` 常规（默认）、`h`/`e` 困难（≤半）、`c` 大成功 |
| `/trpg理智` | `[当前SAN] [成功损失上限]` | SAN 检定。省略 SAN 时用当前角色 SAN；与之一致时检定后写回 |

**示例**

```text
/trpg掷骰 1d100 b
/trpg掷骰 2d6+3
/trpg掷骰 1d100 pp
/trpg检定 侦查
/trpg检定 50 h
/trpg检定 75 c b
/trpg理智
/trpg理智 40 8
```

### 属性与角色

| 指令 | 参数 | 说明 |
|------|------|------|
| `/trpg设置` | `字段=值 …` | 批量写入。八维属性会重算派生；同次里的 `SAN`/`HP`/`MP`/`luck` 在重算之后应用 |
| `/trpg快车` | `[职业]` | 快速车卡：随机属性 + 派生值 + 默认技能，设为当前角色 |
| `/trpg车卡` | | 开始引导车卡；`/trpg车卡 取消` 取消 |
| `/trpg角色` | `[角色名]` | 查看角色卡（图卡优先）。无参 = 当前角色 |
| `/trpg列表` | | 列出本人全部角色（`*` 为当前） |
| `/trpg切换` | `角色名` | 切换当前角色 |
| `/trpg删除` | `角色名` `!` | 删除角色。需带 `!` 确认 |

**引导车卡流程（`/trpg车卡`）**

1. 回复角色名  
2. 回复职业，可附属性生成法：`记者 3d6` 或 `记者 2d6`  
3. 预览属性 → 回复 `ok` / `确定` 保存，或 `r` / `重随` 重 roll  

### 战斗轮

| 指令 | 参数 | 说明 |
|------|------|------|
| `/trpg战斗` | `名字 分数或表达式 …` | 追加并排序。分数可为 `80` 或 `1d100` |
| `/trpg战斗` | | 显示当前战斗轮 |
| `/trpg战斗` | `清空` | 清空 |

```text
/trpg战斗 张三 1d100 李四 72 深潜者 1d100
/trpg战斗 清空
```

排序：分数降序；同分按输入先后。

### NPC

| 指令 | 参数 | 说明 |
|------|------|------|
| `/trpg存npc` | `名字` | 将 **当前角色** 复制为全局 NPC 模板 |
| `/trpgnpc列表` | | 列出 NPC 名 |
| `/trpg读npc` | `名字` | 读取 NPC（图卡优先） |
| `/trpg删npc` | `名字` | 删除 NPC |

### 其他

| 指令 | 说明 |
|------|------|
| `/trpg帮助` | 插件帮助（**不是** 系统 `/help`） |

---

## 规则说明（CoC 7）

### d100 如何掷

内部使用 **两个 d10**：十位骰 + 个位骰，便于奖励 / 惩罚替换十位。

- 奖励骰 `b`：额外十位，取 **最小** 作为有效十位  
- 惩罚骰 `p`：额外十位，取 **最大** 作为有效十位  
- 先应用全部奖励，再应用惩罚  
- `00` + `0` 记为 **100**  
- 展示形如 `[3b* 7|5] → 35`（`*` 为选用的十位）

### 成功等级（技能值 `skill`，掷骰值 `roll`）

| 结果 | 条件 |
|------|------|
| **大失败** | `roll = 100`，或（`skill < 50` 且 `roll ≥ 96`） |
| **大成功** | `roll ≤ max(1, skill // 5)` |
| **困难成功** | `roll ≤ max(1, skill // 2)` |
| **成功** | `roll ≤ skill` |
| **失败** | 其余 |

`/ra` 的难度门槛：`h` / `e` 要求至少困难成功，`c` 要求大成功；未达标记为失败（大失败仍保留）。

### SAN 检定

- 掷 `1d100` ≤ 当前 SAN → 成功，损失 `1d4`（可设上限）  
- 否则失败，损失 `1d6+1`  
- 新 SAN = `max(0, SAN - 损失)`  

### 派生值（快速车卡默认）

| 项 | 公式 |
|----|------|
| HP | `CON//10 + SIZ//10` |
| MP | `POW//10` |
| SAN（初始） | `POW` |
| MOV | STR/DEX/CON 三者中 ≥50 与 <50 的个数决定：7 基准 / 8 / 6 |
| DB / Build | 按 `STR+SIZ` 分段（-2 … +2d6） |

属性生成：

- `3d6x5`（默认）：八维均为 `3d6×5`  
- `2d6+6+30`：八维均为 `2d6+6+30`  

> 本版 **不做** 完整职业表与正规技能点分配；快速车卡附带一组默认技能，可用 `/set` 手工补全。

---

## 配置

当前版本几乎零配置。默认属性法为 `3d6x5`；若需改为 `2d6+6+30`，可在代码中调整 `TrpgKit._attr_method`（后续版本将开放插件 WebUI 配置）。

---

## 开发

```bash
# 建议使用独立 venv
pip install -r requirements-dev.txt
pip install jinja2   # 图卡模板单测需要

python -m pytest tests -q
```

### 目录结构

```text
astrbot_plugin_trpg_kit/
  metadata.yaml
  main.py                 # Star 入口：指令绑定与编排
  dice/
    engine.py             # 表达式解析、d100(2×d10)、奖惩骰
    coc_rules.py          # 成功等级、SAN
  character/
    models.py             # 角色模型与派生值
    store.py              # 多角色 JSON 存取
    creator.py            # 快速生成
    guided.py             # 引导车卡状态机
  npc/store.py
  battle/initiative.py
  render/
    card.py
    templates/character.html
  i18n/zh-CN.json
  tests/
  docs/compose/spec/trpg-kit.md
```

### 设计约束

1. 规则与骰子为 **纯 Python**，不依赖 AstrBot API，便于单测  
2. `main.py` 只做事件绑定与格式化  
3. 持久化写在 AstrBot 的 data 目录，不写插件安装目录  
4. 网络库禁止使用 `requests`（本插件 MVP 无网络请求）  

### 命名

插件目录 / 仓库名：`astrbot_plugin_trpg_kit`（AstrBot 插件市场惯例前缀）。

---

## 已知限制（0.1.0）

- 引导车卡会话仅存内存，**机器人重启后未完成的 `/cc` 会丢失**  
- 无完整职业 / 技能点表，无造物卡、随身物品  
- 战斗轮不区分会话，仅保留最近一次全局表  
- `/init` 的「多行」通过空格分隔参数实现，未做真正的换行消息解析  
- 旧版 AstrBot（&lt;4.16）不在支持范围  
- 未接入完整 i18n 框架（仅有 `i18n/zh-CN.json` 文案雏形）  

---

## 致谢与许可

- 指令灵感来自社区 CoC 骑士 / TRPG 骰子插件，但本项目命令集刻意精简，**未移植其代码**  
- 与 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 生态一致，建议以 **AGPL-3.0** 发布（发布前请再确认与上游依赖声明一致）  

---

## English

**TRPG Assistant** — an AstrBot (≥4.16) plugin for tabletop sessions. Full **Call of Cthulhu 7e** support today; **D&D 5e** and more systems are on the [TODO](#todo).

**Philosophy**: short slash commands, one meaning each. Character/NPC sheets prefer image cards via `html_render`; rolls are plain text.

| Command | Description |
|---------|-------------|
| `/r [expr] [b\|p]…` | Roll dice (default `1d100` as two d10s; bonus/penalty on tens) |
| `/ra skill [n\|h\|e\|c] [b\|p]…` | Skill check with CoC7 levels |
| `/sc [san] [cap]` | SAN check; writes back if it matches current character |
| `/set STR=70 侦查=65` | Set attributes / skills |
| `/cq [job]` | Quick character |
| `/cc` | Guided creation (3 steps) |
| `/pc` `/pcs` `/use` `/del` | Sheet / list / switch / delete |
| `/init …` / `clear` | Initiative tracker |
| `/npcc` `/npcs` `/npr` `/npcd` | NPC templates |
| `/help` | Help |

Install: drop the repo into `data/plugins/astrbot_plugin_trpg_kit`. Tests: `pip install -r requirements-dev.txt && pytest`.

See the Chinese section above for full rules tables.

---

**Version**: 0.1.0 · **Changelog**: [CHANGELOG.md](./CHANGELOG.md)
