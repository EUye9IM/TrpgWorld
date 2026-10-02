# design.md — TrpgWorld 协议框架技术设计

> 本文件是 `prd.md` 的技术设计展开。决策编号沿用 PRD 的 D1–D10。

## 1. 架构总览

系统分两部分：

```
① 框架仓库 (TrpgWorld 项目本身)          ② 冒险目录 (编译产物, 每份模组一个)
   工具库 + 脚手架 + 模板 + 规则 + 示例       自包含 / 自描述 / 自运行 / git 管理
   ─────────────────────────────           ─────────────────────────────
   编译 (build-time)  ───────────────────▶  推进 (play-time)
```

- **框架仓库不持有任何游戏实例**，只提供能力与模板。
- **冒险目录是运行单元**：任意 agent 读它的入口说明即可开跑（D5/R2）。
- **适配层（Pi/dsh 插件）不属于这两者**：它是宿主侧的能力提供者，不解读冒险目录（D6/R12）。

## 2. 原语模型

| 原语 | 定义 | 关键字段/职责 |
|---|---|---|
| **Master** | 流程引擎/导演，**不是角色** | 读 flow；编排 channel；与 KP 协商场景；触发 commit/tag；不扮演角色 |
| **Role** | 对称角色（GM/KP、PL、NPC） | `persona`（设定）、`context`（短期记忆）、`memory`（长期）、`sheet`、可用 `tools` |
| **Channel** | 有界的场景/交互 | `purpose`、`participants`、`termination`、`outcome`（纪要） |
| **Flow** | 阶段程序（跨模组复用） | 阶段列表 + 迁移条件 + 每阶段参与角色/适用规则；阶段粒度强制、阶段内自由 |
| **System（规则系统）** | 机制层 | 规则说明 + 工具绑定 + 默认 flow（如 `coc7e`） |
| **Module** | 剧情内容 | 场景/线索/NPC/`hooks`（对 flow 阶段的覆盖） |
| **Tool** | 确定性 CLI | 随机、状态变更、投影、压缩、git 步进、判定结算 |
| **World State** | 共享真相（剧情层） | 时间、地点、旗标、NPC 状态、线索发现情况 |

**关键原则**：Master 推进流程但不扮演角色；角色对称；角色由 agent 或人类担任是可替换的（前期全 agent）。

## 3. 目录契约

### 3.1 框架仓库（推荐默认，可 fork）

```
TrpgWorld/
├─ README.md                 # 中文简介（首份交付物之一，R13）
├─ docs/                      # 中文正式协议文档（首份交付物，R13）
│   ├─ protocol.md           #   协议总览：原语、生命周期
│   ├─ directory.md          #   目录契约：框架与冒险目录结构
│   ├─ tooling.md            #   工具 CLI 契约 + git 步进契约
│   ├─ visibility.md         #   可见性/秘密隔离/上下文投影
│   └─ capabilities.md       #   宿主能力声明与降级
├─ tools/                    # 确定性 CLI 工具（模板源）
├─ templates/adventure/      # 冒险目录脚手架模板（含 AGENTS.md 模板）
├─ systems/coc7e/            # 规则系统：规则说明 + 默认 flow + 判定工具
├─ examples/soup/            # 示例：由 soup.md 编译出的冒险目录
└─ adapters/                 # （后期）Pi/dsh 能力提供者，非本阶段
```

### 3.2 冒险目录（编译产物）

```
<adventure>/
├─ AGENTS.md            # 【必需·唯一不变量】自描述入口：如何读本目录、如何推进
├─ flow/                # 阶段程序（来自 system，可按本模组微调）
├─ rules/               # 规则（从框架带入并裁剪）
├─ module/              # 编译后的模组内容
│   ├─ overview.md
│   ├─ scenes/          #   拆分后的场景
│   ├─ clues.md
│   ├─ npcs/
│   └─ hooks.md         #   对 flow 阶段的钩子/覆盖（如毒湯 1 小时倒计时）
├─ roles/<id>/          # 角色（记忆层）
│   ├─ persona.md
│   ├─ context.jsonl    #   短期记忆（实际发给 LLM 的 messages 数组）
│   ├─ summary.md       #   滚动摘要
│   ├─ memory.md        #   长期笔记（关系/线索/秘密）
│   └─ sheet.*          #   角色卡
├─ channels/<id>/       # 场景记录（可见层）
│   ├─ meta.json        #   purpose / participants / termination / status
│   └─ transcript.md    #   对话转录
├─ world/               # 共享世界状态（真相层）
├─ log/                 # 系统事件审计（工具调用/状态变更/提交；角色不可见，不用于恢复）
├─ tools/               # 内嵌的确定性工具（可 fork）
└─ .git/                # 历史 / tag / 恢复 / 分叉
```

**可省略**：`summary.md`、`log/`、`rules/` 可按需；**不可省略**：`AGENTS.md`（自描述入口）。

## 4. 编译工作流（build-time）

1. 用户提供原始模组（markdown 等）。
2. agent 读 `docs/` + `templates/adventure/` 的脚手架指令。
3. 生成冒险目录骨架，`git init`。
4. **解析模组**：拆分场景 → `module/scenes/`；提取线索 → `clues.md`；NPC → `npcs/`；模组特例 → `hooks.md`。
5. **定制 flow**：默认取 `systems/coc7e/flow`，按模组特性用 `hooks` 覆盖个别阶段（不改 flow 本体）。
6. **按模组特性微调目录**（可增删目录/文件，可改造工具）。
7. 生成 `AGENTS.md`：自描述「本目录结构与推进方式」。
8. `tools/step commit --tag compile/<module>` 落盘初始提交。

> 编译产物的自描述性由 AC1 验证；agent 对目录的二次开发属于 R11 允许范围。

## 5. 推进工作流（play-time，单步循环）

```
master 读 AGENTS.md + flow            # 定位当前阶段
  ↓
按 flow 阶段决定下一个场景
  ↓
【协商】master 提议 {purpose, participants} → KP 修订 → master 校验并开 channel
  ↓
【运行】参与者子代理各自基于「自己的 context 投影」在 channel 中交互
  ↓
【裁决】需要判定时调用 rules 工具（判定结算）；叙事决定由角色做
  ↓
【副作用】工具写 world/、log/，并把 channel transcript 落盘
  ↓
【结束】master 判定 termination → 生成 channel outcome（纪要）
  ↓
【同步】master 将应公开的 outcome publish 到公共基线频道
  ↓
【记忆】context compact：短期溢出 → summary；更新各角色 memory/context
  ↓
【步进】tools/step commit（每条消息/每步）+ 阶段边界打 tag
  ↓
进入下一场景，或 flow 迁移到下一阶段，直到「结团」
```

**车卡场景**（R5 示例）：master 编排多个 PL 共同讨论，PL 提交卡面后才把结果交给 KP。
**秘密团场景**：master 编排 KP + 特定 PL，其余待机 PL 不进入该 channel。

## 6. 可见性 / 秘密隔离

**隔离由文件位置 + 投影工具保证，不靠角色自律（R8）。**

- 场景内容只存于 `channels/<id>/`；未进入该 channel 的角色不会被喂到。
- 角色上下文由确定性工具投影得到：

```
tools/context build --role <id>   # 读 channels 中该角色参与的 + world 中可见的 + 自身 memory
                                  # → 生成 roles/<id>/context.jsonl（可见层）
```

- 角色/子代理**只读自己的 `context.jsonl`**，不读 `log/`、不读他人 `roles/`、不读全量 `channels/`。
- 秘密骰：工具将点数写入受限位置（不进入公共 transcript），对外只发「可公开的结果事件」。
- **降级模式**：无子代理隔离能力时，master 在同上下文内联扮演，隔离退化为「可见性纪律」，为已知代价（AC5）。

## 7. 工具契约（R7/D8）

所有工具为宿主无关 CLI：**参数/标准输入 → 标准输出（JSON）+ 文件写入 + 审计写入**。

| 工具 | 职责 | 副作用 |
|---|---|---|
| `dice roll` | 带种子的随机源（可复现） | 写 `log/`，返回结果 |
| `check resolve` | CoC 判定结算（成功等级/对抗/SAN/伤害） | 写 `log/` |
| `state get/set` | 读写 `world/` 共享状态 | 写 `world/`、`log/` |
| `context build` | 由 channel/world/memory 投影角色可见上下文 | 写 `roles/<id>/context.jsonl` |
| `context compact` | 短期溢出 → 摘要 | 写 `summary.md`、更新 `context.jsonl` |
| `step commit` | git add/commit（串行） | git 提交 |
| `step tag` | 打边界 tag | git tag |
| `scaffold new` | 由模板生成冒险目录骨架（build-time） | 创建目录、`git init` |

**约定**：工具输出即真相；每次调用记录到 `log/`；git 操作只由 `step *` 串行执行，避免 `index.lock` 竞争。

## 8. 持久化 / 恢复 / 回滚（D9）

- **真相 = 冒险目录的工作树**；**历史 = git 提交**。
- **恢复** = `git checkout <commit>` 后继续（**不重放 log**；`log/` 仅供审计，不参与恢复）。
- **提交粒度 = 每条消息/每步**；**边界 tag** 标记场景与 flow 阶段（如 `scene/003-central-room`、`phase/combat`）。
- **回滚语义**：
  - A1 撤销 = `git reset --hard <commit>`（默认）。
  - A2 分叉 = `git branch <new-timeline> <commit>`（旧线保留，git 原生支持，零额外代码）。
- git 优化：`core.fsyncObjectFiles=false` 本地可接受；定期 `git gc`。

## 9. 记忆分层与压缩（R10）

| 层 | 位置 | 生命周期 |
|---|---|---|
| 短期 | `roles/<id>/context.jsonl` | 最近 N 轮，超出即压缩 |
| 摘要 | `roles/<id>/summary.md` | 场景级滚动摘要 |
| 长期 | `roles/<id>/memory.md` + `sheet.*` | 全场持久 |

场景结束触发 `context compact`，控制上下文体积（避免长跑团膨胀）。

## 10. 宿主能力与降级（R2/R12）

协议声明**能力需求**，宿主提供则用、缺则降级：

| 能力 | 用途 | 缺失时降级 |
|---|---|---|
| `spawn-subagent` | 每角色独立上下文子代理 | master 内联扮演，隔离靠纪律 |
| `human-input` | 人类担任角色 | 不支持（前期全 agent） |
| `context-isolation` | 强制隔离角色上下文 | 文件位置 + 投射仍生效，但同上下文内可能泄漏 |
| `tool-gating` | 按角色限制可用工具 | 约定遵守 |

**适配层只提供能力，不解读目录**（D6）：Pi/dsh 插件暴露上述能力；目录始终由 LLM 读。缺失能力不得阻止一场团跑通（仅影响隔离强度）。

## 11. 权衡与风险

| 风险 | 说明 | 缓解 |
|---|---|---|
| 投影泄密 | `context build` 是安全关键路径 | 做成确定性工具 + AC3 验证 |
| 降级泄漏 | 内联模式无强制隔离 | 文档标注为已知代价；优先有子代理的宿主 |
| 每消息提交噪音 | `git log` 难导航 | 边界 tag + 结构化 commit message |
| 并行写冲突 | 多 channel 并发 git | git 操作统一由 `step *` 串行 |
| 上下文膨胀 | 长跑团记忆爆炸 | 三层记忆 + 场景末压缩 |
| 模组特性差异 | 固定结构放不下特例 | hooks 覆盖 + 目录可 fork（R11） |

## 12. 兼容与迁移

- 旧的 Python/LangGraph 实现已按 R14 **从工作树删除**（仅保留 `modules/` 原始模组）。
- 旧实现完整保留在 git 历史提交 `ed80ff4`、`2fc6819` 中，可随时 `git show` / `git checkout` 取回。
- 迁移映射（规则/判定/车卡/模组解析如何对应到新协议）见 `research/legacy-inventory.md`。
- `systems/coc7e/` 工具、编译期模组解析可参考旧 `src/systems/coc/`、`src/module/reader.py`（从 git 历史取回）。
