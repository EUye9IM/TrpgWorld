# 宿主插件「角色运行时能力契约」批判性审查

> 审查对象：I4 提案的 C1–C10 角色运行时能力契约（spawn_role / tool_policy / exec_tool /
> session_policy / notify / capability_report / no_leak / audit）。
> 任务：`.trellis/tasks/10-04-i4-host-plugins`。
> 立场：**独立、诚实、以证据为准**。本文件明确区分「证据」与「推断」。

---

## 0. 结论先行（TL;DR）

**总体裁决：方向正确，但契约不足以支撑「机制化保证可见性」的目标，且当前不成体系。**

1. **C9a（no_leak，安全核心）的表述是错的/不完整的。** 提案写「靠**工具限制**保证角色读不到未授权数据」。
   证据表明：**工具限制既不充分也不必要**——真正会泄漏的是「角色进程/子代理被自动注入的上下文」，
   而不是「它主动去读的文件」。Pi 与 dsh 都会在没有显式关闭时把工作区 `AGENTS.md` 自动喂进子代理；
   而 `examples/soup/AGENTS.md:43-55` 恰好列出了「毒湯」全部场景名与 NPC 名（含
   「札特瓜的無形眷屬」「恐懼獵人（守衛）」），对一场推理团是直接剧透。**这不是工具能拦住的**。
   → C9a 必须改写为「**上下文注入面隔离**（context-surface isolation）」，工具限制只是其中的一条。

2. **契约存在一处危险设计：`exec_tool(cmd)`。** 以「命令字符串」为参数会在角色侧重新打开任意命令执行面，
   与 C2「不给 bash」自相矛盾。且提案把 `context build` / `step` 列为角色可调用——这两者都会泄漏/破坏：
   `context build --role <任意>` 的输出含 `worldPaths`（`tools/context.py:151`），
   `state mask --role` 会枚举隐藏路径；`step commit/tag` 可改写 git 历史。
   → 改为 `exec_tool(name, args)`，角色侧**封闭白名单 = {dice, check}**。

3. **契约缺「角色读授权参考材料」这条路。** 流程明确要求 PL 读规则：
   `systems/coc7e/flow/phases/01-character-creation.md:56`「PL: 读 roles/pl1/context.jsonl +
   ../../rules/character-creation.md」。但 `context build` 只投影
   persona/memory/summary/sheet/channels/world（`tools/context.py:74-99`），**不含 `rules/`**；
   而 C2 又不给 fs。两者冲突 → 要么投影器纳入授权规则，要么新增**路径受限的 `role_read`**。
   这是「能力缺口」，不是实现细节。

4. **内存模型自相矛盾。** C4 采用「无状态 fresh」，但 R10 依赖 `context compact` 把溢出压进 `summary.md`。
   `context build` 每次都会把参与频道的**全量** transcript 重新拼进投影（`tools/context.py:90-128`），
   于是 compact 之后的 build 会**再次**把旧内容拼回来，形成「压缩→重放→再压缩」的膨胀循环。二者需二选一。

5. **Pi 与 dsh 都能近似覆盖契约，但分叉点明确**：
   - Pi：靠「独立子进程 + CLI 旗标」实现隔离；**默认不安全**（官方 subagent 示例与本仓库
     `trellis` 扩展都不传 `--no-context-files`/`--no-extensions`）。
   - dsh：`ctx.subagents` + `spawn`（`inheritsParentContext=false`）+ `toolFilter` + `persona` +
     `agentOptions` + `maxDepth` 几乎是契约的**逐条对应物**；但 `dsh-agent-instructions` 的
     AGENTS.md 注入**不受 toolFilter 约束**，且「子代理加入父组合」——所以「干净角色」需要
     独立的 role profile/composition 或 out-of-process。

**一句话**：契约应该从「工具白名单」升级为「**三层隔离模型**：注入面隔离 + 工具门控 + 会话/进程边界」，
并补齐模型路由、超时、成本、递归上限、受限读取、隔离自证/金丝雀测试。

---

## 1. 证据来源与方法

### 1.1 本仓库（已读）

| 证据 | 关键内容 |
|---|---|
| `docs/protocol.md` §2.2/§3 | 单步循环、Channel、Role、Tool 原语；「角色子代理各自基于自己的 context 投影交互」 |
| `docs/visibility.md` §2/§2.1/§3/§4 | 投影规则、声明式 mask、秘密骰、`context compact` |
| `docs/capabilities.md` §2/§3/§4 | 4 项宿主能力 + 降级矩阵；**本阶段（I1）不实现插件** |
| `docs/tooling.md` §1–§4 | 工具契约；「角色不得直接调用 `state get`」「工具输出即真相」 |
| `docs/directory.md` §3 | 冒险目录结构；`AGENTS.md` 是唯一硬性不变量 |
| `tools/context.py` | `load_channels` L43-66；`build_messages` L68-133；输出 `worldPaths` L151；始终拼接全量 transcript L121-128 |
| `tools/_lib.py` | `read_visibility` L355-361（缺文件 → `default: public`，**fail-open**）；`safe_id`；`match_path`；`build_projection` |
| `tools/dice.py` | **无 secret 模式**；结果与 seed 都写 `log/events.jsonl` |
| `tools/state.py` | `state mask --role` 打印可见/隐藏路径（审计，也即泄漏面） |
| `tools/step.py` | git 串行入口（角色不可用） |
| `systems/coc7e/flow/phases/01-character-creation.md:56` | PL 被要求读 `rules/character-creation.md` |
| `examples/soup/AGENTS.md:43-55` | 自动注入的 AGENTS.md 内含模组名/场景名/NPC 名（剧透） |
| `examples/soup/world/visibility.json` | 当前是空规则 + `default: public`（模板占位） |
| `systems/coc7e/tools/.gitkeep` | **`check resolve` 尚未实现**（`ls tools/` 只有 context/dice/state/step/scaffold） |
| `.pi/extensions/trellis/index.ts:703-716` | `buildPiArgs` 只传 `--mode json -p --no-session [--model] [--tools]`，**不传** `--no-context-files`/`--no-extensions` |
| `.pi/agents/trellis-research.md` | agent frontmatter 支持 `tools:` / `model:` |

### 1.2 Pi（已读文档/示例/CLI）

| 证据 | 关键内容 |
|---|---|
| `pi --help` | `--no-context-files`、`--no-session`、`--no-extensions`、`--no-skills`、`--no-prompt-templates`、`--tools`、`--system-prompt`、`--append-system-prompt`、`--mode json`、`--print` |
| `docs/cli.md:128` | `--tools` **替换**整个选择：必须列全想要的全部工具 |
| `docs/cli.md:196-197` | `-ne` 关闭已发现/已配置/内置扩展；显式 `-e` 仍加载 |
| `docs/cli.md:212-213` | `-nc` 关闭 `AGENTS.md`/`CLAUDE.md` 发现 |
| `docs/security.md:57` | 「Context files … load **regardless of project trust unless you disable context loading**」 |
| `docs/security.md` §choose | 「工作目录**不阻止**命令访问其它路径」；隔离靠 OS/容器 |
| `docs/extensions.md` §tools | `exposure`、`ctx.executeTool`、`prepareLoadout`；扩展与 pi 同权限 |
| `docs/environment-variables.md` | `PI_CODING_AGENT_DIR` 覆盖配置目录（可指向空目录以隔绝用户级扩展/skills/MCP/trust） |
| `examples/extensions/subagent/index.ts:300-338` | 官方子代理同样只传 `--no-session --model --thinking --tools`，并用 **`--append-system-prompt`**（默认编码助手 system prompt 仍在） |
| `examples/extensions/sandbox/index.ts:1-40` | 仅对 **bash** 做 OS 沙箱（@anthropic-ai/sandbox-runtime）；无「受限 read」 |
| `examples/extensions/subagent/agents/*.md` | persona/tools/model 用 frontmatter 声明 |

### 1.3 dsh（实际查证，非 `.dsh/DSH.md`）

> `.dsh/DSH.md` 说「dsh 无子代理面」——**该说法与实际安装的包不符**，仅代表 Trellis 未为 dsh 提供 agent prompt，
> 不代表 dsh 能力边界。以下为直接证据。

| 证据 | 关键内容 |
|---|---|
| `ls ~/.dsh/profiles/node_modules/@deepseek-ai/` | 存在 `dsh-subagent`、`dsh-subagent-spawn-in-process`、`dsh-subagent-fork-in-process`、`dsh-tool-subagent`、`dsh-tool-subagent-control`、`dsh-client-ui-subagent` |
| `dsh-subagent-spawn-in-process/lib/index.js:15-31` | spawn provider：`capabilities={agentOptions,outputSchema,depthLimit,toolFilter,persona}`，`inheritsParentContext=false` |
| `dsh-tool-subagent/README.md:52,63` | `toolFilter`（每子全局工具限制）、`persona`、`maxDepth`（默认 3，0 禁止委托）、`backgroundMode` |
| `dsh-tools/lib/types/index.d.ts:475-480` | `ToolRestriction { allow?: string[]; deny?: string[] }` |
| `dsh-subagent/lib/types/child-agent.d.ts:73-76` | 每子 `persona`、`toolFilter` |
| `dsh-subagent/README.md`（Model Experience） | 子代理注入固定句：「你的权限范围在启动时固定，无法从会话内部扩大」 |
| `dsh-agent-instructions/README.md:32` | **首个请求注入** `$DSH_HOME/AGENTS.md` + 项目链 `AGENTS.md`/`CLAUDE.md`（因 `dsh-base` 默认启用） |
| `dsh-agent-instructions/lib/types/config.d.ts:13` | `maxBytes` 非正/非有限 → **禁用加载** |
| `dsh-base/cordis.patch.yml` | 默认挂载 `tool-bash`、`tool-fs`、`tool-fs-search`、`tool-web`、`agent-instructions`、`skill`、`subagent`、`tool-subagent`、`sandbox(workspace-write)`、`approval(ask)` |
| `dsh-agent-presets/README.md` | 「**子代理加入父组合**，看到与父相同的工具/提示段」；preset roots 可配置（可指向项目目录） |
| `dsh-fs-sandbox/package.json` | 「**reads pass through**，仅按 sandbox mode 限制 write/edit」 |
| `dsh-sandbox-local/README.md` | bwrap/Landlock/Seatbelt/ACL；bwrap profile 是「read-only host root」→ 仍可读全 host |
| `dsh/README.md` §Profiles | 组合层：bundle → `cordis.patch.yml` → `$DSH_HOME/cordis.patch.yml` → `--patch`；`dsh --profile headless "job"` 可跑一次性进程 |
| `dsh plugin --profile <name> <pnpm args>` | 插件 = profile 内的 pnpm 包；无项目级插件发现面（可 `--patch` 逐次注入） |

### 1.4 方法说明

- 命令：`task.py current --source`、`ls/find`、`dsh --help`、`dsh plugin --help`、
  `pi --help`、对 `~/.dsh/profiles/node_modules/@deepseek-ai/*` 的源码/README/types 检索。
- 未做：真实跑一次 `pi`/`dsh` 子代理端到端（成本/时间）；因此涉及「实际是否注入」处，
  凡未实测者标为**推断**或**待确认**。

---

## 2. 逐条契约裁决

| # | 能力 | 裁决 | 理由（要点） |
|---|---|---|---|
| C1 | `spawn_role(role_id, system, context, instruction?) → reply` | **修订** | 参数语义错位：`system/context` 由 master 传 blob，易注入错角色、膨胀 master 上下文、且把「投影」职责塞回 master。改为 `role_id + context_path`（由协议 CLI 产出）+ `instruction`，并补 `route/model`、`max_output_tokens`、`timeout`、`depth=0`；返回结构化 `{reply, stop_reason, usage, error}` |
| C2 | `tool_policy`（角色只拿白名单，不给 bash/fs/state） | **保留 + 强化** | 必须改为**默认拒绝**（allowlist），并显式 deny `read/grep/find/ls/bash/edit/write/bash/powershell/web/subagent/skill/todo/codemode`。dsh 用 `ToolRestriction.allow`；Pi 用 `--tools`（替换式）|
| C3 | `exec_tool(cmd)` | **修订（危险）** | `cmd` 字符串 = 命令执行面。改 `exec_tool(name, args)`，角色侧封闭集 = `{dice, check}`。**移除** `context build`/`step`（泄漏 `worldPaths`、可改 git）。缺 `check`（未实现）见 §6 |
| C4 | `session_policy`（fresh，无状态） | **保留 + 修订** | fresh 与协议「记忆在文件」一致，是正确默认；但需显式：会话必须 ephemeral（Pi `--no-session`；dsh 无持久），且与 R10 压缩循环冲突（§5）。补可选的 continuable 模式（默认关）|
| C6 | `notify/stream` | **保留（可选）** | 对 TUI/进度有意义；对 headless/MVP 非必需。建议只定义最小事件（`start/tool_call/end/error`），不纳入验收 |
| C8 | `capability_report` | **保留** | 成本极低，是降级矩阵的运行时对应物；建议**同时自报隔离不变量**（是否关 context files / 是否 ephemeral / sandbox 是否可用），作为自证 |
| C9a | `no_leak_guarantee`（靠工具限制） | **修订（核心）** | 表述错误；见 §3。改为「上下文注入面隔离」，工具限制只是其中一层 |
| C10 | `audit` | **修订/合并** | 协议 CLI 已把每次调用写 `log/events.jsonl`（`_lib.log_event`）。C10 应缩小为「宿主原生（非 CLI）工具调用必须落审计」，而非独立能力 |
| C5 | 并行 | 同意暂缓 | 但「同频道多角色」即便串行也需要**顺序与提交策略**，见 §6（C16）|
| C7 | 人类暂停 | 同意暂缓 | 与 `human-input` 能力对应；前期全 agent 不阻塞 |
| C9b | 沙箱兜底 | 建议**重估** | dsh 自带 OS 沙箱（bwrap/Landlock/Seatbelt/ACL），但**只限写/执行，读是 pass-through**——**不能**替代读隔离。故 C9b 仍非安全核心；可作 dsh 侧加分项 |

**新增（缺失但必需）**：C11 每角色模型/凭据路由；C12 超时/中断/错误契约；C13 成本/token 上限；
C14 递归深度上限（角色不得再 spawn）；C15 受限读取（规则/授权材料）；C16 角色↔频道绑定与转录回写；
C17 隔离自证 + 泄漏金丝雀测试。

---

## 3. Q2：C9a 的漏洞逐条排查（核心）

> 判定标准：角色最终「看到」的内容 = 宿主注入的 system prompt + 上下文消息 + 工具返回值。
> 只堵「工具」不堵「注入面」= 漏。

| # | 泄漏路径 | 是否真实 | 证据 | 结论 |
|---|---|---|---|---|
| L1 | 自动加载工作区 `AGENTS.md`/`CLAUDE.md` | **是** | Pi `docs/security.md:57`（除非 `--no-context-files`）；dsh `dsh-agent-instructions/README.md:32` | **高危**。`examples/soup/AGENTS.md:43-55` 含剧透。必须显式关闭 |
| L2 | 用户级/项目级扩展、skills、prompt 模板注入 | **是** | Pi 默认发现 `.pi/`、`.agents/skills`、`~/.pi/agent`；dsh 子代理「加入父组合」（`dsh-agent-presets/README`），挂 `skill`、`web`、`agent-instructions` | **高危**。需 `--no-extensions/--no-skills/--no-prompt-templates` + 干净 `PI_CODING_AGENT_DIR`；dsh 需独立 role composition |
| L3 | MCP server 注入工具/上下文 | **是** | Pi MCP 是内置扩展（`-ne` 可关，`docs/cli.md:197`）；dsh base 无 MCP 但用户 profile 可挂（实测 `web/cordis.patch.yml` 挂了 `mcp-engram`）| 中危。随 L2 一起关 |
| L4 | 继承默认「编码助手」system prompt | **是（推断自官方示例）** | 官方 subagent 用 `--append-system-prompt`（`index.ts:338`）；`trellis` 扩展根本不换 prompt | 中危。角色会以为自己是编码代理。应 `--system-prompt` 整体替换 |
| L5 | 角色残留持久会话被后续读取 | **是（可致）** | Pi 默认持久会话；不加 `--no-session` 会落 `~/.pi/agent/sessions` | 中危。fresh 模式必须 `--no-session` |
| L6 | `read`/`bash` 无路径沙箱 | **是** | Pi `docs/security.md`「工作目录不阻止访问其它路径」；dsh `dsh-fs-sandbox`「reads pass through」 | **高危**。只要给 fs/bash 就全盘可读。必须不给 |
| L7 | `context build` 泄漏他人可见路径 | **是** | `tools/context.py:151` 输出 `worldPaths`；`state mask` 枚举隐藏路径 | **高危（若暴露给角色）**。角色侧不得可调用 |
| L8 | `context build` 投影自身漏 | **部分** | `_lib.read_visibility` L355-361：**缺 `world/visibility.json` → default=public（fail-open）**；`hidden` 状态在无规则时全可见 | **中危**。应改为 fail-closed：有 `state.json` 而无 `visibility.json` 时报错或默认仅 master |
| L9 | 模型 provider 隐藏上下文/服务端会话 | **待确认** | Pi/dsh 每次请求独立 messages；但路由型 provider 可能保留服务端状态 | **低/待确认**。写进风险清单 |
| L10 | 模型「先验知识」剧透 | **是** | 「毒湯」是知名谜题，其解答在公开语料中；模型可能已知 | **无法用机制消除**。C9a 必须声明此边界 |
| L11 | 角色把授权内秘密说给不该听的频道 | N/A | 角色只有自己的投影；不能主动广播 | 不影响「读」，但属协议编排问题 |
| L12 | OS 沙箱能兜底读隔离吗 | **否** | dsh sandbox 仅限写/执行，读 pass-through；Pi 无读沙箱 | C9b ≠ 读隔离 |

**判断**：
- 「只靠工具限制」**不能**保证。真正的最小充分条件 ≈ 「**注入面洁净 + 无 fs/bash + ephemeral 会话 + 完整 system prompt 替换**」
  四者同时成立；工具限制是其中之一。
- 即便四者成立，**L10（模型先验）无解**——机制只能保证「没喂给它的它看不到」，不能保证「它本来就不知道」。
  → C9a 的措辞应从「保证角色读不到未授权数据」收敛为「保证角色**未被注入**未授权数据」，
  并在文档中明确 L10 为已知边界。

---

## 4. Q3：宿主可移植性（Pi vs dsh）

### 4.1 能力映射

| 契约点 | Pi 原语（证据） | dsh 原语（证据） | 一致性 |
|---|---|---|---|
| 独立上下文 spawn | 子进程 `pi --mode json -p --no-session`（`pi --help`） | `spawn` provider，`inheritsParentContext=false`（`spawn-in-process/lib/index.js:30`） | ✅ 等价 |
| 工具门控 | `--tools` 替换式 allowlist（`cli.md:120`） | `ToolRestriction.allow`（`dsh-tools ...:475`） | ✅ 等价 |
| persona/system | `--system-prompt` / `--append-system-prompt` / agent md | `persona` 能力（`types.d.ts:185-191`） | ⚠️ 语义不同（前者整段替换，后者只 shadow deployment persona） |
| fresh/无状态 | `--no-session` | 子代理会话独立、可 ephemeral（`spawn`） | ✅ |
| per-role 模型 | `--model` | `agentOptions{provider,model,reasoningEffort,maxTokens}` | ✅（Pi 无 maxTokens 旗标 → 待确认） |
| 递归上限 | `--tools` 不含 subagent 扩展即可 | `maxDepth=0`（`dsh-tool-subagent README:63`） | ⚠️ Pi 靠「不给工具」，无显式深度概念 |
| 超时/中断 | 外层进程 kill（可自建） | `signal`/`abort`（subagent 契约） | ⚠️ Pi 需适配层自建 |
| 结构化输出 | 解析 `--mode json` 事件流 | `outputSchema` 能力 | ⚠️ Pi 需自解析 |
| OS 沙箱 | 仅 bash（第三方扩展，`examples/extensions/sandbox`） | `dsh-sandbox-local`（写/执行） | ⚠️ 读均不覆盖 |
| 事件/进度 | `pi.on(...)` / `--mode json` 事件 | 生命周期事件 + 结算通知 | ✅ 但形态不同，需抽象 |

### 4.2 分叉点（必须抽象）

1. **「干净子代理」的构造方式分叉**：
   - Pi = **进程边界**：每个隔离维度是一个 CLI 旗标，漏一个就漏。适配层必须集中构造 argv 并做单元断言。
   - dsh = **组合边界**：隔离维度是 composition 里挂了哪些插件。`toolFilter` 能挡工具，
     **挡不住 `agent-instructions`/`skill`/`web` 这类非工具贡献**；且「子代理加入父组合」意味着
     你无法只给子代理一套干净组合。→ dsh 侧干净角色应走**独立 role profile/out-of-process**，
     或全局关闭 `agent-instructions`（`maxBytes<=0`）并接受 master 也失去该注入。

2. **「persona」语义分叉**：Pi `--system-prompt` 是替换整段；dsh `persona` 只 shadow 部署 persona，
   父组合的其它提示段仍继承（`dsh-agent-presets`：子代理加入父组合）。→ 抽象层要区分
   `replace_system_prompt` 与 `append_persona` 两种语义，不能强行归一。

3. **失败/结算形态分叉**：Pi 是子进程退出码 + JSON 事件；dsh 是 `SubagentRun.result` +
   `stop reason` + `abort`。→ 契约需定义宿主无关的 `spawn result`。

### 4.3 宿主无法满足 / 需降级

| 需求 | Pi | dsh | 降级 |
|---|---|---|---|
| 读隔离的机制化保证 | 只能靠「不给 fs 工具」（无读沙箱） | 同左（fs-sandbox 读 pass-through） | 以「注入面洁净 + 无 fs」为降级基线；如需强保证，用容器/独立用户 |
| output token 上限 | `pi --help` 未见对应旗标 | `agentOptions.maxTokens` | Pi 待确认；缺则退化为不限制 + 靠 prompt 约束 |
| 项目级插件挂载 | 有 `.pi/extensions`（需 project trust） | 无项目级插件面；profile/`--patch`/preset root | dsh 适配层需用户级安装或 `--patch`，不能随冒险目录自带 |
| 非工具上下文贡献的按角色关闭 | 有 `--no-context-files` 等 | 无按子关闭（只有全局 composition） | dsh 需 role profile |

---

## 5. Q4：接缝选择——插件 vs 通用 CLI

**结论：插件应是「薄适配」，重活留在协议 CLI（D6）。**

- **应留在 CLI**（已有，正确）：投影/掩码 `context build`、`context compact`、随机 `dice`、
  判定 `check`、状态 `state`、git `step`、审计 `log`。它们是宿主无关、可确定性测试的安全关键路径。
- **应留在插件**（宿主特异）：spawn 子代理、按角色门控工具、注入投影、ephemeral 会话、
  模型路由、超时/中断、事件回流。这些无法用纯 CLI 表达。
- **反模式警告**：`spawn_role(..., context)` 让 master 读投影再转交，等于把投影内容搬进 master 上下文
  （膨胀 + 错角色风险）。应改为插件消费 `roles/<id>/context.jsonl`（由 CLI 产出），
  master 只传 `role_id` + `instruction` + 上下文**路径**。
- **边界判据**：插件**只调用协议 CLI 与其文档化产物**，不解析 `channels/`/`world/` 结构、不实现掩码逻辑。
  这样 D6「适配层不解读目录」成立。

---

## 6. Q5：可验证性

### 6.1 fake-agent 能证明什么（机械可断言）

1. **参数构造**：给定 `role_id/tools/route`，适配层生成的宿主 argv/配置**逐字段**正确
   （单测 `buildPiArgs` 类函数；dsh 检查 `ToolRestriction`/`agentOptions` 对象）。
2. **注入内容取自正确来源**：fake agent 记录收到的 prompt，断言 == `context build --role <id>` 的产物
   （且不含他人投影）。
3. **工具面**：fake agent 声明其可用工具集，断言 == allowlist，且不含 fs/bash/subagent。
4. **门控行为**：对 deny 列表中的工具名调用，fake 执行器返回拒绝。
5. **生命周期/顺序**：spawn → reply → 转录回写 → commit 的顺序与幂等。
6. **禁入内容（金丝雀）**：在未授权产物（他人 `roles/*/context.jsonl`、`world` 秘密、`log`、
   `AGENTS.md`）植入唯一 nonce，断言 nonce **不出现**在送入子代理的完整请求中。

### 6.2 fake-agent **不能**证明什么（关键）

1. **真实宿主是否真的没加载上下文文件。** fake 环绕过了宿主加载器。→ 必须加**对真实宿主二进制**的
   集成测试：植入 canary nonce 到 `AGENTS.md`/用户扩展/skills，真实 spawn 一个角色，
   用「捕获请求载荷」的方式（Pi：`--mode json` 事件 + 自定义记录扩展；dsh：session log / 请求钩子）
   断言 nonce 不出现。**这才是隔离的机械断言**。
2. **宿主升级后旗标语义不变。** 需 pin 版本 + 在 capability_report/自证里断言关键不变量。
3. **模型先验知识（L10）。** 无法机械断言。
4. **OS 层泄漏。** fake/进程内都无法证明；只有沙箱或独立用户能。
5. **非确定性与成本。** fake 不消耗真实 token。

### 6.3 隔离能否被机械断言？

**能，但不是用 fake-agent**。推荐三层：
- 单测：argv/配置构造（fast）。
- 金丝雀集成：真实宿主 + nonce + 请求捕获（slow，阶段门禁）。
- 自证：`capability_report` 返回隔离不变量，启动时对不变量做断言（fail-closed）。

---

## 7. Q6：过度设计 / 遗漏

### 7.1 可能多余

- **C10 audit（作为独立能力）**：协议 CLI 已审计每次调用；仅「宿主原生工具」需要补审。→ 合并。
- **C6 notify/stream**：MVP 非必需，保留为可选即可。
- **C8 capability_report**：保留，但价值主要在「自证隔离不变量」，而非罗列能力。

### 7.2 被忽略但必需

1. **C11 模型/凭据路由（每角色）**——KP 用强模型、NPC 用廉价模型是成本刚需；
   dsh 有 `agentOptions`，Pi 有 `--model`。凭据传递需明确（子进程继承 env；无 bash 则不易外泄）。
2. **C12 超时/中断/错误契约**——C1 无超时、无 abort、无失败语义；长团必须在角色卡死时可中断。
3. **C13 成本/token 上限**——无上限的长团会失控；dsh `maxTokens`，Pi 待确认。
4. **C14 递归深度上限**——角色**绝不能**再 spawn 子代理（否则隔离可被绕过/成本爆炸）。
   dsh `maxDepth=0`；Pi 靠不给 subagent 扩展 + deny 工具。
5. **C15 受限读取**——见 §0.3，`rules/` 必须可达。方案二选一：投影器纳入授权材料，或插件提供
   `role_read(path)` 且 path 受白名单（`rules/**`、`roles/<self>/**`、白名单 module 片段）。
6. **C16 角色↔频道绑定 + 转录回写**——`spawn_role` 应携带 `channel_id`；谁把 reply 写进
   `transcript.md`（master？插件？）必须定死，否则 transcript 不可复现、审计断链。
7. **C17 隔离自证 + 金丝雀测试**——见 §6.3。

### 7.3 与现有工具的缺口（证据）

- `check resolve` **不存在**（`systems/coc7e/tools/` 为空，`tools/` 无 `check.py`）→ C3 引用了未实现工具。
- `dice` **无 secret 模式**（`tools/dice.py` 无相关参数），与 `visibility.md` §3「秘密骰写入受限位置」不符。
- `context compact` 与 fresh+重建模型冲突（§0.4）。

---

## 8. Q7：风险清单

| 风险 | 说明 | 证据/推断 | 缓解 |
|---|---|---|---|
| 宿主升级破坏插件 | CLI 旗标/插件 API 变化 | Pi/dsh 均 rc/快速迭代（dsh `0.1.5-rc.2`） | pin 版本；capability_report 运行时自证；金丝雀测试进门禁 |
| 默认注入泄漏 | AGENTS.md/扩展/skills 自动注入 | 证据 L1/L2/L3 | 显式关闭 + 干净配置目录 + 金丝雀 |
| 模型不可用/限流 | 子代理 spawn 失败 | 推断 | C12 错误契约 + 重试/降级到内联 |
| 成本失控 | 每回合重建全量投影；无 token 上限 | `context build` 全量拼接（L121-128）+ C13 缺失 | 压缩策略修正 + per-role 模型 + token 上限 |
| 非确定性 | 同输入不同输出；难复现 | 协议已有 `seed` 工具 | 随机只经 `dice`；转录 + git 可回放 |
| 会话泄漏 | 持久会话残留 | L5 | `--no-session`；会话目录隔离/清理 |
| 并发 | 已缓，但迟早 | 多频道并发写 git/transcript | `step *` flock 已有；并发 spawn 需 C5 设计 |
| fail-open 掩码 | 缺 `visibility.json` 时全公开 | `_lib.py:355-361` | 改为 fail-closed |
| 压缩膨胀 | compact 被 build 重放 | `context.py:121-128` + `compact` 只截文件 | 改投影源（闭合频道归档）或让 build 消费 summary 替代旧频道 |
| 项目级插件不可随目录分发 | dsh 无项目插件面 | `dsh/README.md` §Profiles | 用户级安装 / `--patch`；文档明确 |

---

## 9. 建议的契约修订（v2 草案）

### 9.1 三层隔离模型

```
Layer A 注入面隔离 (context-surface)
  - 关闭 AGENTS.md/CLAUDE.md 自动加载
  - 关闭用户/项目 扩展、skills、prompt 模板、MCP
  - 使用干净的宿主配置目录（Pi: PI_CODING_AGENT_DIR=空；dsh: 独立 role composition/profile）
  - 整体替换 system prompt（不是 append）
Layer B 工具门控 (tool-gating)
  - 默认拒绝；allow = {dice, check[, role_read]}
  - 显式 deny: read/grep/find/ls/bash/edit/write/web/subagent/skill/todo/codemode
Layer C 会话/进程边界 (session)
  - ephemeral（Pi --no-session；dsh 无持久）
  - 每角色每回合 fresh（默认）；可选 continuable（默认关）
  - depth cap = 0（角色不得再 spawn）
  - timeout + abort
```

### 9.2 修订后的能力表

| # | 能力（建议名） | 契约 | 裁决 |
|---|---|---|---|
| C1 | `spawn_role({role_id, channel_id, instruction, context_path?, route?, max_output_tokens?, timeout?}) → {reply, stop_reason, usage?, error?}` | 全新上下文、fresh 会话 | 修订 |
| C2 | `tool_policy(allow[], deny[])` 默认拒绝 | 宿主强制 | 保留+强化 |
| C3 | `exec_tool(name, args)` 封闭集 `{dice, check}` | 无 shell | 修订 |
| C4 | `session_policy ∈ {fresh(default), continuable(opt)}` | fresh 必须 ephemeral | 保留+修订 |
| C6 | `notify(event)` 最小事件 | 可选 | 保留 |
| C8 | `capability_report() → {capabilities, isolation_invariants}` | 含自证 | 保留+扩展 |
| C9a | `context_isolation`：A+B+C 同时成立；声明 L10 边界 | 安全核心 | **修订（重写）** |
| C10 | 宿主原生工具调用审计（CLI 已审计，不重复） | 可选 | 修订/合并 |
| C11 | `model_route(role) → {provider, model, reasoning, max_tokens?}` | 必需（成本） | **新增** |
| C12 | `spawn` 超时/中断/错误语义 | 必需 | **新增** |
| C13 | per-role token/成本上限 | 必需 | **新增** |
| C14 | `max_depth = 0`（角色不得递归） | 必需 | **新增** |
| C15 | `role_read(path)` 白名单 or 投影纳入 `rules/` | 必需（流程要求） | **新增** |
| C16 | `spawn_role` 携带 `channel_id`，转录回写归属定死 | 必需 | **新增** |
| C17 | 隔离自证 + 泄漏金丝雀测试套件 | 验收 | **新增** |

### 9.3 安全断言（建议写入 AC）

- AC-S1：角色收到的完整请求中**不含** 他人 `roles/*/context.jsonl`、`world` 隐藏路径、`log/`、`AGENTS.md` 内容（金丝雀 nonce 断言）。
- AC-S2：角色可用工具集 == allowlist；对 deny 集调用被拒。
- AC-S3：角色进程/子代理不产生持久会话；无残留可被后续读取。
- AC-S4：`world/visibility.json` 缺失时**不得**退化为全公开（fail-closed）。
- AC-S5：角色无法触发 `context build` / `state` / `step` / 任意 shell。

---

## 10. 待确认（无法查证，不臆测）

1. Pi 是否有 **output token 上限**旗标（`pi --help` 未见）——若无需适配层自建或放弃该上限。
2. dsh 是否支持**按子代理**关闭 `agent-instructions`（本文只见全局 `maxBytes<=0`）——若必须全局，
   则 master 也会失去 AGENTS.md 注入，需要 role profile 隔离。
3. dsh 是否有**项目级插件/配置发现面**（本文只见 profile / `$DSH_HOME` / `--patch` / preset roots）。
4. 路由型 LLM provider 是否在服务端保留跨请求状态（L9）。
5. 真实端到端跑一次 Pi/dsh 子代理的注入行为（本文未实测，L1/L2/L4 为文档+代码证据，**非实测**）。

---

## 附：一句话给决策者

契约的**工程直觉是对的**（独立上下文 + 工具白名单 + 无状态），但**安全叙事夸大**了：
把它写成「工具限制就够」会给出**虚假的安全感**；真正决定成败的是「**别把不该给的东西注进去**」，
而这需要显式关闭宿主的一堆默认行为，并用金丝雀测试守住。其余缺口（模型路由、超时、成本、
递归上限、受限读取、转录归属）都是「不补就跑不完一场真团」的硬缺口。
