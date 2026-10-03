#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""``state`` —— World State（世界真相）读写与可见性 mask 审计。

子命令：
* ``state get <key>``              读取 ``world/state.json`` 的某个路径
* ``state set <key> <value>``      写入（value 先按 JSON 解析，失败则作字符串）
* ``state mask --role <id>``       按 ``world/visibility.json`` 打印可见/隐藏路径

世界状态只经本工具修改。**角色不得直接调用 state get**，只能读 ``context build``
产出的投影；本工具面向 master / 系统工具。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import _lib

INPUTS = "get: key；set: key + value；mask: --role <id>"
OUTPUTS = "JSON: {ok, key/value} / {ok, role, visible, hidden, details}"
SIDE_EFFECTS = "set 写 world/state.json；每次调用追加 log/events.jsonl"


def state_path(adventure: Path) -> Path:
    return adventure / "world" / "state.json"


def load_state(adventure: Path) -> dict:
    data = _lib.read_json(state_path(adventure), {})
    if not isinstance(data, dict):
        raise _lib.AdventureError("world/state.json must contain a JSON object")
    return data


def resolve_path(obj, key: str):
    """按 ``/a/b`` 或 ``a.b`` 路径读取；不存在返回 ``(False, None)``。"""
    segs = [s for s in str(key).replace(".", "/").split("/") if s != ""]
    cur = obj
    for seg in segs:
        if isinstance(cur, dict) and seg in cur:
            cur = cur[seg]
        elif isinstance(cur, list) and seg.isdigit() and int(seg) < len(cur):
            cur = cur[int(seg)]
        else:
            return False, None
    return True, cur


def parse_value(raw: str):
    """优先按 JSON 解析，失败则原样作为字符串。"""
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="state",
        description=(
            "读写 World State（world/state.json）并审计可见性 mask。\n"
            "state set 覆盖指定路径；state mask 按 world/visibility.json 列出 role 的可见/隐藏路径。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_lib.help_epilog(
            inputs=INPUTS,
            outputs=OUTPUTS,
            side_effects=SIDE_EFFECTS,
            exit_codes="0 成功；1 业务失败；2 用法错误",
        ),
    )
    parser.add_argument("--version", action="version", version=f"state {_lib.VERSION}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    get = sub.add_parser(
        "get",
        help="读取一个状态路径",
        description="读取 world/state.json 中指定路径的值（缺失时 found=false，退出码仍为 0）。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_lib.help_epilog(
            inputs=INPUTS,
            outputs=OUTPUTS,
            side_effects=SIDE_EFFECTS,
            exit_codes="0 成功；1 业务失败；2 用法错误",
        ),
    )
    get.add_argument("key", help="JSON 路径，如 timer.remaining_minutes 或 /secrets/x")
    get.add_argument("--adventure", default=None, help="冒险目录；缺省向上找 AGENTS.md")

    setp = sub.add_parser(
        "set",
        help="写入一个状态路径",
        description="把 value 写入指定路径。value 先尝试 JSON 解析，否则作为字符串。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_lib.help_epilog(
            inputs=INPUTS,
            outputs=OUTPUTS,
            side_effects=SIDE_EFFECTS,
            exit_codes="0 成功；1 业务失败；2 用法错误",
        ),
    )
    setp.add_argument("key", help="JSON 路径")
    setp.add_argument("value", help="新值（自动 JSON 解析，失败则为字符串）")
    setp.add_argument("--adventure", default=None, help="冒险目录；缺省向上找 AGENTS.md")

    mask = sub.add_parser(
        "mask",
        help="审计某角色对 world/state.json 的可见性",
        description="按 world/visibility.json 的规则，列出该 role 可见与隐藏的叶子路径。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_lib.help_epilog(
            inputs=INPUTS,
            outputs=OUTPUTS,
            side_effects=SIDE_EFFECTS,
            exit_codes="0 成功；1 业务失败；2 用法错误",
        ),
    )
    mask.add_argument("--role", required=True, help="角色 id，如 kp、pl1")
    mask.add_argument("--adventure", default=None, help="冒险目录；缺省向上找 AGENTS.md")

    return parser


def cmd_get(args: argparse.Namespace) -> int:
    adventure = _lib.find_adventure(adventure=args.adventure)
    state = load_state(adventure)
    found, value = resolve_path(state, args.key)
    output = {
        "ok": True,
        "command": "state get",
        "key": args.key,
        "found": found,
        "value": value,
        "adventure": str(adventure),
    }
    _lib.log_event(
        adventure, "state get", {"key": args.key}, {"found": found}, side_effects=["log/events.jsonl"]
    )
    _lib.emit(output)
    return 0


def cmd_set(args: argparse.Namespace) -> int:
    adventure = _lib.find_adventure(adventure=args.adventure)
    state = load_state(adventure)
    value = parse_value(args.value)
    _lib.set_path(state, args.key.replace(".", "/"), value)
    path = _lib.write_json(state_path(adventure), state)
    output = {
        "ok": True,
        "command": "state set",
        "key": args.key,
        "value": value,
        "stateFile": str(path.relative_to(adventure)),
        "adventure": str(adventure),
    }
    _lib.log_event(
        adventure,
        "state set",
        {"key": args.key, "value": value},
        {"stateFile": output["stateFile"]},
        side_effects=["world/state.json", "log/events.jsonl"],
    )
    _lib.emit(output)
    return 0


def cmd_mask(args: argparse.Namespace) -> int:
    adventure = _lib.find_adventure(adventure=args.adventure)
    role = _lib.safe_id(args.role, kind="role id")
    state = load_state(adventure)
    visibility = _lib.read_visibility(adventure)
    _, details = _lib.build_projection(state, visibility, role)
    visible = [d["path"] for d in details if d["visible"]]
    hidden = [d["path"] for d in details if not d["visible"]]
    output = {
        "ok": True,
        "command": "state mask",
        "role": role,
        "default": visibility.get("default"),
        "rules": visibility.get("rules", []),
        "visible": visible,
        "hidden": hidden,
        "details": details,
        "adventure": str(adventure),
    }
    _lib.log_event(
        adventure,
        "state mask",
        {"role": role},
        {"visible": len(visible), "hidden": len(hidden)},
        side_effects=["log/events.jsonl"],
    )
    _lib.emit(output)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help(sys.stderr)
        return 2
    try:
        return {"get": cmd_get, "set": cmd_set, "mask": cmd_mask}[args.command](args)
    except _lib.UsageError as exc:
        _lib.emit_error(str(exc), code="usage")
        return 2
    except (_lib.AdventureError, json.JSONDecodeError) as exc:
        _lib.emit_error(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
