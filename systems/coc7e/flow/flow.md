# flow —— CoC 7e 阶段程序

> 本目录是 CoC 7e 的**阶段程序（flow）**：一场团分成哪些阶段、各阶段如何进入/退出、
> 以及阶段之间的迁移。master 读本文件与 `phases/*.md` 推进；模组特性通过
> `../module/hooks.md` **覆盖**个别阶段，而不改写本目录本体。
>
> 实现进度：**01 车卡已实现**；02–06 标「后续待补」（后续任务补齐）。

## 1. 阶段索引

| # | 阶段 | slug | 状态 | 文件 |
|---|---|---|---|---|
| 01 | 车卡 | `character-creation` | ✅ 本任务 | [`phases/01-character-creation.md`](phases/01-character-creation.md) |
| 02 | 导入 | `introduction` | 后续待补 | — |
| 03 | 扮演/调查 | `investigation` | 后续待补 | — |
| 04 | 战斗 | `combat` | 后续待补 | — |
| 05 | 理智 | `sanity` | 后续待补 | — |
| 06 | 结团 | `ending` | 后续待补 | — |

## 2. 推进模型

- **master 不是角色**：它只提议场景、开启 `channels/`、驱动迁移；角色（KP / PL / NPC）
  一视同仁，各自只读自己的 `roles/<id>/context.jsonl`。
- 进入某阶段时，master 读对应 `phases/NN-*.md`，按其中的「编排」开启 channel、投影上下文、
  维护 transcript、结束并发布 outcome。
- **未知阶段（后续待补）不阻断**：若 flow 指向尚未实现的阶段，master 按 `module/hooks.md`
  与叙事自行裁定，但须在 `log/` 与 commit message 中注明「阶段未实现，手工接管」。

## 3. 阶段迁移约定

```
01 车卡 ──（本任务终点）──▶ 02 导入 ──▶ 03 扮演/调查 ──▶ 04 战斗 ──▶ 05 理智 ──▶ 06 结团
```

- 每个阶段的**退出条件**写在对应 `phases/*.md`；满足即由 master 落盘并迁入下一阶段。
- 阶段边界必须：`context compact` 相关角色 → `step commit -m "phase: <阶段>完成"` →
  `step tag phase/<slug>`，随后把应公开的 outcome publish 到公共基线频道 `channels/baseline/`。
- **模组钩子**：若 `module/hooks.md` 定义了计时/特殊规则（如《毒湯》一小时倒计时），
  它在整个 flow 上叠加，可跨阶段生效，并可覆盖某阶段的退出条件。

## 4. 真实与虚构

- 随机源（骰子）、状态变更、判定结算**只经确定性工具**；叙事由 agent 裁决，但不得覆盖工具输出。
- 阶段迁移等结构性动作以 git 提交与 tag 为准；`log/` 仅供审计，不参与恢复。
