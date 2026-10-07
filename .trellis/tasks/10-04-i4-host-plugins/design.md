# I4 design — 宿主插件：角色运行时契约 v2 + 最小 Pi 插件

> 依据：`research/plugin-capability-review.md`（批判性审查）、`docs/`、父任务 design。
> 范围：**契约文档 v2 + 最小 Pi 插件**；机制化隔离与 C11–C17 **预留**。

## 1. 契约 v2（写入 `docs/capabilities.md`）

从「能力矩阵」升级为**角色运行时契约**：

### 1.1 三层隔离模型

```
Layer A 上下文注入面（context surface）
  - 关闭工作区 AGENTS.md/CLAUDE.md 自动加载
  - 关闭用户/项目扩展、skills、prompt 模板、MCP
  - 整体替换 system prompt（不是 append）
  - 使用干净配置目录（预留：Pi PI_CODING_AGENT_DIR）
Layer B 工具门控（tool gating）
  - 默认拒绝；allow = {trpg_dice}（角色侧封闭集，后续加 check/role_read）
  - 显式 deny：read/grep/find/ls/bash/edit/write/web/subagent/skill/todo/codemode
Layer C 会话/进程边界（session）
  - ephemeral（--no-session）；每回合 fresh（默认）
  - 递归上限 = 0（角色不得再 spawn）
```

### 1.2 能力表 C1–C17（标注实现状态）

| # | 能力 | 状态 |
|---|---|---|
| C1 `spawn_role({role_id, channel_id?, instruction?, route?, timeout?}) → {reply,...}` | 本任务实现（简化版） |
| C2 `tool_policy`（默认拒绝 + allowlist） | 本任务实现（`--tools trpg_dice`） |
| C3 `exec_tool(name,args)` 封闭集 `{dice}` | 本任务实现 |
| C4 `session_policy` fresh + ephemeral | 本任务实现 |
| C6 `notify/stream` | 预留 |
| C8 `capability_report`（含隔离不变量自证） | 预留 |
| C9 `context_isolation`（A+B+C；声明 L10 边界） | **本任务实现 A/B/C 的免费部分**，金丝雀预留 |
| C10 宿主原生工具审计 | 预留 |
| C11 每角色模型路由 | 预留 |
| C12 超时/中断/错误契约 | 预留 |
| C13 token/成本上限 | 预留 |
| C14 递归上限=0 | 本任务实现（不给 subagent 工具） |
| C15 受限读取（rules/） | 预留（临时：把授权规则纳入投影或由 master 在 instruction 里给） |
| C16 频道绑定 + 转录回写归属 | 本任务定义：**插件只返回 reply，master 负责写入 transcript** |
| C17 金丝雀隔离测试 | 预留 |

### 1.3 已知边界（必须写进文档）
- **L10 模型先验知识无解**：机制只能保证「没注入的看不到」，不能阻止模型本来就知道（如毒湯是知名谜题）。
- **prompt 约束为临时**：本版隔离 = 注入面洁净（免费 flags）+ 无 fs/bash；金丝雀验收延后。

## 2. 最小 Pi 插件

### 2.1 文件
```
.pi/extensions/trpg/index.ts     # 扩展：注册 trpg_role / trpg_dice
.pi/agents/trpg-role.md          # 角色子代理人格模板（说明：只依据给定上下文）
```
并在 `.pi/settings.json` 的 `extensions` 注册 `./extensions/trpg/index.ts`。

### 2.2 `trpg_role`
参数：`{ role_id: string, channel_id?: string, instruction?: string, model?: string, thinking?: string }`

执行：
1. 解析冒险目录（`--adventure` 配置或向上找 `AGENTS.md`）。
2. `spawnSync(uv|python3, [tools/context.py, build, --role, <id>, --adventure, <dir>])` → 生成并读取 `roles/<id>/context.jsonl`（**投影唯一来源，不自行过滤**）。
3. 组装 system prompt：
   - `roles/<id>/persona.md`（人格）
   - 固定协议说明（「你只知道以下内容；不得访问其它数据；需要随机数用 trpg_dice」）
   - 该角色投影 + 频道现状摘要
4. spawn 子 `pi`：
   ```
   pi --mode json -p --no-session --no-context-files \
      --no-extensions --no-skills --no-prompt-templates \
      --no-builtin-tools --tools trpg_dice \
      -e <this-file> \
      --system-prompt <prompt>
   ```
   （`--no-extensions` 关闭发现，但显式 `-e` 仍加载本扩展，供子代理拿 `trpg_dice`）
5. 解析 `--mode json` 事件流取最终回复。
6. 返回 `{ role_id, reply, stop_reason }`；**不写文件**（由 master 落盘 transcript）。

### 2.3 `trpg_dice`
参数：`{ expr: string, seed?: number, count?: number }` → 转调 `uv run tools/dice.py roll ...`，返回 JSON 结果。这是**角色唯一被允许的能力**。

### 2.4 可测试性钩子
- 子 `pi` 命令可被环境变量覆盖（如 `TRPG_PI_CMD`）→ 测试时指向 **fake agent**（记录收到的 argv 与 stdin/prompt 并回显固定回复）。
- `TRPG_DEBUG=1` 时把「构造好的 prompt + argv」写到临时文件，供断言。

## 3. 验证

- **可确定性断言（fake agent）**：投影来自 `context build`、只含该角色内容；argv 含 `--no-session/--no-context-files/--no-builtin-tools --tools trpg_dice`；未给 fs/bash。
- **手动/真实**：`pi -e .pi/extensions/trpg/index.ts` 加载扩展，调用 `trpg_role` 跑一次真实角色回合。
- **回归**：协议 core 不被修改。

## 4. 风险与权衡

| 风险 | 说明 | 缓解 |
|---|---|---|
| prompt 约束是自律 | 本版隔离弱于机制化 | 文档明确标注「临时」+ 预留金丝雀 |
| Pi 旗标语义随版本变化 | 升级可能破坏 | 预留 capability_report/自证 |
| 子代理仍需 `-e` 加载扩展 | 否则没有 `trpg_dice` | argv 集中构造 + 断言 |
| `context build` 现存缺陷（F1–F3） | 会直接影响投影正确性 | **先做 I5 修复** |
| 模型先验剧透（L10） | 无机制解 | 文档声明边界 |

## 5. 依赖顺序

**I5（core 缺陷 F1–F4）应先于 I4 实现**——插件依赖 `context build` 的正确性与 fail-closed mask。
