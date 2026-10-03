# 毒湯 — 冒险目录

> 本目录由 TrpgWorld 脚手架（`scaffold new`）从 `/home/otix/projects/TrpgWorld/modules/soup.md` 编译生成于 2026-10-03T03:48:03+00:00。
> **本文件是唯一硬性不变量**：任意 agent 只要读本文件，就应能理解如何运行与推进本冒险目录。

## 1. 这是什么

这是一个**自包含、自描述、自运行**的 TRPG 冒险目录。它把一份原始模组编译成结构化文件：
场景、线索、NPC、阶段流程、角色记忆、场景转录、世界状态与确定性工具都在这里。

- 框架与协议见 TrpgWorld 仓库的 `docs/`（`protocol.md` / `directory.md` / `tooling.md` / `visibility.md`）。
- 本目录**不依赖**框架仓库即可运行；`tools/` 已内嵌全部确定性工具，可自由 fork 改造。

## 2. 前置条件

- **推荐**：安装 [`uv`](https://docs.astral.sh/uv/)，用 `uv run tools/<tool>.py ...` 运行工具
  （PEP 723 内联元数据，无需 venv / pyproject / 安装）。
- **回退**：所有工具均为纯标准库 Python 单文件，无 `uv` 时可直接
  `python3 tools/<tool>.py ...`。

## 3. 目录结构

```
soup/
├─ AGENTS.md        # 本文件：自描述入口
├─ flow/            # 阶段程序（来自 system，可按本模组微调）
├─ rules/           # 规则（可裁剪）
├─ module/          # 编译后的剧情内容
│   ├─ overview.md  #   总览
│   ├─ scenes/      #   场景
│   ├─ clues.md     #   线索
│   ├─ npcs/        #   NPC 设定
│   └─ hooks.md     #   对 flow 阶段的钩子/覆盖
├─ roles/<id>/      # 角色：persona.md / context.jsonl / summary.md / memory.md / sheet.*
├─ channels/<id>/   # 场景记录：meta.json / transcript.md
├─ world/           # 世界状态：state.json（真相）+ visibility.json（可见性 mask）
├─ log/             # 工具调用审计（events.jsonl）；角色不可读，不参与恢复
└─ tools/           # 内嵌确定性工具（可 fork）
```

## 4. 编译产物速览

- 模组：**毒湯**（slug: `soup`）
- 规则系统：`coc7e`（`flow/` 与 `rules/` 来自 `systems/coc7e/`）
- 场景（`module/scenes/`）：
  - `001-一開始的房間.md` — 3. 一開始的房間
  - `002-東邊房間（奴隸的房間）.md` — 4. 東邊房間（奴隸的房間）
  - `003-西邊房間（書庫）.md` — 5. 西邊房間（書庫）
  - `004-北邊房間（廚房）.md` — 6. 北邊房間（廚房）
  - `005-南邊房間（禮堂）.md` — 7. 南邊房間（禮堂）
  - `006-噩夢現在才要開始？.md` — 9. 噩夢現在才要開始？
- NPC（`module/npcs/`）：
  - `絕對忠實少女（NPC）.md` — 絕對忠實少女（NPC）
  - `保護書本的黑色液狀生物（札特瓜的無形眷屬）.md` — 保護書本的黑色液狀生物（札特瓜的無形眷屬）
  - `恐懼獵人（守衛）.md` — 恐懼獵人（守衛）
  - `來自山丘的恐怖——夏烏戈納爾・法格恩（Chaugnar-Faugn）.md` — 來自山丘的恐怖——夏烏戈納爾・法格恩（Chaugnar Faugn）
- 线索：`module/clues.md`（28 条，已自动抽取，需 master/KP 复核整理）

## 5. 如何运行工具

所有工具的标准输出都是 JSON，并会把每次调用追加到 `log/events.jsonl`。
`--adventure <path>` 可显式指定本目录；缺省从当前目录向上查找 `AGENTS.md`。

```bash
# 随机源（同 seed 同结果；agent 不得自造随机数）
uv run tools/dice.py roll --expr 1d100 --seed 42

# 世界状态（仅 master / 系统工具可直接读写；角色不得直接 state get）
uv run tools/state.py set timer.remaining_minutes 55
uv run tools/state.py get timer.remaining_minutes
uv run tools/state.py mask --role pl1      # 审计该角色可见/隐藏的状态路径

# 角色上下文投影（安全关键：只投影该角色参与的频道 + mask 过滤后的世界状态）
uv run tools/context.py build --role kp
uv run tools/context.py build --role pl1
uv run tools/context.py compact --role pl1 --keep 20

# git 步进（唯一 git 入口，串行，避免 index.lock）
uv run tools/step.py commit --message "scene: 中央房间调查" --tag scene/003-central-room
uv run tools/step.py tag phase/combat
```

每个工具的 `--help` 都写明输入、输出、副作用与退出码；退出码约定：`0` 成功、`1` 业务失败、`2` 用法错误。

## 6. 如何推进一场团

1. **主体（master）**读 `module/overview.md` 与 `flow/`，按阶段推进；master 不是角色。
2. 需要交互时，master **提议**场景 `{purpose, participants}`，开启 `channels/<id>/`
   （写 `meta.json` 的 `purpose` / `participants` / `termination` / `status`，并维护 `transcript.md`）。
3. 每个角色**只读自己的** `roles/<id>/context.jsonl`：
   - 不得读 `log/`、他人 `roles/`、全量 `channels/`；
   - 需要新上下文时，由 master 执行 `context build --role <id>` 重新投影。
4. 场景结束时，master 把应公开的 `outcome` 发布到公共基线频道；随后
   `context compact --role <id>` 把短期溢出压进 `summary.md`。
5. 每步用 `step commit` 落盘；场景/阶段边界用 `step tag` 打 tag。
6. 推进到 `module/overview.md` 描述的结局/结团条件即结束。

## 7. 可见性与秘密隔离

- 秘密靠**文件位置 + 投影工具**隔离，不靠角色自律。
- `world/state.json` 是全部真相；`world/visibility.json` 是声明式 mask：
  `{"default": "public", "rules": [{"pattern": "/secrets/**", "audience": ["kp"]}]}`。
  路径 glob：`*` 一层、`**` 子树；规则**首个命中定档**，否则用 `default`；`public` 表示所有人可见。
- 角色只能读 `context build` 产出的投影；`state get/set` 仅限 master / 系统工具。

## 8. git 语义

- 工具输出即真相；真相 = 工作树，历史 = git 提交。
- 提交粒度 = 每条消息/每步；场景与 flow 阶段边界必须打 tag。
- 恢复 = `git checkout <commit>` 后继续（**不重放 `log/`**）；审计日志仅供排查。
- 回滚：`git reset --hard <commit>`（撤销）或 `git branch <new-timeline> <commit>`（分叉）。

## 9. 本模组的钩子

见 `module/hooks.md`（模组对 `flow/` 阶段的覆盖，例如计时/特殊规则）。
