# 协议实现契约（TrpgWorld）

> 本文件约束后续增量（I2 工具/脚手架、I3 CoC 示例、宿主适配）的实现。权威依据仍是 `docs/` 与任务 `design.md`；本文件只提炼「不可违背」的条款。

## 1. 权威来源

- 协议文档以仓库根 `docs/` 为准（`protocol.md` / `directory.md` / `tooling.md` / `visibility.md` / `capabilities.md`）。
- 设计决策编号 D1–D10、需求 R1–R14 见任务 `prd.md` / `design.md`。
- 文档语言：简体中文（技术术语可保留英文）；不要把这些文档改写成英文。

## 2. 不可违背的契约

1. **唯一硬性不变量 = 目录自描述**：每个冒险目录必须有 `AGENTS.md`（或同等入口说明），自描述到「任意 agent 不依赖外部知识即可运行」。其余结构可被 agent fork。
2. **工具确定性分层（R7/D8）**：随机源（骰子，带种子）与状态变更**必须**经确定性 CLI；判定结算由规则工具提供；叙事裁决由 agent 决定。**工具输出即真相**。
3. **副作用落盘**：工具必须写 `world/`（真相）与 `log/`（审计）；不是无副作用函数。
4. **git 只能由工具串行执行（R9/D9）**：任何 `git add/commit/tag` 都走 `step *` 工具，串行化以避免 `index.lock`；提交粒度 = 每条消息/每步；场景与阶段边界必须打 tag。
5. **可见性靠文件位置 + 投影（R8）**：秘密隔离由 `channels/<id>/` 的文件位置与 `context build --role <id>` 投影保证；**不得**依赖角色/agent 自律。角色只读自己的 `roles/<id>/context.jsonl`。
6. **角色对称，master 不扮演角色（R4/D2）**：GM/KP、PL、NPC 一视同仁；master 只推进流程。
7. **能力缺失不得阻断跑通（R2/R12）**：无 `spawn-subagent` 时降级为内联扮演；降级代价（隔离变弱）在文档中标注即可。

## 3. 命名与目录

- 使用 `docs/`（非 `doc/`）；使用 `roles/` 作为「角色实例」目录，对应需求中的 `characters` 层。
- 冒险目录固定名：`AGENTS.md` / `flow/` / `rules/` / `module/` / `roles/` / `channels/` / `world/` / `log/` / `tools/`。

## 4. 验证要求（I2/I3）

- 工具：每个工具需可独立 CLI 调用并有可断言输出（stdout JSON + 文件副作用）。
- AC1 编译 PoC、AC2 端到端、AC3 秘密隔离、AC4 git 语义、AC5 降级可跑——见任务 `prd.md`，实现后逐条验证。
- 修改 `docs/` 时同步核对 `design.md`，二者不得矛盾。

## 5. 禁止

- 不得引入硬编码的单一流程引擎（回到旧 LangGraph 老路）来替代 `flow/` + master 编排。
- 不得让角色/子代理直接读 `log/`、他人 `roles/`、全量 `channels/`。
- 不得绕过 `step *` 直接 `git commit`。

## 6. 工具实现约定（I2 落地）

- **形态**：每个工具是 PEP 723 内联元数据的 Python 单文件，`# /// script` 中 `dependencies = []`（纯标准库）；`uv run tools/<t>.py` 与 `python3 tools/<t>.py` 均可运行。
- **CLI**：argparse 子命令；stdout 为 JSON；退出码 0（成功）/ 1（业务失败）/ 2（用法错误）。
- **共享库** `tools/_lib.py`：冒险目录定位（`--adventure` 或向上找 `AGENTS.md`）、JSON 输出、`log/events.jsonl` 追加、`.git/trpg.lock` flock 串行锁、JSON 路径 glob + mask 投影。
- **内嵌副本**：`templates/adventure/tools/{_lib,dice,state,context,step}.py` 必须与框架 `tools/` **逐字节一致**（`scaffold.py` 例外，不内嵌）。
- **role id 安全**：传入 `--role` 前必须经 `_lib.safe_id()` 校验（拒空、`.`、`..`、`/`、`\`、NUL、控制字符），防止路径穿越。
- **可见性**：`context build` 双重过滤——channel `participants` + `world/visibility.json` mask；`participants` 全员哨兵为 `["*"]`（也接受 `"public"`）；mask 未命中用 `default`，非 `public`/名单外一律隐藏（fail-closed）。
- **审计不纳入 git**：`log/events.jsonl` 由模板 `.gitignore` 忽略。
- **`roles/` 实例**：目录必需，实例在 play-time（车卡）由 master 创建；编译后可为空。
- **规则系统入包**：`systems/<name>/` 提供 `flow/` 、`rules/` 与可选 `tools/`；`scaffold new --system <name>` 将其带入冒险目录（`tools/` 内嵌副本逐字节一致）。`--no-git` 生成无嵌套 git 的纯净产物，用于提交进框架仓库（如 `examples/soup`）；带 git 的冒烟在 `/tmp` 副本执行。
