# 工具 CLI 契约与 git 步进

> 本文件定义所有确定性工具的命令契约，以及 git 步进/恢复/回滚语义。
> 原语与工作流见 [`protocol.md`](./protocol.md)，可见性投影见 [`visibility.md`](./visibility.md)。

## 1. 总则

所有工具都是**宿主无关 CLI**，统一约定：

```
参数 / 标准输入  →  标准输出（JSON）  +  文件写入  +  审计写入
```

三条不可违逆的约定：

1. **工具输出即真相**（R7/D8）。判定结果、随机点数、状态变更以工具输出为准，任何 agent 的叙事不得覆盖工具输出。
2. **每次调用记录到 `log/`**。工具调用、状态变更、提交都写入冒险目录的 `log/`，供审计与排查。
3. **git 操作只由 `step *` 串行执行**。所有 `git add/commit/tag` 只经由 `step commit` / `step tag`，避免多 channel 并发导致的 `index.lock` 竞争。

### 实现约定：PEP 723 单文件脚本

所有工具实现为带 **PEP 723 内联元数据** 的 Python 单文件脚本，用 `uv run` 执行：

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
```

- `uv run tools/<tool>.py <args>` 按内联元数据临时解析依赖，**无需 venv / pyproject / 安装**，环境隔离、可复现。
- **优先 `dependencies = []`（纯标准库）**：此时无 uv 也可用 `python3 tools/<tool>.py` 直接运行，最大化宿主无关性；确需三方库时才填 `dependencies`，此后运行依赖 `uv`。
- 每个工具的 `--help` 必须说明：输入、输出（JSON）、副作用（写 `world/`、`log/`、git）与退出码。
- 工具随冒险目录一起内嵌并可被 fork；`uv` 是运行前提之一，须写入 `AGENTS.md` 模板。

### 规则确定性分层（R7/D8）

| 层次 | 由谁负责 | 说明 |
|---|---|---|
| 随机源 | **工具**（强制） | 带种子，可复现；agent 不得自造随机数 |
| 状态变更 | **工具**（强制） | 世界状态只经 `state set` 修改 |
| 判定结算 | **规则工具**（可 fork） | `check resolve` 给出成功等级/对抗/SAN（理智）/伤害 |
| 叙事裁决 | **agent** | 描述发生了什么、如何叙述，由角色做决定 |
| 真相 | **工具输出** | 最终以工具结果为准 |

## 2. 工具清单

| 工具 | 职责 | 副作用 |
|---|---|---|
| `dice roll` | 带种子的随机源（可复现） | 写 `log/`，返回结果 |
| `check resolve` | CoC 判定结算（成功等级/对抗/SAN/伤害） | 写 `log/` |
| `state get/set/mask` | 读写 `world/` 共享状态；打印可见性 mask | 写 `world/`、`log/` |
| `context build` | 由 channel/world（按 mask）/memory 投影角色可见上下文 | 写 `roles/<id>/context.jsonl` |
| `context compact` | 短期溢出 → 摘要 | 写 `summary.md`、更新 `context.jsonl` |
| `step commit` | git add/commit（串行） | git 提交 |
| `step tag` | 打边界 tag | git tag |
| `scaffold new` | 由模板生成冒险目录骨架（build-time） | 创建目录、`git init` |

## 3. 各工具契约

### `dice roll`

- **输入**：骰式（如 `1d100`、`2d6+3`）、`--seed <n>`（可选，缺省用注入的确定性种子）。
- **输出**：JSON，含总点数、各骰面、所用种子。
- **副作用**：写 `log/`；**秘密骰的点数写入受限位置，不进入公共 transcript**（见 [`visibility.md`](./visibility.md) §4）。

### `check resolve`

- **输入**：判定类型（技能/属性/对抗/SAN/伤害）、目标值、调整值、骰点或骰式。
- **输出**：JSON，含成功等级（大成功/极难/困难/常规成功/失败/大失败）、是否对抗成功、SAN 损失、伤害。
- **副作用**：写 `log/`。
- **说明**：本题为**规则工具**，属可 fork 内容（换规则系统即换实现）。

### `state get/set/mask`

- **输入**：`state get <key>`、`state set <key> <value>`、`state mask --role <id>`。
- **输出**：JSON；`mask` 打印该角色可见 / 隐藏的路径（可审计）。
- **副作用**：`set` 写 `world/` 与 `log/`。
- **说明**：世界状态（时间、地点、旗标、NPC 状态、线索发现情况）**只经此工具修改**。可见性由 `world/visibility.json` 的声明式 mask 控制；**角色不得直接调用 `state get`**，只能读 `context build` 的投影（见 [`visibility.md`](./visibility.md) §2.1）。

### `context build`

- **输入**：`--role <id>`。
- **行为**：读该角色参与的 `channels/`、`world/state.json` 中按 `world/visibility.json` **mask 对其可见**的部分、以及自身 `roles/<id>/memory.md` 与 `sheet.*`。
- **输出**：JSON 摘要。
- **副作用**：生成 `roles/<id>/context.jsonl`——**角色的可见层**。
- **安全性**：这是**安全关键路径**，做成确定性工具，并由 AC3 验证「不在 channel 中的 PL 投影不含该场景内容、秘密骰点数不出现在投影中」。

### `context compact`

- **输入**：`--role <id>`（可选 `--keep <n>` 保留最近 n 轮）。
- **行为**：短期记忆溢出时，将较早内容压缩为摘要。
- **副作用**：写 `roles/<id>/summary.md`，并裁剪更新 `roles/<id>/context.jsonl`。
- **触发**：场景结束时由 master 触发（见 [`visibility.md`](./visibility.md) §5）。

### `step commit`

- **输入**：`--message <msg>`、可选 `--tag <name>`。
- **行为**：串行执行 `git add -A && git commit`；带 `--tag` 时同时打 tag。
- **副作用**：git 提交（可能附带 tag）。
- **粒度**：**每条消息/每步一次提交**。

### `step tag`

- **输入**：`--name <tag>`。
- **行为**：串行执行 `git tag`。
- **副作用**：git tag。
- **用途**：标记场景与 flow 阶段的**边界**，如 `scene/003-central-room`、`phase/combat`、`compile/<module>`。

### `scaffold new`

- **输入**：`--template adventure --out <dir>`。
- **行为**：由 `templates/adventure/` 生成冒险目录骨架，并 `git init`。
- **副作用**：创建目录、初始化 git。
- **阶段**：仅 build-time 使用。

## 4. git 步进契约（R9/D9）

- **真相 = 冒险目录的工作树**；**历史 = git 提交**。
- **提交粒度 = 每条消息/每步**；**边界 tag** 标记场景与 flow 阶段。
- **结构化 commit message** 便于在大量细粒度提交中导航（缓解「每消息提交噪音」风险）。

### 恢复

```
恢复 = git checkout <commit> 后继续
```

- **不重放 `log/`**；`log/` 仅供审计，**不参与恢复**。

### 回滚语义

| 场景 | 操作 | 说明 |
|---|---|---|
| A1 撤销 | `git reset --hard <commit>` | 默认回滚方式 |
| A2 分叉 | `git branch <new-timeline> <commit>` | 旧时间线保留，git 原生支持，零额外代码 |

### 性能优化

- 本地环境可接受 `core.fsyncObjectFiles=false`。
- 定期 `git gc` 收缩仓库。

### 为什么必须串行

多个 channel 可能并发产生写入；若各自直接调用 git，会争用 `index.lock`。因此**所有 git 操作统一由 `step *` 串行执行**。

## 5. 兼容与迁移

- 旧实现的判定/骰子逻辑（`src/systems/coc/dice.py`、`skills.py`、`rules.py`）可作 `tools/dice` 与 `tools/check` 的参考实现，从 git 历史取回。
- 旧 `src/game/log.py` 的会话日志落盘职责，由新的 `channels/`（对话转录）+ `log/`（审计）分担。
- 完整映射见 `.trellis/tasks/10-02-trpg-agent-protocol/research/legacy-inventory.md`。
