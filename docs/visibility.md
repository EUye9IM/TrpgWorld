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

- 公共基线频道的 `participants` 用**全员哨兵** `["*"]` 表示（也接受 `"public"`），意为所有角色均可读。
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
- `context build` 为判定参与关系会枚举 `channels/*/meta.json`，但**只读取该角色参与的频道的 `transcript.md`**，绝不读未参与频道的 transcript。
- 角色/子代理**只读自己的 `context.jsonl`**：
  - 不读 `log/`；
  - 不读他人 `roles/`；
  - 不读全量 `channels/`。

即：**角色读到的只有自己的投影**，隔离由目录/文件位置保证，而非依赖角色「自觉不看」。

### 2.1 World State 的可见性（mask）

World State 是共享真相，但**并非全部公开**——《毒湯》里「汤是人血」、NPC 真实身份都属于知道但 PL 不该知道的秘密。用**声明式 mask** 表达，而不是把秘密拆成多个文件（文件拆分只是它的特例）。

- `world/state.json`：全部世界事实（唯一真相，结构化 JSON）。
- `world/visibility.json`：可见性 mask（声明式，不用 jq 程序）。

```json
{
  "default": "public",
  "rules": [
    { "pattern": "/secrets/**",             "audience": ["kp"] },
    { "pattern": "/npcs/*/true_identity",   "audience": ["kp"] },
    { "pattern": "/timer/remaining_minutes", "audience": ["kp"] }
  ]
}
```

- `pattern`：JSON 路径 glob，`*` = 一层，`**` = 子树（`**` 可匹配零层，因此 `/secrets/**` 同样覆盖 `/secrets`）。
- `default`：未命中任何规则时的默认受众。取 `"public"` 表示所有人可见；取 role 列表则仅列表内角色可见；取其他值/名单外角色一律**隐藏（fail-closed）**。
- `audience`：可见的 role 列表；未命中任何规则则用 `default`。
- **过滤算法**（在 `tools/context build` 内，纯标准库）：遍历 `state.json` 叶子路径 → 按 `rules` 首个命中定档 → `role ∈ audience` 才保留 → 组装投影 JSON。
- **可审计**：`tools/state mask --role <id>` 打印该角色可见 / 隐藏的路径。
- **强制点**：角色**不得**直接调用 `state get` 读原始 `state.json`；只能读 `context build` 产出的投影。`state get/set` 仅给 master / 系统工具（依赖 `tool-gating` 能力，缺则降级为纪律，见 [`capabilities.md`](./capabilities.md)）。
- **role id 安全**：`--role` 必须是安全 id（不含 `/`、`\`、`..`、空/控制字符），由工具校验；否则退出码 2，防止路径穿越读写 `roles/` 之外的文件。

> **为什么不用 jq**：jq 是一段任意程序，遮不住「到底藏了哪些字段」、难审计、且引入依赖。声明式 mask 是数据、可枚举、可断言（AC3/AC1.4），与「隔离靠机制不靠自律」一致。如确需任意过滤，可作为 agent fork 的高级覆盖，非默认。

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
