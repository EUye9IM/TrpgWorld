# I3 implement — 执行计划

> 复杂任务。**进入实现前需用户评审批准**，然后 `task.py start`。

## 交付物

1. `systems/coc7e/README.md` + `rules/character-creation.md`
2. `systems/coc7e/flow/{flow.md,phases/01-character-creation.md}`（其余阶段在索引标「后续待补」）
3. `tools/scaffold.py` 增加 `--system <name>` / `--systems-dir <dir>`
4. `examples/soup/`（scaffold 产物，含 coc7e flow/rules）
5. 车卡冒烟：`channels/`、`roles/pl1/sheet.{md,json}`、`context.jsonl`、git 提交与 `phase/character-creation` tag
6. `docs/` 同步：`tooling.md`（scaffold `--system`）、`directory.md`（`systems/coc7e/` 说明）

## 执行清单（有序）

- [ ] **1. 车卡规则** `systems/coc7e/rules/character-creation.md`：属性（`3d6×5`，EDU=`(2d6+6)×5`）、派生值（HP/MP/SAN/幸运/DB·Build/MOV/年龄修正）、职业与技能点、判定参数（**大成功 1–5**、极难 ≤1/5、困难 ≤1/2、大失败规则）、`sheet.md`/`sheet.json` 产出格式。
- [ ] **2. flow** `systems/coc7e/flow/flow.md`（阶段索引，01 已实现，02–06 待补）+ `phases/01-character-creation.md`（目标/进入/参与角色/适用规则/退出/产出 + 编排步骤）。
- [ ] **3. `scaffold --system`**：改 `tools/scaffold.py` 支持带入 `flow/`、`rules/`、`systems/<n>/tools/*`；无 `--system` 保持 I2 原行为。
- [ ] **4. `examples/soup/`**：`scaffold new --module modules/soup.md --out examples/soup --system coc7e`；确认 `.git`、flow/rules 就位。
- [ ] **5. 冒烟（内联降级）**：按 `design.md` §5 跑车卡：建车卡 channel → PL 生成角色（sheet.md/json）→ 提交 KP → compact → commit + `phase/character-creation` tag。
- [ ] **6. AC7 工件隔离断言**：`context build --role kp` 不含未参与车卡频道的角色内容（participants 过滤）。
- [ ] **7. docs 同步**：`tooling.md` 的 `scaffold new` 增加 `--system`；`directory.md` 说明 `systems/coc7e/`。
- [ ] **8. 回归**：I2 的 `scaffold`（无 `--system`）与内嵌工具一致性 `cmp` 仍通过。

## 验证命令

```bash
# 骨架与 ---system 带入
uv run tools/scaffold.py new --module modules/soup.md --out /tmp/soup3 --system coc7e
ls /tmp/soup3/flow /tmp/soup3/rules
test -f /tmp/soup3/flow/phases/01-character-creation.md && echo flow-ok
# 无 ---system 向后兼容
uv run tools/scaffold.py new --module modules/example.md --out /tmp/plain3
cmp -s tools/_lib.py /tmp/plain3/tools/_lib.py && echo embed-identical

# 车卡冒烟（agent 执行，见 design §5）
uv run tools/context.py build --role pl1 --adventure examples/soup
uv run tools/context.py build --role kp  --adventure examples/soup
git -C examples/soup log --oneline | head
git -C examples/soup tag | grep phase/character-creation
```

人工核对：
- [ ] AC2（车卡）达成：角色卡 `sheet.md`/`sheet.json` 生成且内容符合规则。
- [ ] AC4：有 `phase/character-creation` tag，`git checkout` 后可续。
- [ ] AC5：全程内联、未派子代理。
- [ ] AC6：`systems/coc7e` 与 `examples/soup` 目录/流程与 `docs/` 一致。
- [ ] AC7：未参与车卡频道的角色投影不含车卡内容。

## 风险文件 / 回滚点

- **新增**：`systems/coc7e/**`、`examples/soup/**`。**修改**：`tools/scaffold.py`、`docs/tooling.md`、`docs/directory.md`。
- **风险**：内联泄密（已知代价）、CoC 规则翻译偏差（参数化可改）、`scaffold --system` 回归。
- **回滚点**：`scaffold.py` 改动单独提交；`examples/soup` 独立目录，可整目录重建。

## task.py start 前检查

- [ ] 用户已评审批准 `prd.md` / `design.md` / `implement.md`。
- [ ] 确认范围：**只做车卡阶段**，`check resolve` 推迟。
- [ ] `implement.jsonl` / `check.jsonl` 填入真实 spec/research 条目。

## 修订

- 2026-10-02 收窄为车卡阶段；大成功 = 1–5。
