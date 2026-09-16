---
feature: trpg-kit
status: delivered
updated: 2026-07-12
branch: feat/trpg-kit
commits: 17de5dc..f4a7dd6
---

# CoC TRPG KP 工具插件（astrbot_plugin_trpg_kit）

## Report

**What was built** — AstrBot ≥4.x 插件 `astrbot_plugin_trpg_kit`：d100 内核为 2×d10（支持 b/p 奖惩骰）、CoC7 成功等级与 SAN 检定、每用户多命名角色 JSON 存档与当前指针、快速车卡与三步引导车卡、战斗轮排序、NPC 模板库、角色/NPC 图片卡（`html_render`，失败降级文本）。指令集刻意精简：`/r /ra /sc /set /cq /cc /pc /pcs /use /del /init /npcc /npcs /npr /npcd /help`。

**Verification** — `python -m pytest tests -q` → **27 passed**；`main.py` AST 语法检查通过。审查（general-1）三项关键修复后由 general-2 复审：引导 `/cc`、`/set` 派生覆盖、`/npr` 图卡均 RESOLVED。

**Journey log** — (1) 参考仓 WhiteEurya/TRPGdice 命令过复杂，产品向「短、少、单一语义」收敛。(2) d100 用 2×d10 以便奖惩替换十位；00+0→100。(3) `/set` 须先 `apply_attrs` 再写 SAN/HP/MP，否则派生被重算冲掉。(4) 引导车卡做成纯状态机 `character/guided.py`，便于无 AstrBot 单测。(5) 本机无 `gh` CLI，GitHub 建仓/push 走 API + `http.proxy=` 绕过本机代理。

## [S1] Problem

跑团（CoC 7 版）需要在聊天群里完成车卡、掷骰、SAN 检定、战斗辅助与 NPC 调用。现有参考实现指令过于复杂、语义不清晰。需要一个 AstrBot ≥4.x 插件，指令少而清楚，角色可按名多存，车卡结果以图片卡展示。

## [S2] Design

### 已定决策

| 轴 | 决策 |
|----|------|
| 运行时 | AstrBot ≥4.x，新插件体系（`metadata.yaml` + `astrbot.api.star/event`） |
| 包名 | `astrbot_plugin_trpg_kit` |
| 规则 | CoC 7 版（中文群常用判定） |
| 指令风格 | 斜杠指令为主；**短、少、含义单一**，拒绝大而全语法 |
| 角色模型 | 每用户多命名角色；按名引用；有「当前角色」指针 |
| 车卡 | 一次性快速生成 + 可选多轮引导 |
| 展示 | 角色卡/完整检定卡：图片（`html_render`）；日常掷骰：纯文本 |
| 掷骰内核 | d100 = 两个 d10（十位+个位），为奖惩骰预留 |
| 存储 | AstrBot 插件数据目录，JSON 持久化 |

### 架构

```
astrbot_plugin_trpg_kit/
  metadata.yaml
  main.py                 # Star 插件入口：注册指令、编排
  dice/engine.py          # 骰子表达式与 d100(2×d10)、奖惩骰
  dice/coc_rules.py       # CoC7 成功等级、SAN 检定
  character/models.py     # 角色数据模型与派生值（HP/MP/SAN）
  character/store.py      # 多角色 JSON 存取、当前角色指针
  character/creator.py    # 快速生成 + 引导态
  npc/store.py            # NPC 模板存取
  battle/initiative.py    # 战斗轮排序
  render/templates/*.html # Jinja2 图卡模板
  i18n/zh-CN.json         # 文案
  requirements.txt
  tests/                  # 引擎与规则单测（不依赖 AstrBot）
```

**原则**：规则与骰子为纯 Python（可单测）；`main.py` 只做事件绑定与输出格式化；AstroBot 运行时 API 不进入 core 单测路径。

### 指令一览（刻意精简）

所有指令默认作用于「当前角色」（若存在）。`@角色名` 可覆盖（除纯掷骰类）。

| 指令 | 参数 | 行为 |
|------|------|------|
| `/r` | `[表达式]` `[b\|p]`… | 掷骰。缺省 `1d100`。表达式见下。后缀 `b`/`p` 表示 1 枚奖励/惩罚骰（可多次，如 `bb`/`bpp`），仅对 `Xd100` 有效 |
| `/ra` | `技能值或技能名` `[难度]` | 技能检定。难度：`n`常规(可省)/`h`困难/`e`极难/`c`大成功门槛；可与 `b`/`p` 奖惩骰连用：`/ra 侦查 h b` |
| `/sc` | `[当前SAN]` `[损失上限]` | SAN 检定；省略则用当前角色 SAN。输出成功=理智-1d4、失败=1d6+1 损失 |
| `/set` | `字段=值` … | 批量设置属性/技能。例：`/set STR=70 侦查=65 SAN=55` |
| `/cc` | | 打开车卡引导（当前会话、发起者、带步骤） |
| `/cq` | `[职业]` | 快速车卡：随机属性+派生值+默认技能，立即可存 |
| `/pc` | | 当前角色图片卡 |
| `/pcs` | | 列出本用户名下全部角色 |
| `/use` | `角色名` | 切换当前角色 |
| `/del` | `角色名` | 删除角色（需再发一次确认或参数 `!`） |
| `/init` | `[列表]` 或 `/init` | 战斗轮：无参=显示当前；`名字 d100` 可多行；`/init clear` 清空 |
| `/npcc` | `名字` | 从当前角色复制为 NPC 模板（全局库） |
| `/npcs` | | 列出 NPC 模板名 |
| `/npr` | `名字` | 读出 NPC 图片卡 |
| `/npcd` | `名字` | 删除 NPC 模板 |
| `/help` | | 本插件指令简表 |

**明确不做**（避免变复杂）：自定义公式语言、跨会话剧本状态机、在线数据同步、WebUI 面板、复杂权限点系统。

### 掷骰表达式

仅支持：`NdM`、`NdM+K`、`NdM-K`、多骰加总 `NdM+NdM`，以及 `Nd100`。  
解析失败时回复一行帮助，不抛异常到框架。

**d100 实现**：`d100( bonus, penalty ) -> (tens_list, ones, value)`  
- 十位骰数 = `1 + bonus + penalty` 枚 d10  
- 奖励：十位取**最小**；惩罚：十位取**最大**；二者同时存在时先合成（常见社区规则：每枚奖/惩替换十位）  
- 值 = `tens*10 + ones`；若 `00+0` 记为 **100**（显示可标 `00`）  
- 展示：`[十位骰…] [个位] → 总值`，奖惩用 `b`/`p` 标在骰子旁  

### CoC7 成功等级（`coc_rules.py`）

对技能值 `skill`（0–999，视为百分比技能的 1/10 位已折入，即 50 = 50%）与掷骰值 `roll`（1–100）：

1. **Fumble 失败**：`roll == 100`，或（`skill < 50` 且 `roll >= 96`）  
2. **Critical 大成功**：`roll <= max(1, skill // 5)` 且未先命中 Fumble 规则冲突时（`01` 在 `skill>=1` 时按大成功；`00` 按 100）  
3. **Extreme 极难成功**：`roll <= max(1, skill // 2)`  
4. **Regular 成功**：`roll <= skill`  
5. 否则 **Failure 失败**

奖惩骰后用合成后的 `roll` 判等级。`/ra` 输出一行：`检定[技能]=x：十位/个位 → roll，成功等级`。

### SAN 检定

- 默认：`当前SAN` 与 `1d100` 比较（CoC7：掷骰 ≤ SAN 则成功）  
- 输出：等级 + 损失（成功 `1d4`，失败 `1d6+1`）+ 新 SAN（不低于 0）  
- 可选参数：`/sc 40` 指定用于比较的 SAN；`/sc 40 8` 成功损失上限 8（失败仍 1d6+1）  
- 若有当前角色，自动回写 SAN 并在下次 `/pc` 反映

### 角色数据模型

```json
{
  "name": "张三",
  "owner_user_id": "平台ID",
  "attrs": {"STR":50,"CON":50,"POW":50,"DEX":50,"APP":50,"SIZ":50,"INT":50,"EDU":50},
  "derived": {"HP":10,"MP":10,"SAN":50,"MOV":7,"DB":"0","build":0,"luck":50},
  "skills": {"侦查":25,"聆听":20},
  "meta": {"job":"记者","age":24,"sex":"男","notes":""},
  "updated_at": "ISO8601"
}
```

- **派生**（CoC7）：`HP=CON//10+SIZ//10`，`MP=POW//10`，`SAN=POW`（初始），`MOV` 按 STR/DEX/CON 三者与 50 比较规则，`DB/build` 按 STR+SIZ  
- **快速车卡**：八维 `3d6×5`（可配置改为 2d6+6+30）；默认技能点 = `EDU×2` 按职业粗分（MVP：侦查/聆听/话术/攀爬/图书馆/心理学 等默认值），未做完整职业表  
- **引导车卡**（`/cc`）：步骤固定少：①角色名 ②职业名（文本） ③选择属性生成方式 ④确认随机结果 ⑤可选补点。每步一条回复；超时/取消 `/cc cancel`  
- 多角色：`characters.json` 中 `owner_user_id → { name → card }`，另 `current.json` 存 `owner → name`  
- 损坏文件：加载失败时备份为 `*.bak` 并新建空库，不崩溃

### NPC

全局 `npcs.json`：`name → card`（结构同角色，无 owner）。`/npcc` 复制当前角色为 NPC。

### 战斗轮

`battle.json`（可扩展为会话级；MVP 按插件全局 + 可选会话 id 键）。  
`/init` 解析多行 `名字 表达式`，统一按 d100 掷后排序降序，文本输出表格；同分按输入序。不持久化跨天会话历史。

### 图片卡

- `render/templates/character.html`：中文衬线/黑体 CSS，属性网格、技能表、页脚时间  
- 通过 `self.html_render(tmpl, ctx)` → `event.image_result(url)`  
- 渲染失败：降级纯文本完整卡，日志 warning  

### 配置（`metadata.yaml` / 插件配置）

MVP 仅少量：`attr_gen_method`：`3d6x5`（默认）或 `2d6+6+30`；`command_prefix` 保持 AstrBot 默认斜杠。高级项不做。

### 错误处理

- 指令参数错误：一行中文提示 + 最小示例  
- 异常统一捕获，回复「指令执行出错」；`logger.exception`  
- 不使用 `requests`；异步 IO 用 `asyncio` 即可（本地文件）

### 测试边界

| 层 | 方式 |
|----|------|
| dice/engine | pytest：表达式解析、奖惩十位合成、00/100 边界 |
| dice/coc_rules | pytest：等级表全分支（含 skill<50 失败区间） |
| character/creator & store | pytest：临时目录 JSON 读写、当前指针 |
| battle/initiative | pytest：排序与同分 |
| main.py 集成 | 不在 MVP 做 AstrBot 运行时 E2E；以 core 测试为准 |

### 数据路径

AstroBot 插件 `data` 根下建 `trpg_kit/`：`characters.json`、`current.json`、`npcs.json`、`battle.json`。具体取数用 AstrBot 提供的插件数据目录 API（若 4.x 有 `Context.get_config`/插件 cwd 约定，则用官方「持久化存 data 目录」规范路径）。

## [S3] Out of Scope

- 完整 CoC 职业技能点表与正规车卡规则书复刻  
- 奖励骰/惩罚骰的 WebUI 配置界面（引擎支持即可，指令可用）  
- 多语言 i18n 框架完整接入（先 zh-CN 字符串集中）  
- 图灵卡、随身物品、战役剧情状态机  
- 对旧版 AstrBot API 兼容  

## Tasks

- [x] T1: 掷骰引擎 d100(2×d10)+奖惩骰与表达式解析 — acceptance: `pytest tests/test_dice_engine.py` 全绿，覆盖 bb/pp/00/100 (covers: S2 掷骰)
- [x] T2: CoC7 成功等级与 SAN 规则纯函数 — acceptance: `pytest tests/test_coc_rules.py` 全绿 (covers: S2 成功等级/SAN; depends: T1)
- [x] T3: 角色模型、派生值、JSON 多角色存取与当前指针 — acceptance: `pytest tests/test_character_store.py` 全绿 (covers: S2 角色)
- [x] T4: 快速车卡生成器（属性方式可切换） — acceptance: 单测生成属性合法且派生一致 (covers: S2 车卡; depends: T3)
- [x] T5: NPC 库与战斗轮排序 core — acceptance: pytest 覆盖增删列与排序 (covers: S2 NPC/战斗)
- [x] T6: main.py 注册全部指令并接 core；文本掷骰输出 — acceptance: 模块可 import，指令 handler 齐全；人工对照指令表抽查逻辑调用 (covers: S2 指令; depends: T1–T5)
- [x] T7: 角色图片卡 HTML 模板 + html_render 接入与文本降级 — acceptance: 模板存在且 render 函数单测（Jinja 预渲染）通过 (covers: S2 图片卡; depends: T3)
- [x] T8: 引导车卡会话态（`/cc` 少步骤 + cancel） — acceptance: 状态机单测步骤转移 (covers: S2 引导车卡; depends: T4)
- [x] T9: README、requirements、ruff 整洁；全量 pytest — acceptance: `python -m pytest` 全绿 (covers: S2; depends: T6–T8)
