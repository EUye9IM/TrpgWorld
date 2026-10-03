#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""``scaffold`` —— 冒险目录脚手架（build-time）。

子命令：
* ``scaffold new --module <path> --out <dir> [--name <slug>] [--system <name>]``

流程：复制 ``templates/adventure/`` 骨架 → 复制框架 ``tools/`` → 解析模组 markdown
→ 写 ``module/{overview.md,scenes/,clues.md,npcs/,hooks.md}`` →（可选）带入
``systems/<name>/`` 的 ``flow/``、``rules/``、``tools/*`` → 渲染 ``AGENTS.md``
→ ``git init`` 并首次提交 + 打 ``compile/<slug>`` tag。

解析保持**通用**（基于 markdown 结构）；CoC 特有语义由 ``--system`` 带入的
``flow/`` 与 ``rules/`` 提供。
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

import _lib
import step

INPUTS = "--module <path> --out <dir> [--name <slug>] [--template <dir>] [--system <name>] [--systems-dir <dir>] [--force] [--no-git]"
OUTPUTS = "JSON: {out, slug, module, system, scenes, npcs, clues, commit, tag}"
SIDE_EFFECTS = "创建 --out 目录、复制模板与工具、写 module/*、带入 system 的 flow/rules/tools、git init + 首次提交 + tag（--no-git 时跳过）、追加 out/log/events.jsonl"

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = FRAMEWORK_ROOT / "templates" / "adventure"
DEFAULT_SYSTEMS_DIR = FRAMEWORK_ROOT / "systems"

#: 随冒险目录内嵌的运行时工具（scaffold 是 build-time 框架工具，不内嵌）。
EMBEDDED_TOOLS = ("_lib.py", "dice.py", "state.py", "context.py", "step.py")

OVERVIEW_KW = ("摘要", "大綱", "大纲", "序論", "序论", "序章", "前言", "導言", "导言", "背景", "簡介", "简介", "引子", "概述")
ENDING_KW = ("結局", "结局", "後日談", "后日谈", "附錄", "附录")
NPC_KW = ("npc", "人物", "角色介紹", "角色介绍", "登場人物", "登场人物")
HOOK_KW = ("計時", "计时", "倒计时", "倒數", "時間限制", "时间限制", "特殊規則", "特殊规则", "鉤子", "钩子")
SCENE_KW = ("场景", "場景", "房間", "房间", "scene", "room", "探索", "調查", "调查", "地點", "地点", "區域", "区域")
CLUE_KW = ("线索", "線索", "判定", "檢定", "检定", "發現", "发现", "情報", "情报")
TIMER_KW = ("一小時", "一小时", "倒计时", "倒數", "計時", "计时", "時間限制", "时间限制")

STATBLOCK_RE = re.compile(r"\|\s*STR\s*\|")


# ---------------------------------------------------------------------------
# Markdown 树
# ---------------------------------------------------------------------------

@dataclass
class Node:
    level: int
    heading: str
    body: list[str] = field(default_factory=list)
    children: list["Node"] = field(default_factory=list)


def parse_markdown(text: str) -> Node:
    root = Node(0, "")
    stack: list[Node] = [root]
    for line in text.split("\n"):
        match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if match:
            node = Node(len(match.group(1)), match.group(2).strip())
            while stack and stack[-1].level >= node.level:
                stack.pop()
            stack[-1].children.append(node)
            stack.append(node)
        else:
            stack[-1].body.append(line)
    return root


def render_node(node: Node) -> str:
    parts: list[str] = []
    if node.level > 0:
        parts.append("#" * node.level + " " + node.heading)
    body = "\n".join(node.body).strip()
    if body:
        parts.append(body)
    for child in node.children:
        parts.append(render_node(child))
    return "\n\n".join(p for p in parts if p)


def walk(node: Node):
    yield node
    for child in node.children:
        yield from walk(child)


def classify_section(heading: str) -> str:
    h = heading.lower()
    if any(k in h for k in OVERVIEW_KW):
        return "overview"
    if any(k in h for k in NPC_KW):
        return "npc"
    if any(k in h for k in ENDING_KW):
        return "overview"
    if any(k in h for k in HOOK_KW):
        return "hooks"
    if any(k in h for k in SCENE_KW):
        return "scene"
    if re.match(r"^\s*\d", heading):
        return "scene"
    return "scene"


# ---------------------------------------------------------------------------
# 模组解析
# ---------------------------------------------------------------------------

def analyze_module(text: str, fallback_title: str) -> dict:
    root = parse_markdown(text)
    level1 = [c for c in root.children if c.level == 1]
    if level1:
        title = level1[0].heading or fallback_title
        sections: list[Node] = []
        for node in level1:
            sections.extend(node.children)
    else:
        title = fallback_title
        sections = root.children

    overview: list[Node] = []
    hooks: list[Node] = []
    scenes: list[Node] = []
    npcs: list[Node] = []
    npc_headings: set[str] = set()

    def add_npc(node: Node) -> None:
        if node.heading and node.heading not in npc_headings:
            npc_headings.add(node.heading)
            npcs.append(node)

    for section in sections:
        kind = classify_section(section.heading)
        if kind == "overview":
            overview.append(section)
        elif kind == "hooks":
            hooks.append(section)
        elif kind == "npc":
            kids = [c for c in section.children if c.level >= 3]
            if kids:
                for kid in kids:
                    add_npc(kid)
            else:
                add_npc(section)
        else:
            scenes.append(section)

    # 全局 NPC 扫描：仅看子节点自身的正文（标题含 npc 或正文本体含属性表），
    # 不把包含 NPC 子节的场景容器误判为 NPC。
    section_ids = {id(s) for s in sections}
    for node in walk(root):
        if node.level < 2 or not node.heading or id(node) in section_ids:
            continue
        own_text = "\n".join(node.body)
        if "npc" in node.heading.lower() or STATBLOCK_RE.search(own_text):
            add_npc(node)

    # 无 level-2 场景时，退而用 level-3 作为场景
    if not scenes:
        scenes = [c for c in walk(root) if c.level == 3 and c.heading]

    # 线索抽取
    clues: dict[str, list[str]] = {}
    for section in scenes:
        for line in render_node(section).split("\n"):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if any(k in stripped for k in CLUE_KW):
                clues.setdefault(section.heading, [])
                if stripped not in clues[section.heading]:
                    clues[section.heading].append(stripped)

    # 计时/时间限制行
    timer_lines: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped and any(k in stripped for k in TIMER_KW):
            if stripped not in timer_lines:
                timer_lines.append(stripped[:300])

    return {
        "title": title,
        "overview": overview,
        "hooks": hooks,
        "scenes": scenes,
        "npcs": npcs,
        "clues": clues,
        "timer_lines": timer_lines,
        "raw": text,
    }


def render_overview(analysis: dict) -> str:
    parts = [f"# {analysis['title']}"]
    for section in analysis["overview"]:
        parts.append(render_node(section))
    if len(parts) == 1:
        excerpt = "\n".join(analysis["raw"].split("\n")[:40]).strip()
        parts.append("## 原始开头（未识别到摘要/大纲小节）\n\n" + excerpt)
    return "\n\n".join(parts) + "\n"


def render_clues(analysis: dict) -> str:
    parts = [
        "# 线索",
        "> 由 `scaffold` 从模组自动抽取，需 master/KP 复核整理；原始措辞保留。",
    ]
    if not analysis["clues"]:
        parts.append("_未自动识别到线索行。请回看 `module/scenes/` 并手工补充。_")
    else:
        for heading, lines in analysis["clues"].items():
            parts.append(f"## {heading}\n\n" + "\n".join(lines))
    return "\n\n".join(parts) + "\n"


def render_hooks(analysis: dict) -> str:
    parts = [
        "# Hooks",
        "> 本模组对 `flow/` 阶段的覆盖与特殊规则。I2 为骨架，语义增强留待规则系统。",
    ]
    if analysis["timer_lines"]:
        parts.append(
            "## 检测到的计时/时间限制\n\n"
            + "\n".join(f"- {line}" for line in analysis["timer_lines"])
        )
    for section in analysis["hooks"]:
        parts.append(render_node(section))
    if len(parts) == 2 and not analysis["hooks"]:
        parts.append("_未自动识别到钩子；如有特殊规则请在此补充。_")
    return "\n\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# 模板复制与渲染
# ---------------------------------------------------------------------------

def copy_template(template_dir: Path, out: Path) -> list[str]:
    written: list[str] = []
    for src in sorted(template_dir.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(template_dir)
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        written.append(str(rel))
    return written


def copy_tools(framework_tools: Path, out: Path) -> list[str]:
    written: list[str] = []
    out_tools = out / "tools"
    out_tools.mkdir(parents=True, exist_ok=True)
    # 清掉可能随模板带入的 build-time 工具，保证内嵌工具集只含运行时工具。
    (out_tools / "scaffold.py").unlink(missing_ok=True)
    for name in EMBEDDED_TOOLS:
        src = framework_tools / name
        if not src.is_file():
            continue
        shutil.copy2(src, out_tools / name)
        written.append(f"tools/{name}")
    return written


def replace_tree(src: Path, dst: Path) -> list[str]:
    """用 ``src`` 目录内容整体替换 ``dst``（先清空 dst），返回相对路径清单。"""
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for item in sorted(src.rglob("*")):
        if not item.is_file():
            continue
        rel = item.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        written.append(str(rel))
    return written


def copy_system(system_dir: Path, out: Path) -> dict:
    """把规则系统 ``systems/<name>/`` 的 flow/rules/tools 带入冒险目录。

    * ``flow/``  → 冒险 ``flow/``（整体替换模板占位）。
    * ``rules/`` → 冒险 ``rules/``（整体替换模板占位）。
    * ``tools/*`` → 冒险 ``tools/``（逐字节复制，不删除内嵌运行时工具）。
    """
    written: dict[str, list[str]] = {"flow": [], "rules": [], "tools": []}
    flow_src = system_dir / "flow"
    if flow_src.is_dir():
        written["flow"] = replace_tree(flow_src, out / "flow")
    rules_src = system_dir / "rules"
    if rules_src.is_dir():
        written["rules"] = replace_tree(rules_src, out / "rules")
    tools_src = system_dir / "tools"
    if tools_src.is_dir():
        out_tools = out / "tools"
        out_tools.mkdir(parents=True, exist_ok=True)
        for src in sorted(tools_src.iterdir()):
            if not src.is_file():
                continue
            shutil.copy2(src, out_tools / src.name)
            written["tools"].append(f"tools/{src.name}")
    return written


def system_note(system: str | None) -> str:
    """渲染 ``AGENTS.md`` 中的规则系统说明行。"""
    if system:
        return f"`{system}`（`flow/` 与 `rules/` 来自 `systems/{system}/`）"
    return "未指定（`flow/` 与 `rules/` 为模板占位）"


def render_agents(
    template_text: str,
    analysis: dict,
    *,
    slug: str,
    source: str,
    system: str | None = None,
) -> str:
    scenes = analysis["scenes"]
    npcs = analysis["npcs"]
    scene_list = "\n".join(
        f"  - `{_scene_filename(i, s.heading)}` — {s.heading}" for i, s in enumerate(scenes)
    ) or "  - _未识别到场景，见 `module/overview.md`_"
    npc_list = "\n".join(f"  - `{_npc_filename(i, n.heading)}` — {n.heading}" for i, n in enumerate(npcs)) or "  - _未识别到 NPC_"
    clue_count = sum(len(v) for v in analysis["clues"].values())
    replacements = {
        "{{MODULE_NAME}}": analysis["title"],
        "{{MODULE_SLUG}}": slug,
        "{{MODULE_SOURCE}}": source,
        "{{CREATED_AT}}": _lib.iso_now(),
        "{{SCENE_LIST}}": scene_list,
        "{{NPC_LIST}}": npc_list,
        "{{CLUE_COUNT}}": str(clue_count),
        "{{SYSTEM_NOTE}}": system_note(system),
    }
    text = template_text
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text


def _scene_filename(index: int, heading: str) -> str:
    return f"{index + 1:03d}-{_lib.slugify(heading, fallback=f'scene-{index + 1}')}.md"


def _npc_filename(index: int, heading: str) -> str:
    return f"{_lib.slugify(heading, fallback=f'npc-{index + 1}')}.md"


def write_module(out: Path, analysis: dict, *, slug: str, source: str) -> dict:
    module_dir = out / "module"
    scenes_dir = module_dir / "scenes"
    npcs_dir = module_dir / "npcs"
    scenes_dir.mkdir(parents=True, exist_ok=True)
    npcs_dir.mkdir(parents=True, exist_ok=True)

    (module_dir / "overview.md").write_text(render_overview(analysis), encoding="utf-8")
    (module_dir / "clues.md").write_text(render_clues(analysis), encoding="utf-8")
    (module_dir / "hooks.md").write_text(render_hooks(analysis), encoding="utf-8")

    scene_files: list[str] = []
    for i, scene in enumerate(analysis["scenes"]):
        name = _scene_filename(i, scene.heading)
        (scenes_dir / name).write_text(render_node(scene) + "\n", encoding="utf-8")
        scene_files.append(name)

    npc_files: list[str] = []
    for i, npc in enumerate(analysis["npcs"]):
        name = _npc_filename(i, npc.heading)
        (npcs_dir / name).write_text(render_node(npc) + "\n", encoding="utf-8")
        npc_files.append(name)

    return {"scenes": scene_files, "npcs": npc_files}


def create_baseline_channel(out: Path, analysis: dict) -> None:
    channel_dir = out / "channels" / "baseline"
    channel_dir.mkdir(parents=True, exist_ok=True)
    _lib.write_json(
        channel_dir / "meta.json",
        {
            "purpose": "全员公共基线频道：发布各场景应公开的 outcome",
            "participants": ["*"],
            "termination": "整个冒险结束时",
            "status": "open",
        },
    )
    (channel_dir / "transcript.md").write_text(
        f"# 公共基线频道 — {analysis['title']}\n\n"
        "> 本频道为全员可见的叠加层；场景频道结束后由 master 把应公开的 outcome 发布到这里。\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# 命令
# ---------------------------------------------------------------------------

def cmd_new(args: argparse.Namespace) -> int:
    module_path = Path(args.module).expanduser().resolve()
    if not module_path.is_file():
        raise _lib.AdventureError(f"module file does not exist: {module_path}")

    template_dir = Path(args.template).expanduser().resolve() if args.template else DEFAULT_TEMPLATE
    if not (template_dir / "AGENTS.md").is_file():
        raise _lib.AdventureError(f"template not found: {template_dir} (expected AGENTS.md)")

    out = Path(args.out).expanduser().resolve()
    if out.exists() and any(out.iterdir()) and not args.force:
        raise _lib.AdventureError(f"output directory is not empty: {out} (use --force to overwrite)")
    out.mkdir(parents=True, exist_ok=True)

    framework_tools = FRAMEWORK_ROOT / "tools"
    if not framework_tools.is_dir():
        raise _lib.AdventureError(f"framework tools not found: {framework_tools}")

    slug = _lib.slugify(args.name or module_path.stem, fallback="adventure")
    source = str(module_path)

    # 规则系统（可选）
    system: str | None = args.system or None
    systems_dir = (
        Path(args.systems_dir).expanduser().resolve() if args.systems_dir else DEFAULT_SYSTEMS_DIR
    )
    system_dir: Path | None = None
    if system:
        system_dir = systems_dir / system
        if not system_dir.is_dir():
            raise _lib.AdventureError(
                f"system not found: {system_dir} (expected a directory under {systems_dir})"
            )

    copy_template(template_dir, out)
    tools_written = copy_tools(framework_tools, out)
    system_written = copy_system(system_dir, out) if system_dir else {"flow": [], "rules": [], "tools": []}
    tools_written.extend(system_written["tools"])

    analysis = analyze_module(module_path.read_text(encoding="utf-8"), fallback_title=module_path.stem)
    module_files = write_module(out, analysis, slug=slug, source=source)

    template_text = (template_dir / "AGENTS.md").read_text(encoding="utf-8")
    agents_text = render_agents(template_text, analysis, slug=slug, source=source, system=system)
    (out / "AGENTS.md").write_text(agents_text, encoding="utf-8")

    create_baseline_channel(out, analysis)

    result: dict = {
        "ok": True,
        "command": "scaffold new",
        "out": str(out),
        "slug": slug,
        "system": system,
    }

    if args.no_git:
        # 用于把示例目录直接提交进框架仓库（避免嵌套 .git 成为 submodule/被忽略）。
        result.update({"commit": None, "tag": None, "git": "skipped (--no-git)"})
        side_effects = ["create adventure directory", "log/events.jsonl"]
    else:
        # git init，然后经 step.do_commit 串行首次提交（契约：git add/commit/tag 只走 step）
        init = _lib.git_init(out)
        if init.returncode != 0:
            raise _lib.AdventureError(f"git init failed: {(init.stderr or init.stdout).strip()}")
        commit_result = step.do_commit(
            out,
            f"chore(compile): scaffold {slug} from {module_path.name}",
            tag=f"compile/{slug}",
            force_tag=True,
        )
        result.update({"commit": commit_result.get("commit"), "tag": commit_result.get("tag")})
        side_effects = ["create adventure directory", "git init", "git commit", "git tag", "log/events.jsonl"]

    _lib.log_event(
        out,
        "scaffold new",
        {"module": source, "out": str(out), "name": args.name, "system": system},
        {
            "slug": slug,
            "system": system,
            "scenes": len(module_files["scenes"]),
            "npcs": len(module_files["npcs"]),
            "clues": sum(len(v) for v in analysis["clues"].values()),
            "commit": result.get("commit"),
            "tag": result.get("tag"),
        },
        side_effects=side_effects,
    )

    result.update(
        {
            "title": analysis["title"],
            "module": source,
            "template": str(template_dir),
            "system": system,
            "systemDir": str(system_dir) if system_dir else None,
            "systemFiles": system_written if system_dir else None,
            "scenes": module_files["scenes"],
            "npcs": module_files["npcs"],
            "clues": sum(len(v) for v in analysis["clues"].values()),
            "tools": tools_written,
            "agentsFile": str(out / "AGENTS.md"),
        }
    )
    _lib.emit(result)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scaffold",
        description=(
            "由 templates/adventure/ 生成冒险目录骨架，解析原始模组 markdown，\n"
            "渲染自描述 AGENTS.md，并 git init + 首次提交。仅 build-time 使用。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_lib.help_epilog(
            inputs=INPUTS,
            outputs=OUTPUTS,
            side_effects=SIDE_EFFECTS,
            exit_codes="0 成功；1 业务失败；2 用法错误",
        ),
    )
    parser.add_argument("--version", action="version", version=f"scaffold {_lib.VERSION}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    new = sub.add_parser(
        "new",
        help="从模组编译一个新的冒险目录",
        description="复制模板 + 工具 → 解析模组 → 写 module/* →（可选）带入 system 的 flow/rules/tools → 渲染 AGENTS.md → git init + 首次提交。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_lib.help_epilog(
            inputs=INPUTS,
            outputs=OUTPUTS,
            side_effects=SIDE_EFFECTS,
            exit_codes="0 成功；1 业务失败；2 用法错误",
        ),
    )
    new.add_argument("--module", required=True, help="原始模组 markdown 路径")
    new.add_argument("--out", required=True, help="输出冒险目录")
    new.add_argument("--name", default=None, help="slug（缺省用模组文件名）")
    new.add_argument("--template", default=None, help="模板目录（缺省为框架 templates/adventure）")
    new.add_argument("--system", default=None, help="规则系统名（如 coc7e）；带入其 flow/、rules/、tools/*")
    new.add_argument("--systems-dir", default=None, help="规则系统根目录（缺省为框架 systems/）")
    new.add_argument("--force", action="store_true", help="输出目录非空时仍写入")
    new.add_argument("--no-git", action="store_true", help="跳过 git init 与首次提交（用于把示例目录提交进框架仓库）")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help(sys.stderr)
        return 2
    try:
        return {"new": cmd_new}[args.command](args)
    except _lib.UsageError as exc:
        _lib.emit_error(str(exc), code="usage")
        return 2
    except (_lib.AdventureError, OSError, shutil.Error) as exc:
        _lib.emit_error(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
