# 01 车卡（character-creation）

## 目标

为每位玩家角色（PC）确定一位**调查员**：生成 8 项属性与派生值，选择职业并分配技能点，
写下背景与随身物品，产出 `sheet.md`（人读）与 `sheet.json`（机读）两份卡面。

## 进入条件

- 冒险目录已由 `scaffold new --system coc7e` 生成，`flow/` 与 `rules/` 就位。
- master 已读 `AGENTS.md`、本阶段文件与 `../rules/character-creation.md`。
- 参与玩家角色（PL）已确定，其 `roles/<id>/` 目录可由 master 创建。

## 参与角色

- **master**：编排——提议并开启车卡频道、校验卡面、发布 outcome、落盘迁移；**不扮演角色**。
- **PL（玩家）**：在车卡频道内生成角色、讨论迭代、提交卡面。
- **KP（守密人）**：**不进入车卡频道**；车卡结束后由 master 把 outcome 发布到公共基线频道
  交给 KP（避免 KP 提前接触玩家 build 过程）。

## 适用规则

- 全部车卡机制见 [`../../rules/character-creation.md`](../../rules/character-creation.md)：
  属性 `3d6×5`（EDU=`(2d6+6)×5`）、派生值（HP/MP/SAN/幸运/DB·Build/MOV/年龄修正）、
  职业与技能点（`EDU×4` + `INT×2`）、判定参数（**大成功 = 1–5**）。
- 掷骰**只经** `tools/dice.py`（带 seed、可复现）；agent 不得自造随机数。
- 本阶段**不做** `check resolve` 结算（推迟到扮演/战斗阶段）。

## 退出条件

- 每位 PL 都提交了符合规则的 `roles/<id>/sheet.md` 与 `sheet.json`；
- master 校验卡面（属性可复现、派生值正确、技能点不超支、至少 8 项本职技能）通过；
- 车卡频道写入 `outcome` 并 `status=closed`；应公开的 outcome 已 publish 到公共基线频道；
- 已执行 `context compact --role <pl>`，并 `step commit` + `step tag phase/character-creation`。

## 产出

| 产出 | 位置 |
|---|---|
| 车卡频道记录 | `channels/<id>/meta.json`（purpose/participants/termination/status/outcome）+ `transcript.md` |
| 玩家角色卡（人读） | `roles/<pl>/sheet.md` |
| 玩家角色卡（机读） | `roles/<pl>/sheet.json` |
| 角色短期上下文 | `roles/<pl>/context.jsonl`（由 `context build` 投影） |
| 角色摘要 | `roles/<pl>/summary.md`（由 `context compact` 生成，可选） |
| git 边界 | commit + tag `phase/character-creation` |

## 编排（内联降级模式下 master 依此推进）

```
进入 01-车卡
  master 建车卡频道 (例: channels/ch-001-character-creation/)
    meta.json: purpose="车卡", participants=[pl1], termination="卡面提交并校验通过", status=open
    transcript.md: 记录 PL 生成/讨论/迭代
  master 为参与者建 roles/<pl>/persona.md（若缺）
  master: context build --role pl1            # 投影角色可见上下文
  PL: 读 roles/pl1/context.jsonl + ../../rules/character-creation.md
      用 tools/dice.py 掷属性/幸运（记录 seed）→ 算派生值/技能点 → 写 sheet.md/json
      在频道 transcript 内讨论/迭代
  master: 校验卡面 → step commit -m "character: pl1 提交卡面"
  master: 写 channel outcome（卡面摘要），status=closed
  master: 把 outcome publish 到公共基线频道 channels/baseline/transcript.md
  master: context build --role kp             # 把 outcome 交给 KP（KP 不在车卡频道）
  master: context compact --role pl1
  master: step commit -m "phase: 车卡完成" + step tag phase/character-creation
退出 01 → （02 导入及后续阶段尚未实现；冒烟到此为止）
```

## 内联降级说明

无 `spawn-subagent` 时，master 在**同一上下文内联扮演** PL。文件位置与投影仍生效
（`context build` 照常产出），隔离退化为「可见性纪律」——这是已知代价，不阻断跑通。
