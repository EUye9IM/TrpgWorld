# I4 implement — 执行计划

> 复杂任务。**进入实现前需用户评审批准**，然后 `task.py start`。
> **依赖**：I5（core 缺陷 F1–F4）应先完成——插件依赖 `context build` 的正确性与 fail-closed mask。

## 交付物

1. `docs/capabilities.md` — 契约 v2（三层隔离模型 + C1–C17 + Pi/dsh 映射 + 已实现/预留标注 + L10 边界）
2. `.pi/agents/trpg-role.md` — 角色子代理人格模板
3. `.pi/extensions/trpg/index.ts` — 注册 `trpg_role` / `trpg_dice`
4. `.pi/settings.json` — 注册扩展
5. 测试：fake agent 断言（投影来源、argv 隔离旗标、工具面）
6. README「当前状态」补 I4

## 执行清单（有序）

- [ ] **1. 契约 v2 文档**：改写 `docs/capabilities.md`——三层隔离模型、C1–C17 表（逐条 `已实现/预留`）、Pi/dsh 原语映射、降级矩阵、**L10 与 prompt 约束临时性**声明。
- [ ] **2. `trpg-role.md`**：角色人格模板（frontmatter `tools: trpg_dice` 或说明；正文写「只依据注入内容行动」）。
- [ ] **3. `index.ts`**：
  - `resolveAdventure()`（`AGENTS.md` 向上查找 / 配置）
  - `buildProjection(role)`：spawn `context.py build`
  - `buildRolePrompt(persona, projection, instruction)`：纯函数，便于断言
  - `buildChildArgv(...)`：集中构造 `pi` 子进程参数（含所有隔离旗标）——**便于单测**
  - `trpg_role` / `trpg_dice` 两个 `registerTool`
  - `TRPG_PI_CMD`（测试可覆盖）、`TRPG_DEBUG`（写 prompt+argv 到临时文件）
- [ ] **4. 注册**：`.pi/settings.json` 加 `./extensions/trpg/index.ts`。
- [ ] **5. fake agent 测试**：脚本（bash 或 node）伪造 `pi`，读取 argv/prompt → 写断言：
  - 投影 == `context build --role <id>` 产物；不含他人投影；
  - argv 含 `--no-session --no-context-files --no-extensions --no-skills --no-prompt-templates --no-builtin-tools --tools trpg_dice`；
  - 未授予 fs/bash/state/context/step/subagent。
- [ ] **6. 真实回合（可选/冒烟）**：`pi -e .pi/extensions/trpg/index.ts` 加载后调用 `trpg_role`，跑一次真实角色回合。
- [ ] **7. README / docs 同步**：README 状态、`docs/capabilities.md` 交叉引用。

## 验证命令

```bash
# 扩展可加载（注册表可见）
pi -e .pi/extensions/trpg/index.ts --help 2>&1 | head   # 或在 pi 内 /help 查工具
# fake agent：覆盖子 pi 命令，断言隔离旗标与注入
TRPG_PI_CMD=$PWD/tests/fake-pi.sh TRPG_DEBUG=1 \
  node --experimental-strip-types .pi/extensions/trpg/index.ts 2>/dev/null || true
# 断言 TRPG_DEBUG 产出的 prompt/argv
grep -q -- "--no-context-files" "$TRPG_DEBUG_OUT" && echo argv-ok
grep -q -- "--tools trpg_dice" "$TRPG_DEBUG_OUT" && echo tools-ok
# 协议 core 未被改
git status --short
```

人工核对：
- [ ] AC1 契约 v2 完整、逐条标注、与审查结论一致。
- [ ] AC2 插件可加载、工具可查。
- [ ] AC3 投影来自 `context build`（fake agent 断言）。
- [ ] AC4 core 无副作用。
- [ ] AC5 文档声明 prompt 约束为临时 + 预留项。

## 风险文件 / 回滚点

- **新增**：`.pi/agents/trpg-role.md`、`.pi/extensions/trpg/index.ts`、测试脚本。
- **修改**：`docs/capabilities.md`、`.pi/settings.json`、`README.md`。
- **风险**：Pi 旗标/API 版本漂移；子代理未加载扩展导致无 `trpg_dice`；prompt 约束隔离弱（已知）。
- **回滚点**：扩展独立文件，删除即恢复；不改 core。

## task.py start 前检查

- [ ] 用户已评审批准。
- [ ] **I5 已完成**（F1–F4）。
- [ ] `implement.jsonl` / `check.jsonl` 填入真实条目。

## 修订

- 2026-10-04 依审查报告收敛：契约 v2 仅文档；插件用 prompt+无 fs/bash 隔离；机制化隔离与 C11–C17 预留。
