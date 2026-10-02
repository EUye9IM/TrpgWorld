#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""``context`` —— 角色可见上下文投影与压缩（安全关键路径）。

子命令：
* ``context build --role <id>``               生成 ``roles/<id>/context.jsonl``
* ``context compact --role <id> [--keep N]``  短期溢出 → ``roles/<id>/summary.md``

``build`` 只读取：

1. ``channels/*/meta.json`` 中 ``participants`` 含该 role（或哨兵 ``*``/``public``）的频道；
2. ``world/state.json`` 经 ``world/visibility.json`` mask 过滤后的可见部分；
3. 该角色自己的 ``roles/<id>/{persona,memory,summary}.md`` 与 ``sheet.*``。

它**不读** ``log/``、他人 ``roles/``、也不整体读取 ``channels/``；未参与频道的
transcript 不会进入投影。秘密隔离由本工具保证，而非角色自律。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import _lib

INPUTS = "build: --role <id>；compact: --role <id> [--keep N]"
OUTPUTS = "JSON: {role, channels, worldPaths, messages} / {before, after, summarized}"
SIDE_EFFECTS = "build 写 roles/<id>/context.jsonl；compact 写 summary.md 并截断 context.jsonl；均追加 log/events.jsonl"


def participants_include(participants, role: str) -> bool:
    if not isinstance(participants, (list, tuple)):
        return False
    return role in participants or _lib.PUBLIC in participants or "*" in participants


def load_channels(adventure: Path, role: str) -> list[dict]:
    """返回该角色参与、且按 id 排序的频道（含 transcript）。"""
    channels_dir = adventure / "channels"
    if not channels_dir.is_dir():
        return []
    included: list[dict] = []
    for meta_path in sorted(channels_dir.glob("*/meta.json")):
        try:
            meta = _lib.read_json(meta_path, {}) or {}
        except json.JSONDecodeError:
            continue
        participants = meta.get("participants", [])
        if not participants_include(participants, role):
            continue
        cid = meta_path.parent.name
        transcript_path = meta_path.parent / "transcript.md"
        transcript = transcript_path.read_text(encoding="utf-8") if transcript_path.exists() else ""
        included.append(
            {
                "id": cid,
                "purpose": meta.get("purpose", ""),
                "participants": participants,
                "status": meta.get("status", ""),
                "transcript": transcript,
            }
        )
    return included


def load_role_files(adventure: Path, role: str) -> dict[str, str]:
    role_dir = adventure / "roles" / role
    files: dict[str, str] = {}
    for name in ("persona.md", "memory.md", "summary.md"):
        path = role_dir / name
        if path.exists():
            files[name] = path.read_text(encoding="utf-8")
    for sheet in sorted(role_dir.glob("sheet.*")):
        if sheet.is_file():
            files[sheet.name] = sheet.read_text(encoding="utf-8")
    return files


def build_messages(adventure: Path, role: str) -> tuple[list[dict], list[dict], list[str]]:
    visibility = _lib.read_visibility(adventure)
    state = _lib.read_json(adventure / "world" / "state.json", {})
    projection, details = _lib.build_projection(state, visibility, role)
    visible_paths = [d["path"] for d in details if d["visible"]]

    channels = load_channels(adventure, role)
    role_files = load_role_files(adventure, role)

    messages: list[dict] = [
        {
            "role": "system",
            "source": "protocol",
            "content": (
                f"你是冒险中的角色 `{role}`。你只能基于本 context.jsonl 中的内容行动；"
                "执行确定性操作（骰子、状态、git）必须调用 tools/ 下的 CLI。"
            ),
        }
    ]
    for name in ("persona.md", "memory.md", "summary.md"):
        if name in role_files:
            messages.append(
                {"role": "system", "source": name, "content": role_files[name]}
            )
    for name in sorted(k for k in role_files if k.startswith("sheet.")):
        messages.append({"role": "system", "source": name, "content": role_files[name]})

    if projection:
        messages.append(
            {
                "role": "system",
                "source": "world",
                "content": "以下是按可见性 mask 过滤后的世界状态（world/state.json 的投影）：\n"
                + json.dumps(projection, ensure_ascii=False, indent=2),
            }
        )

    for channel in channels:
        header = f"[channel/{channel['id']}] purpose={channel['purpose']} status={channel['status']}"
        messages.append(
            {
                "role": "user",
                "source": f"channel/{channel['id']}",
                "purpose": channel["purpose"],
                "content": header + "\n\n" + channel["transcript"].strip(),
            }
        )
    return messages, channels, visible_paths


def cmd_build(args: argparse.Namespace) -> int:
    adventure = _lib.find_adventure(adventure=args.adventure)
    role = _lib.safe_id(args.role, kind="role id")
    messages, channels, visible_paths = build_messages(adventure, role)

    role_dir = adventure / "roles" / role
    role_dir.mkdir(parents=True, exist_ok=True)
    context_path = role_dir / "context.jsonl"
    with context_path.open("w", encoding="utf-8") as fh:
        for message in messages:
            fh.write(json.dumps(message, ensure_ascii=False) + "\n")

    output = {
        "ok": True,
        "command": "context build",
        "role": role,
        "channels": [c["id"] for c in channels],
        "worldPaths": visible_paths,
        "messages": len(messages),
        "contextFile": str(context_path.relative_to(adventure)),
        "adventure": str(adventure),
    }
    _lib.log_event(
        adventure,
        "context build",
        {"role": role},
        {"channels": output["channels"], "messages": len(messages)},
        side_effects=["roles/%s/context.jsonl" % role, "log/events.jsonl"],
    )
    _lib.emit(output)
    return 0


def summarize(messages: list[dict]) -> str:
    """确定性占位摘要：逐条拼接 source 与内容首段。"""
    lines = []
    for message in messages:
        source = message.get("source", message.get("role", "?"))
        content = " ".join(str(message.get("content", "")).split())
        if len(content) > 200:
            content = content[:200] + "…"
        lines.append(f"- [{source}] {content}")
    return "\n".join(lines)


def cmd_compact(args: argparse.Namespace) -> int:
    adventure = _lib.find_adventure(adventure=args.adventure)
    role = _lib.safe_id(args.role, kind="role id")
    keep = args.keep
    if keep < 0:
        raise _lib.UsageError("--keep must be >= 0")

    context_path = adventure / "roles" / role / "context.jsonl"
    if not context_path.exists():
        raise _lib.AdventureError(
            f"no context to compact: {context_path} (run `context build --role {role}` first)"
        )
    messages = [
        json.loads(line)
        for line in context_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    before = len(messages)
    if before <= keep:
        output = {
            "ok": True,
            "command": "context compact",
            "role": role,
            "before": before,
            "after": before,
            "summarized": 0,
            "contextFile": str(context_path.relative_to(adventure)),
            "adventure": str(adventure),
        }
        _lib.log_event(adventure, "context compact", {"role": role, "keep": keep}, output, [])
        _lib.emit(output)
        return 0

    dropped = messages[: before - keep]
    tail = messages[before - keep :]
    summary_file = adventure / "roles" / role / "summary.md"
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    block = (
        f"\n## 压缩记录 {_lib.iso_now()}\n\n"
        "> 由 `context compact` 生成的确定性占位摘要；LLM 精炼由 master 在 play-time 完成。\n\n"
        + summarize(dropped)
        + "\n"
    )
    with summary_file.open("a", encoding="utf-8") as fh:
        fh.write(block)

    with context_path.open("w", encoding="utf-8") as fh:
        for message in tail:
            fh.write(json.dumps(message, ensure_ascii=False) + "\n")

    output = {
        "ok": True,
        "command": "context compact",
        "role": role,
        "before": before,
        "after": len(tail),
        "summarized": len(dropped),
        "summaryFile": str(summary_file.relative_to(adventure)),
        "contextFile": str(context_path.relative_to(adventure)),
        "adventure": str(adventure),
    }
    _lib.log_event(
        adventure,
        "context compact",
        {"role": role, "keep": keep},
        {"before": before, "after": len(tail), "summarized": len(dropped)},
        side_effects=["roles/%s/summary.md" % role, "roles/%s/context.jsonl" % role, "log/events.jsonl"],
    )
    _lib.emit(output)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="context",
        description=(
            "角色上下文投影（安全关键）。build 只把该角色参与的频道 + mask 过滤后的世界状态\n"
            "+ 自身记忆投影进 roles/<id>/context.jsonl；compact 把短期溢出压进 summary.md。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_lib.help_epilog(
            inputs=INPUTS,
            outputs=OUTPUTS,
            side_effects=SIDE_EFFECTS,
            exit_codes="0 成功；1 业务失败；2 用法错误",
        ),
    )
    parser.add_argument("--version", action="version", version=f"context {_lib.VERSION}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    build = sub.add_parser(
        "build",
        help="投影角色可见上下文",
        description="生成 roles/<id>/context.jsonl；按 channel participants 与 world mask 双重过滤。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_lib.help_epilog(
            inputs=INPUTS,
            outputs=OUTPUTS,
            side_effects=SIDE_EFFECTS,
            exit_codes="0 成功；1 业务失败；2 用法错误",
        ),
    )
    build.add_argument("--role", required=True, help="角色 id，如 kp、pl1")
    build.add_argument("--adventure", default=None, help="冒险目录；缺省向上找 AGENTS.md")

    compact = sub.add_parser(
        "compact",
        help="压缩短期上下文到 summary.md",
        description="把 context.jsonl 超出最近 --keep 条的部分摘要进 summary.md 并截断 context.jsonl。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_lib.help_epilog(
            inputs=INPUTS,
            outputs=OUTPUTS,
            side_effects=SIDE_EFFECTS,
            exit_codes="0 成功；1 业务失败；2 用法错误",
        ),
    )
    compact.add_argument("--role", required=True, help="角色 id")
    compact.add_argument("--keep", type=int, default=20, help="保留最近 N 条（默认 20）")
    compact.add_argument("--adventure", default=None, help="冒险目录；缺省向上找 AGENTS.md")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help(sys.stderr)
        return 2
    try:
        return {"build": cmd_build, "compact": cmd_compact}[args.command](args)
    except _lib.UsageError as exc:
        _lib.emit_error(str(exc), code="usage")
        return 2
    except (_lib.AdventureError, json.JSONDecodeError, OSError) as exc:
        _lib.emit_error(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
