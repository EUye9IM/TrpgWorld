# 协议总览

> 本文件定义 TrpgWorld 的**原语**与**两条生命周期**，是整个协议的入口。其余文档：
> 目录契约见 [`directory.md`](./directory.md)，工具契约见 [`tooling.md`](./tooling.md)，
> 可见性与记忆见 [`visibility.md`](./visibility.md)，宿主能力与降级见 [`capabilities.md`](./capabilities.md)。

## 1. 这是什么

TrpgWorld 把「怎么跑一场 TRPG」从任何具体引擎中抽离成一套**通用 agent 可读、可执行的协议与目录结构**。

- **不再绑死单一引擎**：跑团逻辑不再由 Python/LangGraph 状态机硬编码，而是由 agent 阅读普通文件后执行。
- **换宿主不改协议**：任意主流 agent 宿主（Pi、dsh、Claude Code、Cursor……）都能读取并运行同一份冒险目录。
- **一切都是普通文件**：模组、流程、规则、角色、状态、历史都是可编辑、可 fork、可版本化的文本。

系统分为两部分，彼此解耦：

```
① 框架仓库 (TrpgWorld 项目本身)          ② 冒险目录 (编译产物, 每份模组一个)
   工具库 + 脚手架 + 模板 + 规则 + 示例       自包含 / 自描述 / 自运行 / git 管理
   ─────────────────────────────           ─────────────────────────────
   编译 (build-time)  ───────────────────▶  推进 (play-time)
```

- **框架仓库不持有任何游戏实例**，只提供能力与模板。
- **冒险目录是运行单元**：任意 agent 读它的入口说明（`AGENTS.md`）即可开跑。
- **适配层（Pi/dsh 插件）不属于这两者**：它是宿主侧的能力提供者，只提供能力、**不解读冒险目录**。

## 2. 两条工作流

### 2.1 编译（build-time）

输入一份原始 TRPG 模组，产出一个自包含、自描述、可运行的**冒险目录**。由 agent 执行，步骤概览（细节见 [`directory.md`](./directory.md) 与 [`tooling.md`](./tooling.md)）：

1. 用户提供原始模组（markdown 等）。
2. agent 读 `docs/` 与 `templates/adventure/` 的脚手架指令。
3. 生成冒险目录骨架，`git init`。
4. **解析模组**：拆分场景 → `module/scenes/`；提取线索 → `clues.md`；NPC → `npcs/`；模组特例 → `hooks.md`。
5. **定制 flow**：默认取 `systems/coc7e/flow`，按模组特性用 `hooks` 覆盖个别阶段（**不改 flow 本体**）。
6. 按模组特性微调目录（可增删目录/文件，可改造工具）。
7. 生成 `AGENTS.md`：自描述「本目录结构与推进方式」。
8. `tools/step commit --tag compile/<module>` 落盘初始提交。

### 2.2 推进（play-time）

master agent 读取冒险目录，从车卡自动推进到结团。单步循环：

```
master 读 AGENTS.md + flow            # 定位当前阶段
  ↓
按 flow 阶段决定下一个场景
  ↓
【协商】master 提议 {purpose, participants} → KP 修订 → master 校验并开 channel
  ↓
【运行】参与者子代理各自基于「自己的 context 投影」在 channel 中交互
  ↓
【裁决】需要判定时调用 rules 工具（判定结算）；叙事决定由角色做
  ↓
【副作用】工具写 world/、log/，并把 channel transcript 落盘
  ↓
【结束】master 判定 termination → 生成 channel outcome（纪要）
  ↓
【同步】master 将应公开的 outcome publish 到公共基线频道
  ↓
【记忆】context compact：短期溢出 → summary；更新各角色 memory/context
  ↓
【步进】tools/step commit（每条消息/每步）+ 阶段边界打 tag
  ↓
进入下一场景，或 flow 迁移到下一阶段，直到「结团」
```

- **车卡场景**：master 编排多个 PL 共同讨论，PL 提交卡面后才把结果交给 KP。
- **秘密团场景**：master 编排 KP + 特定 PL，其余待机 PL 不进入该 channel。

## 3. 原语模型

| 原语 | 定义 | 关键字段/职责 |
|---|---|---|
| **Master** | 流程引擎/导演，**不是角色** | 读 flow；编排 channel；与 KP 协商场景；触发 commit/tag；不扮演角色 |
| **Role（角色）** | 对称角色（GM/KP、PL、NPC） | `persona`（设定）、`context`（短期记忆）、`memory`（长期）、`sheet`（角色卡）、可用 `tools` |
| **Channel（频道）** | 有界的场景/交互 | `purpose`、`participants`、`termination`、`outcome`（纪要） |
| **Flow** | 阶段程序（跨模组复用） | 阶段列表 + 迁移条件 + 每阶段参与角色/适用规则；阶段粒度强制、阶段内自由 |
| **System（规则系统）** | 机制层 | 规则说明 + 工具绑定 + 默认 flow（如 `coc7e`） |
| **Module（模组）** | 剧情内容 | 场景/线索/NPC/`hooks`（对 flow 阶段的覆盖） |
| **Tool（工具）** | 确定性 CLI | 随机、状态变更、投影、压缩、git 步进、判定结算 |
| **World State（世界状态）** | 共享真相（剧情层） | 时间、地点、旗标、NPC 状态、线索发现情况 |

**关键原则**：

1. **Master 推进流程但不扮演角色**。master 是导演，负责定位阶段、编排频道、协商场景、落盘与打 tag；它不进入任何角色人格。
2. **角色对称**。GM/KP、PL、NPC 是地位完全相同的角色，各自拥有独立的 `persona`、上下文、记忆与工具。KP 不是特权角色，只是恰好承担主持叙事的角色之一。
3. **角色由 agent 或人类担任是可替换的**。前期全部由 agent 担任；协议预留人类担任的暂停/输入/恢复接口（见 [`capabilities.md`](./capabilities.md)）。

### 分层正交

协议将四类内容正交分层，互不污染：

```
rules（机制）   ← 判定如何结算
flow（阶段程序） ← 一场团分成哪些阶段、如何迁移（跨模组复用）
module（剧情内容）← 这个模组有什么场景/线索/NPC
characters（角色实例）← 本场团的 KP、PL、NPC 各自是谁
```

- **模组通过 `hooks` 覆盖 flow 的阶段，而不是改写 flow 本体**——这样 flow 可跨模组复用。
- 框架与内容无关：flow 是可替换内容，规则系统是可替换内容，自带 CoC 7e 作为示例。

## 4. 设计决策索引

| # | 决策 | 结论 |
|---|---|---|
| D1 | 编排层策略 | 宿主无关核心 + 后期原生适配 |
| D2 | 参与模型 | master 推进流程；GM/PL/NPC 对称；人类担任可替换（前期全 agent） |
| D3 | 框架与内容 | 框架内容无关；flow 是可替换内容；自带 CoC 示例 |
| D4 | 分层 | rules / flow（阶段粒度）/ module / characters 正交；模组 hooks 覆盖 flow |
| D5 | 项目与冒险目录 | 工具库/脚手架 → 生成自包含冒险目录；分发非目标 |
| D6 | 扩展模型 | 唯一不变量 = 自描述；其余完全可 fork；适配层只供能力 |
| D7 | 可见性与频道 | master 运行时编排 channel；保留公共基线；场景构成 = master↔KP 协商 |
| D8 | 规则确定性 | 随机+状态强制工具；判定结算规则工具；叙事裁决 agent；输出即真相 |
| D9 | 持久化 | 目录 + git；恢复 = checkout；每消息提交 + 边界 tag；工具串行 |
| D10 | 首份交付物 | `docs/` 正式文档 + 根 README（中文） |

## 5. 需求到文档的落点

| 需求 | 说明 | 落点 |
|---|---|---|
| R1 | 编译产物 = 自包含可运行冒险目录 | [`directory.md`](./directory.md)、[`tooling.md`](./tooling.md) |
| R2 | 宿主无关，可降级 | [`capabilities.md`](./capabilities.md) |
| R3 | rules / flow / module / characters 正交 | 本文件 §3、[`directory.md`](./directory.md) |
| R4 | 角色对称，master 不是角色 | 本文件 §3 |
| R5 | 频道化可见性 | [`visibility.md`](./visibility.md) |
| R6 | 场景由 master↔KP 协商 | 本文件 §2.2、[`visibility.md`](./visibility.md) |
| R7 | 规则确定性分层 | [`tooling.md`](./tooling.md) |
| R8 | 秘密隔离 | [`visibility.md`](./visibility.md) |
| R9 | 持久化与恢复 | [`tooling.md`](./tooling.md) |
| R10 | 记忆分层 | [`visibility.md`](./visibility.md) |
| R11 | 可 fork | [`directory.md`](./directory.md) |
| R12 | 适配层只供能力 | [`capabilities.md`](./capabilities.md) |
| R13 | 首份交付物为中文文档 | 本文件及 `docs/` 全部、根 `README.md` |
| R14 | 清理残留与旧实现 | 见下方「兼容与迁移」 |

## 6. 兼容与迁移

- 旧的 Python/LangGraph 实现已按 R14 **从工作树删除**，工作树仅保留 `modules/`（原始模组）与工程/agent 配置。
- 旧实现完整保留在 git 历史提交 `ed80ff4`、`2fc6819` 中，可随时 `git show` / `git checkout` 取回。
- 规则/判定/车卡/模组解析如何映射到新协议的清点表见任务研究文件
  `.trellis/tasks/10-02-trpg-agent-protocol/research/legacy-inventory.md`。
- 后续 `systems/coc7e/` 工具与编译期模组解析，可参考旧 `src/systems/coc/`、`src/module/reader.py`（从 git 历史取回）。
