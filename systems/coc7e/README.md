# CoC 7e 规则系统（`systems/coc7e`）

本目录是「克苏鲁的呼唤 第七版（Call of Cthulhu 7th Edition）」的一个可运行规则系统子集。
它把**机制（rules）**与**阶段程序（flow）**打包在一起，供 `scaffold new --system coc7e`
带入一份冒险目录。

## 1. 内容

```
systems/coc7e/
├─ README.md                       # 本文件：规则系统说明、如何被 scaffold 带入
├─ rules/
│   └─ character-creation.md       # 车卡规则：属性 / 派生值 / 职业与技能 / 判定参数 / 卡面格式
├─ flow/
│   ├─ flow.md                     # 阶段索引（01 车卡已实现，02–06 后续待补）
│   └─ phases/
│       └─ 01-character-creation.md# 车卡阶段：目标 / 进入 / 参与角色 / 适用规则 / 退出 / 产出 + 编排
└─ tools/                          # 判定工具（本阶段为空；check resolve 推迟到扮演/战斗阶段）
    └─ .gitkeep
```

> **范围说明（I3）**：本任务只实现**车卡阶段**。导入 / 扮演调查 / 战斗 / 理智 / 结团阶段、
> 以及 `check resolve` 的完整结算，都在 `flow.md` 中留位，由后续任务补齐。

## 2. 如何被 scaffold 带入

`scaffold new --system coc7e`（或 `--system <name> --systems-dir <dir>`）会：

1. 按 I2 原流程生成冒险目录骨架并解析模组；
2. 把 `systems/coc7e/flow/` 的内容复制到冒险 `flow/`（覆盖模板占位）；
3. 把 `systems/coc7e/rules/` 的内容复制到冒险 `rules/`；
4. 把 `systems/coc7e/tools/*` 复制到冒险 `tools/`（与源**逐字节一致**）；
5. 在冒险 `AGENTS.md` 注明所用规则系统。

不带 `--system` 时行为与 I2 完全一致（带入模板占位 `flow/`、`rules/`）。

## 3. 与协议的对应

- **机制**落在 `rules/`，**阶段程序**落在 `flow/`，二者分层正交（见 `docs/directory.md` §3.3）。
- 随机源与状态变更**只经确定性工具**（`tools/dice.py` / `tools/state.py`）；规则文档只描述
  **机制与参数**，不含硬编码引擎，执行由 agent + 工具完成（见 `docs/tooling.md` §1）。
- 模组可用 `module/hooks.md` 覆盖个别阶段（例如《毒湯》的一小时倒计时），而不改写 `flow/` 本体。
- 阶段边界用 `step tag phase/<name>` 标记（当前实现：`phase/character-creation`）。
