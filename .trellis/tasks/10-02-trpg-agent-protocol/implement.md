# implement.md — 执行计划

> 复杂任务执行计划。**当前测试点：进入实现前需用户评审并明确批准**（Trellis 规划门）。批准后才 `task.py start`。

## 范围界定

本次任务（父任务）= 定义协议框架。按用户明确要求，**第一个交付增量只做文档，不改任何代码**；工具/脚手架/示例作为后续独立增量。

| 增量 | 内容 | 验收 | 归属 |
|---|---|---|---|
| **I1（本次实现）** | 中文协议文档 `docs/` + 根 `README.md` | AC6 | 本任务 |
| I2 | 确定性工具 + 脚手架模板 + 编译流程 | AC1 | 建议独立子任务 |
| I3 | CoC 7e 系统 + soup 示例 + 端到端 PoC | AC2–AC5 | 建议独立子任务 |

> I2/I3 依赖 I1 的文档定稿。父任务只承担 I1；I2/I3 建议用 `task.py create --parent` 建子任务（待用户确认是否拆分）。

## I1 执行清单（有序）

- [x] **1. 建立文档骨架**：创建 `docs/` 目录。
- [x] **2. `docs/protocol.md`**：协议总览——原语（Master/Role/Channel/Flow/System/Module/Tool/World）、两条生命周期（编译/推进）、角色对称与 master 定位。
- [x] **3. `docs/directory.md`**：目录契约——框架仓库结构与冒险目录结构、必需/可选文件、唯一不变量（`AGENTS.md` 自描述）。
- [x] **4. `docs/tooling.md`**：工具 CLI 契约（dice/check/state/context/step/scaffold）+ git 步进契约（每消息提交、边界 tag、串行执行）。
- [x] **5. `docs/visibility.md`**：频道化可见性、上下文投影（`context build`）、秘密隔离、记忆三层与压缩、降级模式。
- [x] **6. `docs/capabilities.md`**：宿主能力声明（spawn-subagent/human-input/context-isolation/tool-gating）与降级矩阵。
- [x] **7. 根 `README.md`**：中文简介——这是什么、两条工作流、目录一览、指向 `docs/`。
- [x] **8. 自洽性复查**：逐条核对 `docs/` 覆盖 PRD 的 D1–D10 与 R1–R13；统一术语（master/KP/PL/channel/flow/module/role）；确认全中文。
- [x] **9. 清理残留（R14）**：已删除 `logs/`、所有 `__pycache__/`、`.pytest_cache/`，以及旧实现 `src/`、`main.py`、`tests/`、`pyproject.toml`、`uv.lock`、`.python-version`、`.env.example`、`.venv`；仅保留 `modules/` 与配置。

## 验证命令

文档阶段无测试，验证 = 覆盖与自洽检查：

```bash
# 目录产物存在性
ls -R docs README.md

# 关键术语/决策覆盖抽查（示例）
rg -n "master|channel|flow|context build|自描述|降级" docs README.md

# 中文性：不应出现整段英文说明（术语除外）
rg -n "^[A-Za-z].{40,}" docs README.md

# 残留已清空（logs / pytest 缓存 / __pycache__）
! test -d logs && ! test -d .pytest_cache && ! find . -name __pycache__ -not -path './.venv/*' | grep -q .
```

人工核对清单：
- [x] D1–D10 每条都能在 `docs/` 找到落点。
- [x] R1–R13 每条都有对应描述。
- [x] AC1–AC6 在文档中可被读者理解与验证。
- [x] 术语前后一致，无中英混排的未定义术语。

## 风险文件 / 回滚点

- **改动文件**：新增 `docs/*.md`；改写根 `README.md`（当前为空）；删除生成物与旧实现（R14，已完成）。
- **不再存在**：`src/`、`main.py`、`tests/`、`pyproject.toml`、`uv.lock`、`.python-version`、`.env.example`、`.venv`（旧实现已按用户确认删除，git 历史可恢复）。
- **保留**：`modules/`（原始模组）、`AGENTS.md`、`.gitignore`、`.trellis/`、`.pi/`、`.dsh/`、`.agents/`。
- **风险**：低。文档与代码解耦；删除项均为生成物/缓存或已在 git 历史的旧实现。
- **回滚点**：I1 完成后打一个提交（`docs: 协议框架文档`），便于评审回退。

## 进入实现前的检查（task.py start 前）

- [x] 用户已评审并明确批准 `prd.md` + `design.md` + `implement.md`。
- [x] 用户确认 I1 只做文档、不改代码。
- [x] 用户确认 I2/I3 是否拆分为子任务（以及是否现在创建）。
- [x] `implement.jsonl` / `check.jsonl` 已按需填充（本任务无既有 spec 可引用时，可指向 `docs/` 产物与 `design.md`）。

## 后续增量预告（不在本次范围）

- **I2**：`tools/`（dice/check/state/context/step）、`templates/adventure/`、`scaffold new` 编译流程。
- **I3**：`systems/coc7e/`（规则+默认 flow+判定工具）、`examples/soup/`、端到端 PoC（AC2–AC5）。
- **后续**：Pi/dsh 适配插件（能力提供者）、人类担任角色、replay 生成、旧 Python 实现处置。
