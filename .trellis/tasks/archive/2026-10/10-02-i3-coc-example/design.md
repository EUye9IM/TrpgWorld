# I3 design — CoC 7e 车卡阶段技术设计

> 依据 `docs/` 与父任务 `design.md`。范围：**只做车卡阶段**。

## 1. 交付物结构

```
systems/coc7e/
├─ README.md                       # 规则系统说明：如何被 scaffold 带入
├─ rules/
│   └─ character-creation.md       # 车卡规则（属性/派生/职业/技能/背景 + 参数）
├─ flow/
│   ├─ flow.md                     # 阶段索引（只实现 01；其余标「后续待补」）
│   └─ phases/
│       └─ 01-character-creation.md
└─ tools/                          # 本阶段为空（check resolve 推迟）
    └─ .gitkeep

examples/soup/                     # scaffold new --module modules/soup.md --system coc7e 产物
```

## 2. 车卡规则（`rules/character-creation.md`）

- **属性**：8 项（STR/CON/SIZ/DEX/APP/INT/POW/EDU），每项 `3d6×5`（EDU 为 `(2d6+6)×5`，按 CoC 7e）。
- **派生值**：HP = ⌊(CON+SIZ)/10⌋、MP = ⌊POW/5⌋、SAN = POW、幸运 = `3d6×5`、DB/Build 由 STR+SIZ 表决定、MOV 由 STR/DEX−SIZ 与年龄决定。
- **年龄修正**：按 CoC 7e 年龄分档调整属性/EDU（可选，MVP 允许简化并注明）。
- **职业与技能**：从职业技能表中选 8 项本职技能；技能点 = EDU×4（+ 职业公式差异）；兴趣点 = INT×2。
- **判定参数**（供后续 `check` 使用，本阶段仅文档化）：**大成功 = 1–5**、极难 ≤1/5、困难 ≤1/2、常规 ≤目标、大失败 96–100（目标 <50）或 100（目标 ≥50）。
- **产出**：`roles/<id>/sheet.md`（人读）+ `roles/<id>/sheet.json`（机读，含 attributes/derived/skills/occupation/backstory）。

> 规则文档只描述**机制与参数**，不含硬编码引擎；执行由 agent + `dice` 工具完成。

## 3. 车卡 flow（`flow/flow.md` + `phases/01-character-creation.md`）

阶段索引：

| # | 阶段 | 状态 |
|---|---|---|
| 01 | 车卡 character-creation | ✅ 本任务 |
| 02 | 导入 introduction | 后续待补 |
| 03 | 扮演/调查 investigation | 后续待补 |
| 04 | 战斗 combat | 后续待补 |
| 05 | 理智 sanity | 后续待补 |
| 06 | 结团 ending | 后续待补 |

`01-character-creation.md` 内容约定字段：**目标 / 进入条件 / 参与角色 / 适用规则 / 退出条件 / 产出**。

编排（内联降级下 master 依此推进）：

```
进入 01-车卡
  master 开 channel(车卡, participants=[pl1])        # 车卡频道，KP 不入内
  PL 依 rules + dice 生成角色；在频道内讨论/迭代
  PL 提交卡面 → master 校验 → 关闭 channel（outcome=卡面摘要）
  master 把 outcome publish 到公共基线频道并交给 KP
  context compact(pl1) + step commit + step tag phase/character-creation
退出 01 → （后续阶段未实现，冒烟到此为止）
```

## 4. `scaffold --system`

- 新增参数：`--system <name>`、`--systems-dir <dir>`（缺省 `<框架>/systems`）。
- 行为：
  1. 现有模板流程不变（骨架 + 解析模组 + 渲染 AGENTS.md）。
  2. 若给 `--system`：把 `systems/<name>/flow/` 内容复制到冒险 `flow/`（覆盖模板占位）；`systems/<name>/rules/` → 冒险 `rules/`。
  3. 复制 `systems/<name>/tools/*` → 冒险 `tools/`（**逐字节一致**，沿用 I2 约束）。
  4. 在 `AGENTS.md`/`module/overview.md` 注明所用 system。
- 无 `--system` 时保持 I2 行为（向后兼容）。

## 5. 冒烟流程（AC2/AC4/AC5/AC7）

以 `examples/soup` 为场地，用**内联降级**执行：

1. `scaffold new --module modules/soup.md --out examples/soup --system coc7e`。
2. agent 读 `examples/soup/AGENTS.md` + `flow/flow.md` → 定位 01-车卡。
3. master 建 `channels/ch-001-character-creation/meta.json`（participants=[pl1]）。
4. `uv run tools/context.py build --role pl1` → 读 `roles/pl1/context.jsonl` → PL 发言/生成角色 → 追加 transcript → `step commit`。
5. 车轮若干回合；PL 提交卡面（写 `roles/pl1/sheet.md|json`）。
6. master 关闭 channel（写 outcome），`publish` 到公共基线频道，交给 KP（`context build --role kp`）。
7. `context compact --role pl1`；`step commit -m "phase: 车卡完成"` + `step tag phase/character-creation`。
8. **AC7 断言**：`context build --role kp` 与 `--role pl1` 的投影中，未参与角色不含车卡频道内容（用 participants 过滤验证）。

## 6. 风险与权衡

| 风险 | 缓解 |
|---|---|
| 内联降级可能泄密 | 已知代价；AC7 只做**工件级**断言 |
| 车卡规则翻译偏差（CoC 7e） | 参数化（大成功 1–5 等），文档可改；允许简化并注明 |
| `scaffold --system` 破坏 I2 兼容 | 无 `--system` 保持原行为；回归 I2 的 scaffold 用例 |
| 内嵌工具不一致 | 沿用逐字节 `cmp` 校验 |
| 冒烟依赖真实 LLM、非确定 | 限定有界样本；产出工件可人工复核 |

## 7. 与后续任务的接口

- `check resolve`、导入/扮演/战斗/理智/结团 → 后续阶段任务（在 `flow.md` 留位）。
- 独立上下文角色子代理 / 编排驱动 → I4 适配层任务。
