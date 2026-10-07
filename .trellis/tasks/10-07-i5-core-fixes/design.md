# I5 design — core 缺陷修复

> 依据源码证据（见 prd Background）。改动集中在 `tools/_lib.py`、`tools/context.py`、`tools/dice.py`，并同步 `templates/adventure/tools/*`（逐字节一致）与 `docs/`。

## F1 fail-closed mask

**现状**：`_lib.read_visibility` 缺/非法文件 → `{"default": "public", "rules": []}`。

**改法**：
- 缺/非法 → 返回 `{"default": [], "rules": [], "_missing": True}`（**空受众 = 任何角色都不可见**）。
- `decide_path`：`default` 允许 `"public"` 或 role 列表；**空列表** = 无人可见（visible=False）。
- `context build` / `state mask` 检测 `_missing` → stderr 警告，并在 stdout 标 `"visibility": "missing(fail-closed)"`。
- 空 `state.json`（无叶子）不受影响。

**语义**：mask 是「允许清单」；无清单 = 不放行。与 R8「隔离靠机制」一致。

## F2 频道状态驱动投影（停止重放膨胀）

**现状**：`load_channels` 对参与频道一律拼接全量 `transcript.md`；`compact` 截角色文件 → 下次 build 又重放。

**改法**：
- `channels/<id>/meta.json` 约定：`status ∈ {open, closed}`、`outcome`（关闭纪要字符串，可选文件 `outcome.md`）。
- `load_channels`：
  - **open** 频道 → 全量 transcript（活跃场景必须完整）。
  - **closed** 频道 → 只用 `outcome`（纪要），**不再读 transcript**。
- 效果：已关闭频道对投影的贡献固定为纪要长度，体积不随历史线性增长。
- `context compact` 职责收敛：仅对角色**私有记忆**（`memory.md`/`summary.md`）做摘要，不再承担「控住 build 体积」。
- 关闭频道由 master 执行（写 `meta.json.status=closed` + `outcome`）；本任务不改工具集新增 channel 工具（未来需要再补）。
- 文档同步：`docs/visibility.md`。

## F3 移除 worldPaths 默认输出

- `cmd_build`：默认 stdout 去掉 `worldPaths`；`--debug` 时保留（`visible_paths` 已只含可见路径，无隐藏泄漏，仅卫生）。

## F4 工具结果可见性：统一原则（无代码特例）

**原则**：**工具不管理可见性**。
1. 工具结果只：**返回调用者**（stdout）+ 写**系统审计** `log/events.jsonl`（系统层，**永不投影给角色**）。
2. 要可见，由 master/角色**显式写入** `channels/<id>/`（按 participants）/ `roles/<id>/`（仅自己）/ `world/`（按 mask）。
3. **可见性 = 写入位置**（沿用「位置即权限」）。

**推论**：
- 秘密骰 = 调用者不把点数写进公共频道 → 自动隔离，**无需 `--secret`**。
- 任何工具一律适用，无逐工具可见性参数。
- 审计日志含敏感值是可接受的（`log/` 永不投影、不入 git）。

**本任务落地**：仅**文档化**该原则（`docs/visibility.md` §3 改写、`docs/tooling.md` 总则补一句）；并**断言 `context build` 不读 `log/`**。

> 未来可选：提供 `channel append <id>` 之类的**显式写入助手**，让「写对位置」更容易；不在本任务。

## 兼容

- 内嵌副本：`templates/adventure/tools/{_lib,context,dice}.py` 修改后与框架 `tools/` **逐字节一致**（`cmp` 校验）。
- I2/I3 行为回归：非缺陷路径不变（dice 默认、context 默认不含 closed 频道、非 `_missing` mask 行为不变）。

## 风险

| 风险 | 缓解 |
|---|---|
| fail-closed 使既有示例（无 visibility 规则）world 不可见 | scaffold 始终生成 `visibility.json`；`examples/soup` 已有（空规则+public）；文档说明 |
| 关闭频道无 outcome 导致信息丢失 | build 在 `closed` 且无 `outcome` 时回退 transcript 并警告 |
| `default: []` 语义与既有 `default: "public"` 混用 | `decide_path` 显式分支 + 测试 |
| 「位置即权限」依赖写入纪律 | 显式写文件可审计；未来可加 `channel append` 助手；文档强调 |
