# I2 design — 工具与脚手架技术设计

> 依据 `docs/tooling.md` / `docs/directory.md` / 父任务 `design.md`。I2 只实现**通用**工具。

## 1. 工具框架

- **位置**：框架 `tools/`（模板源）→ 脚手架复制进每个冒险目录的 `<adventure>/tools/`。
- **形态**：每个工具一个 PEP 723 单文件脚本：

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
```

- **共享库**：`tools/_lib.py`（同目录，`import _lib` 可用；`uv run` 与 `python3` 均把脚本目录置于 `sys.path[0]`）。
  - 提供：冒险目录定位（`--adventure` 或向上查找 `AGENTS.md`）、JSON 输出、`log/events.jsonl` 追加、git 串行锁、时间戳/seed 工具。
- **CLI 约定**：`argparse` 子命令；成功退出码 `0`，用法错误 `2`，业务失败 `1`；`--help` 必须完整。

## 2. 数据格式

| 文件 | 格式 | 说明 |
|---|---|---|
| `world/state.json` | JSON object | I2 用单文件世界状态；`state set` 覆盖键，`state get` 读取 |
| `world/visibility.json` | JSON | 世界状态可见性 mask：`{default, rules:[{pattern,audience}]}` |
| `log/events.jsonl` | JSONL，append-only | 每次工具调用一条：`{ts, tool, args, result, sideEffects}` |
| `roles/<id>/context.jsonl` | JSONL | 投影出的可见上下文（messages 数组形态） |
| `roles/<id>/summary.md` | Markdown | 滚动摘要 |
| `channels/<id>/meta.json` | JSON | `purpose / participants / termination / status` |
| `channels/<id>/transcript.md` | Markdown | 场景转录 |

## 3. 各工具设计

### `dice roll`
- `--expr 1d100 --seed <int> [--count N]`；用 `random.Random(seed)` 保证可复现。
- 输出 `{rolls, total, seed, expr}`；写 `log/`。
- 支持 CoC 常用：`1d100`、`NdM`、`NdM+mod`。

### `state get/set/mask`
- `state get <key>` / `state set <key> <value>`（value 解析 JSON，回退字符串）。
- `state mask --role <id>`：打印该角色对 `world/state.json` 的可见 / 隐藏路径（可审计）。
- 读写 `world/state.json`；写 `log/`。
- **角色不得直接调用 `state get`**；只读 `context build` 产出的投影。

### World State mask 过滤（安全关键）
- `world/visibility.json` 形式：
  ```json
  { "default": "public",
    "rules": [ { "pattern": "/secrets/**", "audience": ["kp"] } ] }
  ```
- 算法（`_lib.py`，纯 stdlib）：遍历 `state.json` 叶子路径 → 按 `rules` **首个命中**定档，未命中用 `default` → `role ∈ audience` 才保留 → 组装投影 JSON。
- `pattern`：JSON 路径 glob，`*` = 一层，`**` = 子树。
- 不使用 jq；mask 是数据不是程序，可枚举、可断言。

### `context build`
- `--role <id>`：读取
  - `channels/*/meta.json` 中 `participants` 含该 role 的频道 → 其 `transcript.md`
  - `world/state.json` **按 `world/visibility.json` mask 过滤后**的可见部分
  - `roles/<id>/{persona.md,memory.md,summary.md}`
- 生成 `roles/<id>/context.jsonl`（可见层）；**不含**该角色未参与的频道；**不读** `log/`、他人 `roles/`。
- 这是安全关键路径：必须按 participants 与 world mask 过滤，不允许「读全量 channels/state」。

### `context compact`
- `--role <id> [--keep N]`：把 `context.jsonl` 超出最近 N 条的部分摘要进 `summary.md`，并截断 `context.jsonl`。
- 摘要生成在 I2 先做**确定性占位**（如结构化拼接）；LLM 摘要由 play-time 的 master/agent 调用来填（I3 或后续）。I2 保证机制与文件契约可用。

### `step commit` / `step tag`
- `step commit --message "..." [--all]`：`git add -A` + `git commit`；无变更则安全跳过。
- `step tag <name>`：`git tag <name>`。
- **串行化**：用 `<adventure>/.git/trpg.lock`（`flock`/独占创建）包住 git 操作，避免并发 `index.lock`。

## 4. 脚手架 `scaffold new`

- 命令：`uv run tools/scaffold.py new --module <path> --out <dir> [--name <slug>]`。
- 步骤：
  1. 复制 `templates/adventure/` 骨架到 `--out`（含 `tools/`、`AGENTS.md` 模板、空 `roles/ channels/ world/ log/`）。
  2. 解析模组 markdown：按 `#` 标题分段（参考旧 `src/module/reader.py` 思路）。
     - 摘要/大纲 → `module/overview.md`
     - 每个场景小节 → `module/scenes/<slug>.md`
     - 线索（含「判定/线索/发现」等）→ `module/clues.md`
     - NPC 小节 → `module/npcs/<slug>.md`
     - 模组特例（计时/特殊规则）→ `module/hooks.md`
  3. 渲染 `AGENTS.md`：填入模组名、目录结构、工具用法、推进方式（自描述）。
  4. `git init` + 首次提交（经 `step commit`）。
- 解析规则保持**通用**（基于 markdown 结构），CoC 特有语义留待 I3 的 `systems/coc7e` 增强。

## 5. 模板 `templates/adventure/`

```
templates/adventure/
├─ AGENTS.md            # 模板（含占位符，scaffold 渲染）
├─ flow/README.md       # 占位，I3 填充 CoC 默认 flow
├─ rules/README.md
├─ module/              # 由 scaffold 填充
├─ roles/.gitkeep
├─ channels/.gitkeep
├─ world/state.json     # 初始 {}
├─ world/visibility.json # 初始 {"default":"public","rules":[]}
├─ log/.gitkeep
└─ tools/               # I2 工具副本（dice/state/context/step + _lib）
```

## 6. 风险与权衡

| 风险 | 缓解 |
|---|---|
| `context build` 泄密 | 严格按 participants 过滤；AC1.4 断言未参与频道不出现；不读 log/ 与他人 roles/ |
| 并发 git 锁 | `trpg.lock` 串行化；AC1.5 并发测试 |
| `python3` 与 `uv run` 行为差异 | 纯标准库 + 相同 `sys.path` 假设；AC1.1 两路都验 |
| 模组解析质量参差 | I2 只保证结构产出（AC1.6）；语义增强留 I3 |
| 摘要质量 | I2 用确定性占位，契约先立；质量优化后置 |

## 7. 与 I3 的接口

- I3 在 `systems/coc7e/` 提供 `check resolve`，并在 `scaffold` 时装入冒险目录 `tools/`。
- I2 的 `flow/` 为空占位；I3 提供 CoC 默认 flow。
- I2 保证 `context build` / `step *` / `state` 可直接被 I3 的 play-time 流程复用。
