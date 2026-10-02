# 重设计 TrpgWorld 为「模组编译 + master 编排」的 TRPG 协议

## Goal

把「怎么跑一场 TRPG」从 Python/LangGraph 引擎中抽离成一套**通用 agent 可读、可执行的协议与目录结构**：

1. **编译（build-time）**：给定一份原始 TRPG 模组，用本项目的脚手架把它编译成一个**自包含、自描述、可运行**的冒险目录（解析拆分场景/线索/NPC/钩子，并按模组特性定制）。
2. **推进（play-time）**：master agent 读取该目录，从车卡自动推进到结团；GM/PL/NPC 是对称的「角色」，由子代理（或内联降级）扮演。

用户价值：跑团逻辑不再被单一引擎绑死；换任意主流 agent 宿主都能按同一套约定「编译 + 开跑」；模组、流程、规则、角色、状态都是可编辑、可 fork、可版本化的普通文件。

## Background（已确认事实）

- **旧实现**：Python + LangGraph，`src/game/engine.py` 状态机 `load_module → gm ↔ pl → log`；自写 `src/core/agent.py` 工具循环；`src/systems/coc/` 为 CoC 7e 规则；`src/module/reader.py` 按标题切分 markdown 模组。流程硬编码、智能被框架绑死——本次重做的动因。
- **宿主能力差异**：Pi 有 extension API 与原生 sub-agent API；dsh 无 project-level sub-agent 定义面，只能内联；Claude Code/Cursor 等形态不一。「派生子代理 + 分配工具」不是所有宿主都有，协议必须有降级路径。

## Requirements

- **R1 编译产物**：框架是一个工具库 + 脚手架；输入原始模组，产出一个自包含、自描述、可运行的「冒险目录」。
- **R2 宿主无关**：任意主流 agent 宿主都能读取并运行一份冒险目录；无 sub-agent 能力时降级为同上下文内联扮演角色。
- **R3 分层正交**：`rules`（机制）/ `flow`（阶段程序，跨模组复用）/ `module`（剧情内容）/ `characters`（角色实例）分层；模组通过 `hooks` 覆盖 flow 的阶段，不改 flow 本身。
- **R4 角色对称**：master agent 只推进流程、本身不是角色；GM/PL/NPC 是地位对称的角色，各自有独立设定、上下文与工具。
- **R5 频道化可见性**：可见性由 master 运行时编排的 `channel`（场景）实现，而非静态标签；channel 含 `purpose` / `participants` / `termination` / `outcome`；保留一条全员公共基线频道。
- **R6 场景协商**：场景由 master 依 flow/module 提议、KP 按叙事修订、master 校验并开启；master 有最终裁量权。
- **R7 规则确定性分层**：随机源（带种子）与状态变更**强制**走确定性工具；判定结算由规则工具提供（可 fork）；叙事裁决由 agent 决定；工具输出即真相。
- **R8 秘密隔离**：角色只能读到「自己可见的上下文投影」；隔离由目录/文件位置保证，不依赖角色自律。
- **R9 持久化与恢复**：冒险目录 + git；恢复 = `git checkout`；**每条消息提交 + 边界 tag**；所有 git 操作由确定性工具**串行**执行。
- **R10 角色记忆分层**：短期上下文（消息数组）/ 滚动摘要 / 长期笔记（`memory.md`）+ 卡面；场景结束时触发压缩。
- **R11 可 fork**：框架默认产物可被 agent 完全 fork；**唯一硬性不变量 = 目录自描述**（入口说明足够让任意 agent 读懂并运行）。
- **R12 适配层只供能力**：Pi/dsh 等插件不解读目录，只提供宿主能力（人类介入、子代理派生、上下文隔离）；协议声明所需能力，缺失则优雅降级。
- **R13 首个交付物**：中文文档——`docs/` 下的正式协议文档 + 根 `README.md` 简介。
- **R14 清理残留与旧实现**：移除生成物（`logs/`、`__pycache__/`、`.pytest_cache/`）与旧实现（`src/`、`main.py`、`tests/`、`pyproject.toml`、`uv.lock`、`.python-version`、`.env.example`、`.venv`）；**仅保留 `modules/`（原始模组）** 与工程/agent 配置（`.trellis/`、`.pi/`、`.dsh/`、`.agents/`、`AGENTS.md`、`.git*`、`README.md`）。旧实现仍保留在 git 历史（`ed80ff4`、`2fc6819`）中可恢复。

## Acceptance Criteria

- [ ] **AC1 编译 PoC**：对一份原始模组（如 `soup.md`）执行编译，产出冒险目录，含入口说明、`flow/`、`module/`（拆分后的场景/线索/NPC/hooks）、`roles/`、`channels/`、`world/`、`log/`、`tools/`、`.git`。
- [ ] **AC2 端到端**：任意 agent 读入口说明后，能从车卡推进到结团；编排不依赖框架内硬编码代码。
- [ ] **AC3 秘密隔离可验证**：不在 channel 中的 PL，其上下文投影不含该场景内容；秘密骰点数不出现在 PL 的投影中。
- [ ] **AC4 git 语义**：可按场景/阶段 tag 定位历史；`git checkout` 到任一提交后可继续推进。
- [ ] **AC5 降级可跑**：无 sub-agent 能力的宿主走内联降级，仍能跑完同一场团（隔离由可见性纪律模拟）。
- [ ] **AC6 文档自洽**：`docs/` + `README.md` 覆盖上述全部决策，为中文。
- [ ] **AC7 残留与旧实现清空**：工作树不再存在 `logs/`、`__pycache__/`、`.pytest_cache/`、`src/`、`main.py`、`tests/`、`pyproject.toml` 等；仅保留 `modules/` 与配置。

## 关键决策索引

技术细节见 `design.md`；执行步骤见 `implement.md`。

| # | 决策 | 结论 |
|---|---|---|
| D1 | 编排层策略 | 宿主无关核心 + 后期原生适配 |
| D2 | 参与模型 | master 推进流程；GM/PL/NPC 对称；人类担任可替换（前期全 agent） |
| D3 | 框架与内容 | 框架内容无关；flow 是可替换内容；自带 CoC example |
| D4 | 分层 | rules / flow（阶段粒度）/ module / characters 正交；模组 hooks 覆盖 flow |
| D5 | 项目与冒险目录 | 工具库/脚手架 → 生成自包含冒险目录；分发非目标 |
| D6 | 扩展模型 | 唯一不变量 = 自描述；其余完全可 fork；适配层只供能力 |
| D7 | 可见性与频道 | master 运行时编排 channel；保留公共基线；场景构成 = master↔KP 协商 |
| D8 | 规则确定性 | 随机+状态强制工具；判定结算规则工具；叙事裁决 agent；输出即真相 |
| D9 | 持久化 | 目录 + git；恢复 = checkout；每消息提交 + 边界 tag；工具串行 |
| D10 | 首份交付物 | `docs/` 正式文档 + 根 README（中文） |

## Out of Scope（本阶段不做）

- **replay 回放生成**（用户明确搁置）。
- **Pi / dsh 原生适配插件**（后期单独任务；协议只定义能力声明与降级）。
- **人类担任角色**（协议预留暂停/输入/恢复接口，前期全 agent）。
- **多种规则系统**（先只做 CoC 7e 一个 example）。
