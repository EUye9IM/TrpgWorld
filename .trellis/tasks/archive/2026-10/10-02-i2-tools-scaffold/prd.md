# I2: 确定性工具与冒险目录脚手架

## Goal

实现 TrpgWorld 的**通用确定性工具**与**冒险目录脚手架**，让「原始模组 → 冒险目录」这条编译链可用，并为 I3 的规则系统与端到端跑团提供地基。验收 AC1。

## Background

- 权威依据：`docs/tooling.md`（工具契约 + PEP 723 约定）、`docs/directory.md`（目录契约）、`docs/visibility.md`（投影）、父任务 `design.md`。
- 父任务 I1 已完成（协议文档就绪）。
- 实现约定（D8 + docs/tooling.md）：PEP 723 单文件 Python，`uv run` 执行，优先 `dependencies = []`。

## 范围界定

- **本任务（I2）**：通用工具 + 脚手架模板 + `scaffold new` 编译流程。
- **不属于 I2**：`check resolve`（CoC 判定结算）由**规则系统** `systems/coc7e` 提供，属 I3；CoC 规则/flow 属 I3；端到端跑团属 I3；宿主适配插件不在本阶段。

## Requirements

- **R1 工具实现约定**：每个工具为 PEP 723 内联元数据的 Python 单文件脚本；`uv run tools/<tool>.py` 可执行；优先纯标准库（无 uv 时 `python3` 亦可运行）。
- **R2 通用工具集**：
  - `dice roll`：带种子的随机源；同 seed 同结果。
  - `state get/set`：读写世界状态（`world/state.json`）。
  - `state mask`：读取 `world/visibility.json`，打印指定角色可见/隐藏的路径（可审计）。
  - `context build`：按可见性（channel participants + world mask）投影生成 `roles/<id>/context.jsonl`。
  - `context compact`：短期溢出压缩进 `roles/<id>/summary.md`。
  - `step commit`：串行 `git add/commit`。
  - `step tag`：串行打边界 tag。
- **R3 工具契约**：标准输出为 JSON；退出码语义明确；`--help` 说明输入/输出/副作用/退出码；以 `--adventure <path>`（或当前目录）定位冒险目录。
- **R4 审计**：每次工具调用追加写入 `log/`（如 `log/events.jsonl`）。
- **R5 git 串行**：`step commit` / `step tag` 是唯一 git 入口；需避免并发 `index.lock`。
- **R6 脚手架模板** `templates/adventure/`：目录骨架 + `AGENTS.md` 模板 + 内嵌 `tools/`。
- **R7 `scaffold new`**：输入原始模组（markdown），生成冒险目录：拆分场景/线索/NPC/hooks → `module/`；放置 `flow/`、`rules/`、`roles/`、`channels/`、`world/`、`log/`、`tools/`；生成 `AGENTS.md`；`git init` 并首次提交。
- **R8 可 fork / 内嵌**：工具随冒险目录内嵌并可被 agent 二次开发；框架 `tools/` 为模板源。
- **R9 自描述**：产物满足「唯一不变量」——`AGENTS.md` 足以让任意 agent 读懂并运行。
- **R10 World State 可见性 mask**：单文件 `world/state.json`（全部事实）+ 声明式 `world/visibility.json`（`default` + `rules[{pattern, audience}]`，JSON 路径 glob，`*` 一层、`**` 子树）；`context build` 按 mask 过滤世界状态（首个命中定档，否则 default；`role ∈ audience` 才保留）；**不使用 jq**；角色不得直接 `state get`，只能读投影。

## Acceptance Criteria

- [ ] **AC1.1** 所有 I2 工具均可 `uv run <tool>.py --help` 运行并打印完整用法（输入/输出/副作用/退出码）。
- [ ] **AC1.2** `dice roll` 固定 `--seed` 时多次运行结果完全一致。
- [ ] **AC1.3** `state set k v` 后 `state get k` 往返一致，且 `world/` 落盘。
- [ ] **AC1.4** `context build --role <id>` 生成的 `context.jsonl` 只含该角色可见内容（不含其未参与的 channel）；`context compact` 更新 `summary.md`。
- [ ] **AC1.5** `step commit` 产生 git 提交、`step tag` 产生 tag；并发调用不出现 `index.lock` 失败。
- [ ] **AC1.6** `scaffold new` 对 `modules/soup.md` 生成冒险目录，含 `AGENTS.md`、`flow/`、`module/{overview.md,scenes/,clues.md,npcs/,hooks.md}`、`roles/`、`channels/`、`world/`、`log/`、`tools/`、`.git`。
- [ ] **AC1.7** 每次工具调用在 `log/` 留有记录。
- [ ] **AC1.8** 对生成目录，仅凭 `AGENTS.md` 即可理解如何运行与推进（人工评估自描述性）。
- [ ] **AC1.9** `world/visibility.json` 生效：`state mask --role <id>` 能列出可见/隐藏路径；`context build --role <pl>` 的投影不含 mask 判定为 `kp`-only 的字段（如 `/secrets/**`），而 `--role kp` 含。

## Out of Scope

- `check resolve` 判定结算与 CoC 规则数据（I3，`systems/coc7e`）。
- CoC 默认 flow（车卡/扮演/战斗/结团）（I3）。
- `examples/soup` 端到端跑团验证（I3，AC2–AC5）。
- 宿主适配插件、人类角色、replay（见父任务 Out of Scope）。
