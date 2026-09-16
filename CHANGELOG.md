# Changelog

本项目版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。  
格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1./)。

## [Unreleased]

### 计划中

- **DND 5e**：检定、豁免、优势劣势、先攻、角色卡与车卡
- 插件 WebUI 配置：默认属性法、指令开关、规则系统切换
- 更多规则系统（Pathfinder、COC 6e 变体等）
- 完整 CoC7 职业表与技能点分配
- 战斗轮按会话隔离
- 引导车卡会话持久化（重启可恢复）
- 奖励 / 惩罚骰在 `/ra` 输出中的更清晰分列展示

---

## [0.1.0] - 2026-07-12

首个可安装版本。AstrBot **≥4.16, &lt;5**。

### Added

#### 产品

- 中文显示名 **TRPG助手**（`metadata.yaml` `display_name`）
- 插件 Logo：`logo.png`（256×256）
- README：我的世界风格浏览计数器、TODO 路线（含 **DND 5e**）

#### 掷骰

- `/r`：支持 `NdM`、`NdM±K`、多段加减；缺省 `1d100`
- **d100 内核为两个 d10**（十位 + 个位），为奖励 / 惩罚骰设计
- 奖励骰 `b`（额外十位取最小）、惩罚骰 `p`（额外十位取最大），可连写
- `00+0` 记为 100；展示格式含选用十位标记

#### CoC7 检定

- `/ra`：技能值或技能名 / 属性名检定
- 成功等级：大成功（≤⅕）、困难成功（≤½）、成功、失败、大失败（100 或低技能 96+）
- 难度门槛 `n` / `h` / `e` / `c`；可与奖惩骰组合
- `/sc`：SAN 检定；成功 `1d4`（可设上限）、失败 `1d6+1`；与当前角色 SAN 一致时自动写回

#### 角色

- 多命名角色 JSON 存档 + 每用户当前角色指针
- `/cq` 快速车卡：属性法 `3d6x5`（默认）或 `2d6+6+30`；派生 HP/MP/SAN/MOV/DB/Build
- `/cc` 三步引导车卡：名字 → 职业与属性法 → 预览 / `r` 重随 / `ok` 保存
- `/set` 写入属性 / 技能 / 派生（SAN、HP、MP、luck）；同次命令中派生值不被属性重算覆盖
- `/pc` `/pcs` `/use` `/del`（删除需 `!` 确认）
- 角色图片卡（Jinja2 HTML + `html_render`），失败降级纯文本

#### NPC 与战斗

- `/npcc` `/npcs` `/npr` `/npcd`：全局 NPC 模板库；`/npr` 优先图卡
- `/init`：战斗轮追加、显示、`clear` 清空；同分按输入序

#### 工程

- `metadata.yaml`（新插件体系）、`astrbot_version: ">=4.16,<5"`
- 纯核心层单测（不依赖 AstrBot 运行时）：骰子、规则、存档、引导状态机、图卡渲染
- `i18n/zh-CN.json` 文案雏形
- Compose 规格：`docs/compose/spec/trpg-kit.md`

### Fixed

- `/set` 与属性重算同时写入 SAN / HP / MP 时，派生值被 `apply_attrs` 清空的问题
- 引导车卡仅创建会话、无法推进的问题（补齐状态机与消息推进）

### Notes

- 数据文件：`trpg_kit/characters.json`、`current.json`、`npcs.json`、`battle.json`
- 引导车卡会话为内存态，进程重启后未完成流程会丢失
- 未支持 AstrBot 旧版 API

---

[Unreleased]: https://github.com/Eason4869/astrbot_plugin_trpg_kit/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Eason4869/astrbot_plugin_trpg_kit/releases/tag/v0.1.0
