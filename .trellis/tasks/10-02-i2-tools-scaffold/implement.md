# I2 implement — 执行计划

> 复杂任务。**进入实现前需用户评审批准**，然后 `task.py start`。

## 交付物

1. `tools/_lib.py` + `tools/{dice,state,context,step,scaffold}.py`（PEP 723 单文件）
2. `templates/adventure/`（骨架 + `AGENTS.md` 模板）
3. `scaffold new` 编译流程可用
4. 文档/索引小幅同步（README 目录一览已含 tools/，无需大改）

## 执行清单（有序）

- [ ] **1. `tools/_lib.py`**：冒险目录定位、JSON 输出、`log/events.jsonl` 追加、git 串行锁、seed/时间工具。
- [ ] **2. `tools/dice.py`**：`roll --expr --seed [--count]`；`random.Random(seed)`；写 log。
- [ ] **3. `tools/state.py`**：`get/set/mask`；读写 `world/state.json` 与 `world/visibility.json`；写 log。
- [ ] **4. `tools/context.py`**：`build --role`（按 participants + world mask 投影）+ `compact --role [--keep]`；投影日志。
- [ ] **5. `tools/step.py`**：`commit --message`（无变更跳过）+ `tag <name>`；`trpg.lock` 串行。
- [ ] **6. `templates/adventure/`**：骨架 + `AGENTS.md` 模板（含 `uv` 前提、工具用法、推进方式占位）。
- [ ] **7. `tools/scaffold.py`**：`new --module --out [--name]`；复制模板 → 解析模组 → 渲染 AGENTS.md → `git init` + 首发提交。
- [ ] **8. 端到端编译自测**：对 `modules/soup.md` 生成 `/tmp` 冒险目录，跑 AC1.1–AC1.8。
- [ ] **9. 自洽核对**：产物目录与 `docs/directory.md` 一致；工具行为与 `docs/tooling.md` 一致。

## 验证命令

```bash
# 工具可运行（PEP 723 / uv）
uv run tools/dice.py --help
uv run tools/state.py --help
uv run tools/context.py --help
uv run tools/step.py --help

# AC1.2 可复现
uv run tools/dice.py roll --expr 1d100 --seed 42
uv run tools/dice.py roll --expr 1d100 --seed 42   # 两次应相同

# AC1.3 状态往返
uv run tools/state.py set sanity 55 --adventure /tmp/soup
uv run tools/state.py get sanity --adventure /tmp/soup

# AC1.9 mask 过滤（公开 vs kp-only）
uv run tools/state.py mask --role pl1 --adventure /tmp/soup
uv run tools/context.py build --role pl1 --adventure /tmp/soup
uv run tools/context.py build --role kp  --adventure /tmp/soup
# 断言：pl1 的 context.jsonl 不含 /secrets/** 内容，kp 含

# AC1.6 编译
uv run tools/scaffold.py new --module modules/soup.md --out /tmp/soup
ls /tmp/soup /tmp/soup/module /tmp/soup/tools
git -C /tmp/soup log --oneline

# AC1.7 审计
tail -n 5 /tmp/soup/log/events.jsonl

# 纯标准库回退（无 uv 亦可）
python3 tools/dice.py roll --expr 1d100 --seed 42
```

人工核对：
- [ ] AC1.1–AC1.9 逐条通过。
- [ ] `context build` 不含未参与频道（构造两频道、一个角色只在一个频道，断言另一个不出现）。
- [ ] `context build` 按 world mask 过滤（pl1 无 `/secrets/**`，kp 有）。
- [ ] 并发 `step commit` 不报 `index.lock`。
- [ ] 生成目录的 `AGENTS.md` 单读即可理解如何运行。

## 风险文件 / 回滚点

- **新增**：`tools/*`、`templates/adventure/*`。**同步更新** `docs/visibility.md` / `docs/tooling.md`（World State mask）。
- **风险**：`context build` 泄密（安全关键，含 channel participants + world mask 两重过滤）、并发 git 锁、uv 缺失时的回退。
- **回滚点**：每完成一个工具提交一次；`scaffold` 只写 `--out` 目录，不污染框架仓库。

## task.py start 前检查

- [ ] 用户已评审批准 `prd.md` / `design.md` / `implement.md`。
- [ ] 确认 `check resolve` 归 I3，不在 I2。
- [ ] `implement.jsonl` / `check.jsonl` 填入真实 spec/research 条目。

## 修订

- 2026-10-02 规划初稿。
