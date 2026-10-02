# 可见性、秘密隔离与记忆

> 本文件定义频道化可见性、上下文投影、秘密隔离、记忆分层与压缩，以及内联降级模式的代价。
> 工具契约见 [`tooling.md`](./tooling.md)，宿主能力见 [`capabilities.md`](./capabilities.md)。

## 1. 频道（channel）

**可见性由 master 运行时编排的 `channel`（场景）实现，而非静态标签**（R5/D7）。

每个 channel 含**四要素**：

| 要素 | 含义 |
|---|---|
| `purpose` | 本频道的目标（如「车卡」「中央房间调查」） |
| `participants` | 参与本频道的角色（KP/PL/NPC） |
| `termination` | 终止条件（何时结束本频道） |
| `outcome` | 结束后的纪要（发生了什么、公开什么） |

channel 落盘于 `channels/<id>/`：

- `meta.json`：`purpose` / `participants` / `termination` / `status`。
- `transcript.md`：对话转录。

### 公共基线频道

始终保留一条**全员公共基线频道**。场景频道是建立在它之上的**叠加层（overlay）**：

- 场景频道结束后，master 将**应公开的 `outcome` publish 到公共基线频道**。
- 未公开的内容只留在该场景频道的 transcript 中，不进入未参与角色的上下文。

### 场景协商（R6）

场景由 master 依 flow/module **提议**、KP 按叙事**修订**、master **校验并开启**：

```
master 提议 {purpose, participants}  →  KP 修订  →  master 校验并开 channel
```

master 有**最终裁量权**。

## 2. 上下文投影

**隔离由文件位置 + 投影工具保证，不靠角色自律**（R8）。

```
tools/context build --role <id>
   # 读 channels 中该角色参与的 + world 中可见的 + 自身 memory
   # → 生成 roles/<id>/context.jsonl（可见层）
```

规则：

- 场景内容只存于 `channels/<id>/`；**未进入该 channel 的角色不会被喂到**。
- 角色/子代理**只读自己的 `context.jsonl`**：
  - 不读 `log/`；
  - 不读他人 `roles/`；
  - 不读全量 `channels/`。

即：**角色读到的只有自己的投影**，隔离由目录/文件位置保证，而非依赖角色「自觉不看」。

## 3. 秘密骰

- 秘密骰的点数由工具写入**受限位置**，**不进入公共 transcript**。
- 对外只发**「可公开的结果事件」**（例如「你感到一阵寒意，检定结果失败」，而非点数本身）。
- 因此不在该场景中的 PL，其上下文投影中**既不含场景内容，也不含秘密骰点数**（AC3 验证点）。

## 4. 记忆分层与压缩（R10）

| 层 | 位置 | 生命周期 |
|---|---|---|
| 短期 | `roles/<id>/context.jsonl` | 最近 N 轮，超出即压缩 |
| 摘要 | `roles/<id>/summary.md` | 场景级滚动摘要 |
| 长期 | `roles/<id>/memory.md` + `sheet.*` | 全场持久 |

- **短期上下文** = 实际发给 LLM 的 messages 数组。
- **滚动摘要** = 场景级摘要，承接被挤出短期窗口的内容。
- **长期笔记 + 卡面** = `memory.md`（关系/线索/秘密）与 `sheet.*`（角色卡），全场持久。

**压缩触发**：**场景结束时**由 master 触发 `context compact`，把短期溢出转为摘要并更新 `context.jsonl`，从而控制上下文体积、避免长跑团膨胀。

## 5. 可见性工作流摘要

```
【协商】master 提议 {purpose, participants} → KP 修订 → master 校验并开 channel
【运行】参与者子代理各自基于「自己的 context 投影」在 channel 中交互
【结束】master 判定 termination → 生成 channel outcome（纪要）
【同步】master 将应公开的 outcome publish 到公共基线频道
【记忆】context compact：短期溢出 → summary；更新各角色 memory/context
```

## 6. 降级模式及其已知代价

无子代理隔离能力时，master 在**同上下文内联扮演**所有角色，隔离退化为**「可见性纪律」**：

- 文件位置与投影**仍然生效**（`context build` 照常产出），但所有角色共享同一 LLM 上下文，理论上可能泄漏。
- 这是**已知代价**：缺能力不得阻止一场团跑通，仅影响隔离强度（AC5）。
- 缓解建议：**优先使用具备 `spawn-subagent` 能力的宿主**。能力矩阵见 [`capabilities.md`](./capabilities.md)。

## 7. 兼容与迁移

- 旧实现的 GM/PL 回合逻辑（`src/systems/coc/gm.py` / `pl.py`）以硬编码流程驱动；新协议改由 master 编排 channel、角色读各自 `context.jsonl`。
- 旧 `src/game/engine.py` 的状态机 `load_module → gm ↔ pl → log` 由 `flow/` 阶段程序 + master 取代；日志拆入 `channels/` 与 `log/`。
- 完整映射见 `.trellis/tasks/10-02-trpg-agent-protocol/research/legacy-inventory.md`。
