# I3 车卡冒烟证据（smoke evidence）

- **任务**：`.trellis/tasks/10-02-i3-coc-example`（I3：CoC 7e 车卡阶段）
- **日期**：2026-10-03
- **环境**：`uv 0.7.12`、`python3`、`git`、`flock` 可用
- **场地**：`/tmp/soup-smoke`（`scaffold new --system coc7e`，**带 git**）
- **模式**：**内联降级**（无 sub-agent；master 在同上下文内联扮演 PL/KP），证明 AC5。
- **框架仓库交付**：`systems/coc7e/**`、`examples/soup/**`、`tools/scaffold.py`、`docs/tooling.md`、`docs/directory.md`、`templates/adventure/{AGENTS.md,tools/step.py}`、`tools/step.py`

---

## 0. 实现中发现并修复的 I2 缺陷（`tools/step.py`）

**现象**：`step commit` 子命令**完全不可用**——`cmd_commit` 引用 `args.all`，但
`build_parser()` 从未定义 `--all`（仅出现在 `INPUTS`/docstring 中），运行必抛
`AttributeError: 'Namespace' object has no attribute 'all'`。

```
$ uv run tools/step.py commit -m "x"
AttributeError: 'Namespace' object has no attribute 'all'
```

**影响**：I2 的 `scaffold.py` 直接调用 `step.do_commit()` 未触发该路径，故 I2 回归未暴露；
但一切 play-time 的 `step commit`（本任务车卡冒烟的核心）都会失败。

**修复**（最小改动，符合契约 `INPUTS = "... [--all] ..."`）：在 `commit` 子解析器补上
`--all`（`do_commit` 恒执行 `git add -A`，该 flag 为兼容占位），并同步
`templates/adventure/tools/step.py`（逐字节一致）。

```python
commit.add_argument("--all", action="store_true",
                    help="暂存全部变更（do_commit 恒执行 git add -A；保留以兼容契约）")
```

修复后 `step commit` / `step tag` 正常（见 §4、§6）。

---

## 1. 脚手架（`--system` 带入 + git）

```bash
$ uv run tools/scaffold.py new --module modules/soup.md --out /tmp/soup-smoke --system coc7e
{ "ok": true, "command": "scaffold new", "out": "/tmp/soup-smoke", "slug": "soup",
  "system": "coc7e",
  "systemFiles": { "flow": ["flow.md","phases/01-character-creation.md"],
                   "rules": ["character-creation.md"],
                   "tools": ["tools/.gitkeep"] },
  "commit": "f93d050", "tag": "compile/soup" }
```

- `flow/` = `flow.md` + `phases/01-character-creation.md`（模板占位 `flow/README.md` 被覆盖移除）。
- `rules/` = `character-creation.md`（模板占位 `rules/README.md` 被覆盖移除）。
- `AGENTS.md` 注明：`- 规则系统：\`coc7e\`（\`flow/\` 与 \`rules/\` 来自 \`systems/coc7e/\`）`。

```
$ git -C /tmp/soup-smoke log --oneline
f93d050 chore(compile): scaffold soup from soup.md
$ git -C /tmp/soup-smoke tag
compile/soup
```

---

## 2. 定位车卡阶段（读 AGENTS.md + flow）

- `AGENTS.md` §6「如何推进一场团」+ `flow/flow.md` 阶段索引 → 01 车卡 `character-creation`。
- `flow/phases/01-character-creation.md` 给出：目标 / 进入条件 / 参与角色（master + pl1，KP 不入内）/
  适用规则 / 退出条件 / 产出 / 编排步骤。

## 3. 开频道 + 投影（master）

```bash
# channels/ch-001-character-creation/meta.json
{ "purpose": "车卡：pl1 生成调查员并提交卡面",
  "participants": ["pl1"], "termination": "卡面提交并校验通过",
  "status": "open", "outcome": null }

$ uv run tools/context.py build --role pl1 --adventure /tmp/soup-smoke
{ "ok": true, "role": "pl1",
  "channels": ["baseline", "ch-001-character-creation"], "messages": 4 }

$ uv run tools/step.py commit --message "character: 开启车卡频道 ch-001（participants=pl1）"
{ "committed": true, "commit": "a74b8e6" }
```

## 4. 内联扮演 PL 生成角色（属性掷骰，记录 seed）

```bash
$ uv run tools/dice.py roll --expr 3d6      --count 7 --seed 1001   # STR/CON/SIZ/DEX/APP/INT/POW
  totals: [4, 11, 13, 15, 12, 8, 16]
$ uv run tools/dice.py roll --expr "2d6+6"  --seed 1002             # EDU
  total: 16
$ uv run tools/dice.py roll --expr 3d6      --seed 1003             # 幸运
  total: 12
```

换算（×5）+ 派生值：

| | STR | CON | SIZ | DEX | APP | INT | POW | EDU | 幸运 |
|---|---|---|---|---|---|---|---|---|---|
| 值 | 20 | 55 | 65 | 75 | 60 | 40 | 80 | 80 | 60 |

- HP = ⌊(55+65)/10⌋ = **12**；MP = ⌊80/5⌋ = **16**；SAN = POW = **80**
- DB/Build：STR+SIZ = 85 → 85–124 档 → DB **0** / Build **0**
- MOV：DEX(75) ≥ SIZ(65)（非「两者皆大于」）→ **8**
- 年龄 30（20–39，无年龄修正）
- 职业技能点 = EDU×4 = **320**；兴趣技能点 = INT×2 = **80**

```bash
$ uv run tools/step.py commit -m "character: pl1 掷属性并确定职业方向（医生）"
{ "committed": true, "commit": "6270d3b" }
```

## 5. 提交卡面（`sheet.md` + `sheet.json`）并被校验

```bash
$ uv run tools/step.py commit -m "character: pl1 提交卡面（sheet.md + sheet.json）"
{ "committed": true, "commit": "13ebd32" }
```

`roles/pl1/sheet.json`（节选）：

```json
{ "system": "coc7e", "name": "苏晚晴", "player": "pl1", "occupation": "医生",
  "age": 30, "gender": "女",
  "attributes": { "STR":20,"CON":55,"SIZ":65,"DEX":75,"APP":60,"INT":40,"POW":80,"EDU":80 },
  "derived": { "HP":12,"MP":16,"SAN":80,"Luck":60,"DB":"0","Build":0,"MOV":8 },
  "skillPoints": { "occupation":320, "interest":80 },
  "occupationSkills": ["急救","医学","外语(拉丁语)","心理学","科学(生物学)","精神分析","说服","信用评级"],
  "skills": { "信用评级":40,"医学":75,"急救":70,"心理学":60,"精神分析":40,"说服":40,
              "科学(生物学)":25,"外语(拉丁语)":24,"侦查":60,"图书馆使用":50,"聆听":35,"母语":80,"闪避":37 },
  "rolls": { "attrsSeed":1001, "eduSeed":1002, "luckSeed":1003 } }
```

master 校验（确定性脚本）：

```
本职技能数: 8 | 职业技能点: 320 / 320 | 兴趣技能点: 80 / 80
校验结果: PASS ✅
```

关闭频道并发布 outcome：

```json
{ "participants": ["pl1"], "status": "closed",
  "outcome": "pl1 完成车卡：苏晚晴（女，30，医生）。STR20/CON55/SIZ65/DEX75/APP60/INT40/POW80/EDU80；HP12/MP16/SAN80/幸运60/DB0/Build0/MOV8；职业点 320、兴趣点 80；卡面见 roles/pl1/sheet.{md,json}。" }
```

应公开 outcome 已写入 `channels/baseline/transcript.md`（公共基线频道）。

```bash
$ uv run tools/step.py commit -m "character: pl1 卡面校验通过，关闭 ch-001 并发布 outcome"
{ "committed": true, "commit": "b6d70e8" }
```

## 6. 交给 KP + 压缩 + 阶段边界（tag）

```bash
$ uv run tools/context.py build --role kp --adventure /tmp/soup-smoke
{ "ok": true, "role": "kp", "channels": ["baseline"], "messages": 3 }

$ uv run tools/context.py compact --role pl1 --keep 2 --adventure /tmp/soup-smoke
{ "ok": true, "role": "pl1", "before": 6, "after": 2, "summarized": 4 }
# → 写 roles/pl1/summary.md 并截断 context.jsonl

$ uv run tools/step.py commit -m "phase: 车卡完成（01-character-creation）" --tag phase/character-creation
{ "committed": true, "commit": "c2c7c99", "tag": "phase/character-creation" }
```

最终历史与 tag：

```
$ git -C /tmp/soup-smoke log --oneline
c2c7c99 phase: 车卡完成（01-character-creation）
b6d70e8 character: pl1 卡面校验通过，关闭 ch-001 并发布 outcome
13ebd32 character: pl1 提交卡面（sheet.md + sheet.json）
6270d3b character: pl1 掷属性并确定职业方向（医生）
a74b8e6 character: 开启车卡频道 ch-001（participants=pl1）
f93d050 chore(compile): scaffold soup from soup.md

$ git -C /tmp/soup-smoke tag
compile/soup
phase/character-creation
```

---

## 7. AC7：车卡频道工件隔离断言

车卡频道 `participants=[pl1]`；KP **未参与**。`context build` 按 participants 过滤：

```
kp  channels: ['channel/baseline']
pl1 channels: ['channel/baseline', 'channel/ch-001-character-creation']
PASS ✅ kp 不含 ch-001 频道
PASS ✅ kp 不含车卡私聊标记（seed=1001）
PASS ✅ kp 不含车卡私聊标记（3d6×5）
PASS ✅ pl1 含 ch-001 频道
PASS ✅ pl1 含车卡私聊标记（seed=1001）
PASS ✅ kp 仍含公共基线 outcome（苏晚晴）
AC7: PASS ✅
```

即：未参与车卡频道的 KP，其 `roles/kp/context.jsonl` **不含**车卡频道的 transcript 内容
（含仅存在于该频道的掷骰 seed），但**含**发布到公共基线的 outcome。隔离由
`channels/<id>/meta.json` 的 `participants` + `tools/context.py` 保证，非角色自律。

## 8. AC4：git 恢复点

```bash
$ git -C /tmp/soup-smoke checkout -q 13ebd32     # 回到「提交卡面」提交
HEAD now: 13ebd32 ; sheet.md present: yes ; context.jsonl present: yes
$ git -C /tmp/soup-smoke checkout -q master
HEAD now: c2c7c99 (phase: 车卡完成)
```

`git checkout <commit>` 后工作树完整、可继续；tag `phase/character-creation` → `c2c7c99`。

## 9. I2 回归（无 `--system`）

```bash
$ uv run tools/scaffold.py new --module modules/example.md --out /tmp/plain3
  system: None ; systemFiles: None ; commit: 91b1652 ; tag: compile/example
$ ls /tmp/plain3/flow /tmp/plain3/rules
  /tmp/plain3/flow:  README.md        # 模板占位保留
  /tmp/plain3/rules: README.md
$ grep 规则系统 /tmp/plain3/AGENTS.md
  - 规则系统：未指定（`flow/` 与 `rules/` 为模板占位）
$ for f in _lib dice state context step; do cmp -s tools/$f.py /tmp/plain3/tools/$f.py; done  # 全部一致
```

内嵌工具逐字节一致（框架 `tools/` ↔ `templates/adventure/tools/` ↔ `examples/soup/tools/`）：
`_lib.py` / `dice.py` / `state.py` / `context.py` / `step.py` 全部 `cmp` 通过。

---

## 10. AC 对照

| AC | 内容 | 结果 | 证据 |
|---|---|---|---|
| AC2（车卡） | 读 `AGENTS.md` 后完成车卡：生成角色、写 `sheet.md`/`sheet.json`、提交 KP；编排不依赖框架硬编码 | ✅ | §2–§6；sheet 校验 PASS |
| AC4 | 产生 `phase/character-creation` tag；`git checkout` 后可续 | ✅ | §6、§8 |
| AC5 | 全程内联降级（无 sub-agent） | ✅ | 本文件由 implement agent 内联扮演全部角色，未派子代理 |
| AC6 | `systems/coc7e/` + `examples/soup/` 与 `docs/` 契约一致 | ✅ | 目录树见 §11；`docs/directory.md` §2.1、`docs/tooling.md` `scaffold new` 已同步 |
| AC7 | 车卡频道工件隔离（participants 过滤） | ✅ | §7 |

## 11. `examples/soup/` 产物（`--system coc7e --no-git`，无嵌套 `.git`）

```
examples/soup/
├─ AGENTS.md
├─ flow/flow.md
├─ flow/phases/01-character-creation.md
├─ rules/character-creation.md
├─ module/{overview.md,clues.md,hooks.md,scenes/*,npcs/*}
├─ channels/baseline/{meta.json,transcript.md}
├─ roles/.gitkeep
├─ world/{state.json,visibility.json}
└─ tools/{_lib,dice,state,context,step}.py   # 与框架源逐字节一致
```

## 12. 契约缺口 / 不确定点（只报告）

1. **`step.py --all` 缺陷**（已修，见 §0）：I2 遗留，`step commit` CLI 完全不可用。已同步框架、
   模板、示例三份副本，保持逐字节一致。
2. **框架根 `.gitignore` 的 `log/` 规则**：会忽略 `examples/soup/log/`，故示例目录的审计日志
   不进入框架仓库（符合「审计不纳入 git」契约，但 `log/` 目录本身也不会被跟踪）。不阻断验收。
3. **规则口径**：本任务按 `implement.md` 固化「8 项中仅 EDU 用 `(2d6+6)×5`」（真实 CoC 7e 中
   INT 亦用 `(2d6+6)×5`）。已在 `rules/character-creation.md` 显式注明为**本实现口径**，便于后续调整。
4. **`check resolve` 未实现**：判定参数（大成功 1–5 等）仅文档化，属预期范围（推迟到扮演/战斗阶段）。
