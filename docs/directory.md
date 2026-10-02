# 目录契约

> 本文件定义**框架仓库**与**冒险目录**的结构、必需/可选文件，以及唯一硬性不变量。
> 原语定义见 [`protocol.md`](./protocol.md)，工具落盘位置见 [`tooling.md`](./tooling.md)。

## 1. 两类目录

协议只有两类目录：

- **框架仓库**（TrpgWorld 项目本身）：工具库 + 脚手架 + 模板 + 规则 + 示例，**不持有任何游戏实例**。
- **冒险目录**（编译产物）：每份模组一个，**自包含、自描述、自运行、git 管理**。

适配层（Pi/dsh 插件）不属于这两者，它是宿主侧的能力提供者（见 [`capabilities.md`](./capabilities.md)）。

## 2. 框架仓库结构（推荐默认，可 fork）

```
TrpgWorld/
├─ README.md                 # 中文简介（首份交付物之一）
├─ docs/                     # 中文正式协议文档（首份交付物）
│   ├─ protocol.md           #   协议总览：原语、生命周期
│   ├─ directory.md          #   目录契约：框架与冒险目录结构（本文件）
│   ├─ tooling.md            #   工具 CLI 契约 + git 步进契约
│   ├─ visibility.md         #   可见性/秘密隔离/上下文投影
│   └─ capabilities.md       #   宿主能力声明与降级
├─ tools/                    # 确定性 CLI 工具（模板源）
├─ templates/adventure/      # 冒险目录脚手架模板（含 AGENTS.md 模板）
├─ systems/coc7e/            # 规则系统：规则说明 + 默认 flow + 判定工具
├─ examples/soup/            # 示例：由 soup.md 编译出的冒险目录
├─ modules/                  # 原始模组输入（如 soup.md、example.md）
└─ adapters/                 # （后期）Pi/dsh 能力提供者，非本阶段
```

| 目录 | 职责 |
|---|---|
| `docs/` | 协议文档，供 agent 与人类阅读 |
| `tools/` | 确定性 CLI 工具的实现，也是冒险目录内嵌工具的模板源 |
| `templates/adventure/` | 冒险目录骨架模板，`scaffold new` 依此生成 |
| `systems/coc7e/` | 一个规则系统示例：规则说明 + 默认 flow + 判定工具 |
| `examples/soup/` | 一份编译完成的冒险目录示例（PoC） |
| `modules/` | 原始模组输入，编译的起点 |
| `adapters/` | 后期宿主能力提供者，本阶段不实现 |

> 以上结构是**推荐默认**，可整体 fork 改造。框架仓库中除「`docs/` 描述协议」外没有其它硬性不变量。

## 3. 冒险目录结构（编译产物）

```
<adventure>/
├─ AGENTS.md            # 【必需·唯一不变量】自描述入口：如何读本目录、如何推进
├─ flow/                # 阶段程序（来自 system，可按本模组微调）
├─ rules/               # 规则（从框架带入并裁剪）
├─ module/              # 编译后的模组内容
│   ├─ overview.md      #   模组总览
│   ├─ scenes/          #   拆分后的场景
│   ├─ clues.md         #   线索
│   ├─ npcs/            #   NPC 设定
│   └─ hooks.md         #   对 flow 阶段的钩子/覆盖（如毒湯 1 小时倒计时）
├─ roles/<id>/          # 角色（记忆层）
│   ├─ persona.md       #   角色设定
│   ├─ context.jsonl    #   短期记忆（实际发给 LLM 的 messages 数组）
│   ├─ summary.md       #   滚动摘要
│   ├─ memory.md        #   长期笔记（关系/线索/秘密）
│   └─ sheet.*          #   角色卡
├─ channels/<id>/       # 场景记录（可见层）
│   ├─ meta.json        #   purpose / participants / termination / status
│   └─ transcript.md    #   对话转录
├─ world/               # 共享世界状态（真相层）
├─ log/                 # 系统事件审计（工具调用/状态变更/提交；角色不可见，不用于恢复）
├─ tools/               # 内嵌的确定性工具（可 fork）
└─ .git/                # 历史 / tag / 恢复 / 分叉
```

### 3.1 必需与可选

| 路径 | 必需性 | 说明 |
|---|---|---|
| `AGENTS.md` | **必需** | 自描述入口；唯一硬性不变量 |
| `module/` | 必需 | 模组内容，无它则无剧情 |
| `roles/` | 必需 | 至少含 KP 与 PL 的角色实例 |
| `channels/` | 必需 | 场景/交互记录 |
| `world/` | 必需 | 共享真相层 |
| `tools/` | 必需 | 内嵌确定性工具 |
| `.git/` | 必需 | 历史、tag、恢复、分叉 |
| `flow/` | 必需 | 阶段程序；来自 system，可按本模组微调 |
| `rules/` | 可选 | 规则裁剪结果；可按需省略，由 system 提供 |
| `summary.md`（角色级） | 可选 | 滚动摘要，无长跑团时可缺省 |
| `log/` | 可选 | 审计，仅供排查，不参与恢复 |

> **可省略**：`summary.md`、`log/`、`rules/` 可按需。
> **不可省略**：`AGENTS.md`（自描述入口）。

### 3.2 `AGENTS.md`——唯一硬性不变量

整个协议**唯一**强制的不变量是：**冒险目录自描述**。

- `AGENTS.md` 必须让任意 agent 读懂：本目录是什么、有哪些子目录、如何定位当前阶段、如何推进到结团、工具怎么调用、秘密如何隔离。
- 只要 `AGENTS.md` 足够自描述，**其余一切完全可 fork**：目录可增删改、工具可重写、flow 可替换、结构可调整。
- 编译的最后一步就是把 `AGENTS.md` 写清楚，并用 `tools/step commit --tag compile/<module>` 落盘（见 [`tooling.md`](./tooling.md)）。

### 3.3 分层正交的落点

| 层 | 目录/文件 | 职责 |
|---|---|---|
| `rules`（机制） | `rules/`、`systems/coc7e/` | 判定如何结算 |
| `flow`（阶段程序） | `flow/` | 一场团分成哪些阶段、如何迁移 |
| `module`（剧情内容） | `module/` | 本模组的场景/线索/NPC |
| `characters`（角色实例） | `roles/<id>/` | 本场的 KP、PL、NPC |

模组通过 `module/hooks.md` **覆盖** `flow/` 的个别阶段，而不改写 `flow/` 本体，从而让 flow 跨模组复用。

## 4. 编译如何填充目录

1. `scaffold new` 由 `templates/adventure/` 生成骨架并 `git init`。
2. 解析原始模组：`module/scenes/`、`module/clues.md`、`module/npcs/`、`module/hooks.md`。
3. 带入 `systems/coc7e/` 的默认 `flow/` 与 `rules/`。
4. 按模组特性用 `hooks.md` 覆盖个别阶段，并可增删目录/文件、改造工具。
5. 初始化 `roles/`（KP/PL/NPC）、`channels/`（含公共基线频道）、`world/`。
6. 生成自描述的 `AGENTS.md`。
7. `tools/step commit --tag compile/<module>` 落盘初始提交。

## 5. 兼容与迁移

- 旧 Python 实现的目录（`src/`、`main.py`、`tests/` 等）已按 R14 从工作树删除；其映射去向见
  `.trellis/tasks/10-02-trpg-agent-protocol/research/legacy-inventory.md`。
- 旧实现保留在 git 历史 `ed80ff4`、`2fc6819` 中，可用 `git show ed80ff4:<path>` 取回。
- 工作树仅保留 `modules/soup.md`、`modules/example.md` 作为示例编译输入。
