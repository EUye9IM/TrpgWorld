# I5 implement — 执行计划

> 复杂任务（4 项缺陷，跨 3 个文件）。**进入实现前需用户评审批准**，然后 `task.py start`。

## 交付物

1. `tools/_lib.py`：`read_visibility` fail-closed；`decide_path` 支持空受众。
2. `tools/context.py`：closed 频道用 `outcome`；`worldPaths` 移入 `--debug`；`_missing` 警告。
3. `tools/dice.py`：`--secret` / `--role`；公共审计脱敏。
4. `templates/adventure/tools/{_lib,context,dice}.py`：逐字节同步。
5. `docs/visibility.md`、`docs/tooling.md` 同步。

## 执行清单（有序）

- [ ] **1. F1**：`_lib.read_visibility` 缺/非法 → `{"default": [], "rules": [], "_missing": True}`；`decide_path` 分支处理 `default` 为 `"public"` / 列表 / 空列表；返回结构保持稳定。
- [ ] **2. F1 传播**：`context.py` 与 `state.py` 检测 `_missing` → stderr 警告 + stdout 标 `visibility` 状态；`state mask` 全隐藏。
- [ ] **3. F2**：`context.load_channels` 读 `meta.status`/`meta.outcome`（或 `outcome.md`）；open→transcript，closed→outcome（缺失则回退 transcript + 警告）。
- [ ] **4. F3**：`context.cmd_build` 默认不输出 `worldPaths`；`--debug` 时输出。`dice`/其它工具的 `--debug` 保持一致（如已存在）。
- [ ] **5. F4（文档+断言）**：`docs/visibility.md` §3 改写为「工具不管理可见性 / 位置即权限」；`docs/tooling.md` 总则补一句；**不加** `--secret`。断言 `context build` 不读 `log/`。
- [ ] **6. 同步内嵌副本**：`cp tools/{_lib,context,dice}.py templates/adventure/tools/` 并 `cmp` 校验。
- [ ] **7. docs 同步**：`visibility.md`（fail-closed、closed/outcome、秘密骰受限位置）、`tooling.md`（dice `--secret`、context `--debug`）。
- [ ] **8. 回归**：I2/I3 行为与非缺陷路径不变。

## 验证命令

```bash
# AC1 fail-closed
cp examples/soup/world/visibility.json /tmp/vis.bak
mv examples/soup/world/visibility.json /tmp/vis.moved
uv run tools/state.py set secret.x 1 --adventure examples/soup >/dev/null
uv run tools/context.py build --role pl1 --adventure examples/soup   # 投影不含 world 状态 + 警告
uv run tools/state.py mask --role pl1 --adventure examples/soup      # 全隐藏
mv /tmp/vis.moved examples/soup/world/visibility.json

# AC2 closed 频道用 outcome
# 构造 channels/closed1/{meta.json(status=closed,outcome=...)}, channels/open1/...
uv run tools/context.py build --role pl1 --adventure /tmp/advx
# 断言 closed1 内容 == outcome，且不含 transcript 全量

# AC3 worldPaths 默认不输出
uv run tools/context.py build --role pl1 --adventure examples/soup | grep -c worldPaths   # 期望 0
uv run tools/context.py build --role pl1 --adventure examples/soup --debug | grep -c worldPaths

# AC4 通用原则：context build 不读 log/ 作为投影来源
rg -n "log/" tools/context.py || echo "context 不引用 log/（期望）"
# 投影来源仅：roles/<id>/*、world/（masked）、channels/（participants）

# AC5 内嵌一致
for f in _lib context dice; do cmp -s tools/$f.py templates/adventure/tools/$f.py && echo "$f ok"; done
git status --short
```

人工核对：
- [ ] AC1–AC5 逐条通过。
- [ ] 非缺陷路径回归：`dice` 默认行为不变；`context` 对 open 频道仍给全量；正常 mask 行为不变。
- [ ] AC4：文档含通用原则；`context build` 不引用 `log/`。

## 风险文件 / 回滚点

- **修改**：`tools/_lib.py`、`tools/context.py`、`templates/adventure/tools/*`、`docs/visibility.md`、`docs/tooling.md`（F4 仅文档，`dice.py` 不改）。
- **风险**：fail-closed 影响既有示例；`default: []` 语义分支遗漏；closed 无 outcome 回退。
- **回滚点**：三项独立，可按 F1/F2/F3/F4 分别提交，便于回退。

## task.py start 前检查

- [ ] 用户已评审批准。
- [ ] F1–F4 语义（尤其 fail-closed 与 closed/outcome）已确认。
- [ ] `implement.jsonl` / `check.jsonl` 填入真实条目。

## 修订

- 2026-10-04 依 I4 审查报告建立；F3 判定为卫生问题（非泄漏）。
