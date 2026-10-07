# TrpgWorld

把「怎么跑一场 TRPG」从任何具体引擎中抽离成一套**通用 agent 可读、可执行的协议与目录结构**。

跑团逻辑不再被单一引擎绑死：换任意主流 agent 宿主（Pi、dsh、Claude Code、Cursor……）都能按同一套约定「编译 + 开跑」；模组、流程、规则、角色、状态都是可编辑、可 fork、可版本化的普通文件。

## 两条工作流

- **编译（build-time）**：拿一份原始 TRPG 模组，用脚手架把它编译成一个**自包含、自描述、可运行**的冒险目录（拆分场景/线索/NPC/钩子，并按模组特性定制 flow）。
- **推进（play-time）**：master agent 读取冒险目录，从车卡自动推进到结团；GM/KP、PL、NPC 是地位对称的「角色」，由子代理（或内联降级）扮演。

## 核心概念

| 原语 | 一句话 |
|---|---|
| **Master** | 流程引擎/导演，**不是角色**：读 flow、编排频道、协商场景、落盘打 tag |
| **Role（角色）** | 对称的 GM/KP、PL、NPC，各有 persona / context / memory / sheet / tools |
| **Channel（频道）** | 有界的场景/交互，含 purpose / participants / termination / outcome |
| **Flow** | 跨模组复用的阶段程序 |
| **System** | 规则系统（机制层 + 默认 flow），自带 CoC 7e 示例 |
| **Module（模组）** | 剧情内容，用 `hooks` 覆盖 flow 阶段 |
| **Tool** | 确定性 CLI：随机、状态变更、投影、压缩、git 步进、判定结算 |
| **World State** | 共享真相（剧情层） |

**关键原则**：master 推进流程但不扮演角色；角色对称；角色可由 agent 或人类担任（前期全 agent）；工具输出即真相；秘密隔离由文件位置 + 投影工具保证。

## 目录一览

### 框架仓库（本项目）

```
TrpgWorld/
├─ README.md              # 中文简介（本文件）
├─ docs/                  # 中文协议文档
├─ tools/                 # 确定性 CLI 工具（模板源）
├─ templates/adventure/   # 冒险目录脚手架模板
├─ systems/coc7e/         # 规则系统示例
├─ examples/soup/         # 编译完成的冒险目录示例
├─ modules/               # 原始模组输入（soup.md、example.md）
└─ adapters/              # （后期）Pi/dsh 能力提供者
```

### 冒险目录（编译产物）

```
<adventure>/
├─ AGENTS.md   # 【必需·唯一不变量】自描述入口
├─ flow/       # 阶段程序
├─ rules/      # 规则（可裁剪）
├─ module/     # 场景 / 线索 / NPC / hooks
├─ roles/      # 角色：persona / context.jsonl / summary.md / memory.md / sheet
├─ channels/   # 场景：meta.json / transcript.md
├─ world/      # 共享世界状态
├─ log/        # 审计
├─ tools/      # 内嵌工具
└─ .git/       # 历史 / tag / 恢复 / 分叉
```

**唯一硬性不变量 = 目录自描述**（`AGENTS.md` 足够让任意 agent 读懂并运行）；其余完全可 fork。

## 文档

| 文档 | 内容 |
|---|---|
| [`docs/protocol.md`](./docs/protocol.md) | 协议总览：原语、两条生命周期 |
| [`docs/directory.md`](./docs/directory.md) | 目录契约：框架与冒险目录结构、必需/可选 |
| [`docs/tooling.md`](./docs/tooling.md) | 工具 CLI 契约 + git 步进契约 |
| [`docs/visibility.md`](./docs/visibility.md) | 频道化可见性、秘密隔离、记忆分层 |
| [`docs/capabilities.md`](./docs/capabilities.md) | 宿主能力声明与降级矩阵 |

原始模组示例见 [`modules/soup.md`](./modules/soup.md) 与 [`modules/example.md`](./modules/example.md)。

## 当前状态（阶段性归档）

> 本阶段完成：协议框架 + 通用工具 + CoC 车卡阶段 + core 加固。**宿主插件已规划但未实现**。

### 已完成

| 里程碑 | 内容 |
|---|---|
| **I1** | 中文协议文档 `docs/`（protocol / directory / tooling / visibility / capabilities）+ 本 README |
| **I2** | 通用确定性工具 `tools/`（PEP 723 + `uv run`：`dice` / `state` / `context` / `step` / `scaffold`）+ 脚手架 `templates/adventure/` |
| **I3** | CoC 7e **车卡阶段**：`systems/coc7e/`（车卡规则 + 默认 `flow/`，大成功 = 1–5）+ `examples/soup/`；`scaffold --system` 带入规则系统；车卡冒烟通过（内联降级） |
| **I5** | core 加固：mask **fail-closed**；频道状态驱动投影（closed→outcome，停止重放膨胀）；`worldPaths` 仅 `--debug`；**工具结果可见性通用原则**（位置即权限，不加 `--secret`） |

### 未完成 / 后续

| 项 | 状态 |
|---|---|
| **I4 宿主插件**（角色运行时契约 v2 + Pi 插件 `trpg_role` / `trpg_dice`） | **已规划、未实现**；机制化隔离 / 金丝雀测试 / C11–C17 预留 |
| CoC 后续阶段：导入 / 扮演·调查 / 战斗 / 理智 / 结团 | 未做 |
| `check resolve` 判定工具 | 未实现（`systems/coc7e/tools/` 为空） |
| dsh 插件适配 | 未做 |
| 真·独立上下文角色子代理 | 未做（仅文档与计划） |
| 人类担任角色、replay 回放 | 未做 |
| core 自动化测试 / CI | **缺失**（当前仅手工验证） |

### 已知边界

- **内联降级**：无子代理时角色共享同一上下文，隔离较弱（已知代价）。
- **隔离强度**：插件方案为「prompt 约束 + 不给 fs/bash」，属**临时**手段；机制化三层隔离与金丝雀测试待做。
- **模型先验剧透（L10）**：机制只能保证「没注入的看不到」，不能阻止模型本来就知道（如《毒湯》是知名谜题）。
- **无 `tests/` 与 CI**：安全关键逻辑（fail-closed、投影）目前靠手工验证。

工具用法详见 [`docs/tooling.md`](./docs/tooling.md)：

```bash
uv run tools/scaffold.py new --module modules/soup.md --out /tmp/soup --system coc7e
uv run tools/dice.py roll --expr 1d100 --seed 42
python3 tools/state.py get sanity --adventure /tmp/soup   # 纯标准库回退
```
