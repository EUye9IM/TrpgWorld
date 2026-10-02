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

## 当前状态

本阶段（I1）交付物为协议文档（`docs/` + 本 README）。确定性工具、脚手架模板、CoC 7e 系统与端到端示例（I2/I3）为后续增量。
