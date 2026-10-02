# 旧实现清点（迁移参考）

> 本文件供 I1 文档的「兼容与迁移」章节，以及后续 I2/I3 参考。**旧实现已按 R14 从工作树删除**，下表是清点与恢复入口。

## 目录 / 文件

| 路径 | 作用 | 新协议中的去向 |
|---|---|---|
| `main.py` | 入口：装配 LLM + engine，打印角色创建结果 | 由 agent 读 `AGENTS.md` 取代 |
| `src/core/agent.py` | 自写 LLM 工具调用循环（litellm + langchain messages） | 由宿主 agent 原生工具循环取代 |
| `src/core/types.py` | Pydantic：`CoCCharacter` / `GameState` / `GMResponse` / `PlayerAction` 等 | 拆入 `roles/<id>/sheet.*`、`world/`、channel meta |
| `src/game/engine.py` | LangGraph 状态机 `load_module → gm ↔ pl → log` | 由 `flow/` 阶段程序 + master 取代 |
| `src/game/state.py` | 初始 GameState | 由 `world/` + `roles/` 初始化取代 |
| `src/game/log.py` | 会话日志落盘 | 由 `channels/` + `log/` 取代 |
| `src/module/reader.py` | markdown 按标题切段、检索 | 编译期「解析拆分模组」的起点 |
| `src/systems/coc/dice.py` | CoC 骰子/判定 | `tools/dice` + `tools/check` 参考实现 |
| `src/systems/coc/skills.py` | 技能表、职业表 | `systems/coc7e/` 规则数据参考 |
| `src/systems/coc/character.py` | 车卡：属性投掷、技能分配 | `flow` 车卡阶段 + `roles/<id>/sheet.*` |
| `src/systems/coc/rules.py` | 职业校验、角色状态格式化 | `systems/coc7e/` 规则工具参考 |
| `src/systems/coc/prompts.py` | GM/PL 提示词 | 编译期生成 `AGENTS.md` / `roles/<id>/persona.md` 的素材 |
| `src/systems/coc/gm.py` / `pl.py` | GM/PL 回合逻辑（硬编码流程） | 由 master 编排 channel + 角色 context 取代 |
| `tests/test_agent.py` / `test_tool_chain.py` | 旧工具循环测试 | 新协议暂无对应用例；工具落地后另建 |
| `modules/soup.md` | 原始模组《毒湯》 | **保留**，I3 示例编译输入 |
| `modules/example.md` | 原始模组示例 | **保留**，编译输入 |
| `logs/` | 旧运行日志（生成物） | **R14 删除** |
| `__pycache__/`、`.pytest_cache/` | 缓存（生成物） | **R14 删除** |

## 关键结论

- 旧实现已从工作树删除（R14），全部信息保留在 git 历史（`ed80ff4`、`2fc6819`）中；取回方式：`git show ed80ff4:<path>`。
- `docs/` 的「兼容与迁移」章节应引用本表，说明规则/判定/车卡逻辑如何映射到新协议。
- 工作树仅保留 `modules/soup.md`、`modules/example.md` 作为示例编译输入。
