#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""``dice`` —— 带种子的确定性随机源。

子命令：
* ``dice roll --expr <NdM[±mod]> [--seed <int>] [--count N]``

同 ``seed`` + 同 ``expr`` 必定得到相同结果；agent 不得自造随机数，随机源只经此工具。
"""

from __future__ import annotations

import argparse
import random
import re
import secrets
import sys

import _lib

DICE_RE = re.compile(r"^\s*(?:(\d+)\s*)?d\s*(\d+)\s*([+-]\s*\d+)?\s*$", re.IGNORECASE)

INPUTS = "骰式 NdM±mod（如 1d100、2d6+3）、可选 --seed、可选 --count"
OUTPUTS = "JSON: {expr, seed, count, results:[{rolls,total,modifier}], totals, total}"
SIDE_EFFECTS = "追加 <adventure>/log/events.jsonl；不修改 world/"


def parse_expr(expr: str) -> tuple[int, int, int]:
    """解析 ``NdM±mod``；返回 ``(n, m, modifier)``。``dM`` 视为 ``1dM``。"""
    match = DICE_RE.match(expr)
    if not match:
        raise _lib.UsageError(f"invalid dice expression: {expr!r} (expected NdM, e.g. 1d100 or 2d6+3)")
    n = int(match.group(1)) if match.group(1) else 1
    m = int(match.group(2))
    modifier = int(match.group(3).replace(" ", "")) if match.group(3) else 0
    if n < 1:
        raise _lib.UsageError("number of dice must be >= 1")
    if m < 2:
        raise _lib.UsageError("die faces must be >= 2")
    return n, m, modifier


def roll_once(rng: random.Random, n: int, m: int, modifier: int) -> dict:
    rolls = [rng.randint(1, m) for _ in range(n)]
    return {"rolls": rolls, "modifier": modifier, "total": sum(rolls) + modifier}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dice",
        description=(
            "带种子的确定性随机源。工具输出即真相：任何叙事不得覆盖本工具的点数。\n"
            "同 seed + 同 expr 多次运行结果完全一致。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_lib.help_epilog(
            inputs=INPUTS,
            outputs=OUTPUTS,
            side_effects=SIDE_EFFECTS,
            exit_codes="0 成功；1 业务失败；2 用法错误",
        ),
    )
    parser.add_argument("--version", action="version", version=f"dice {_lib.VERSION}")

    sub = parser.add_subparsers(dest="command", metavar="<command>")

    roll = sub.add_parser(
        "roll",
        help="掷骰并输出可复现结果",
        description="掷 ``NdM±mod``；可用 --seed 固定随机源以复现。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_lib.help_epilog(
            inputs=INPUTS,
            outputs=OUTPUTS,
            side_effects=SIDE_EFFECTS,
            exit_codes="0 成功；1 业务失败；2 用法错误",
        ),
    )
    roll.add_argument("--expr", "-e", required=True, help="骰式，如 1d100 或 2d6+3")
    roll.add_argument("--seed", type=int, default=None, help="随机种子；缺省时自动生成并在输出中回传")
    roll.add_argument("--count", "-c", type=int, default=1, help="重复掷骰次数（默认 1）")
    roll.add_argument("--adventure", default=None, help="冒险目录；缺省从当前目录向上找 AGENTS.md")

    return parser


def cmd_roll(args: argparse.Namespace) -> int:
    n, m, modifier = parse_expr(args.expr)
    if args.count < 1:
        raise _lib.UsageError("--count must be >= 1")

    adventure = _lib.find_adventure(adventure=args.adventure)
    seed = args.seed if args.seed is not None else secrets.randbits(63)
    rng = random.Random(seed)

    results = [roll_once(rng, n, m, modifier) for _ in range(args.count)]
    totals = [r["total"] for r in results]
    output = {
        "ok": True,
        "command": "dice roll",
        "expr": args.expr,
        "seed": seed,
        "count": args.count,
        "results": results,
        "totals": totals,
        "total": sum(totals),
        "adventure": str(adventure),
    }
    log_path = _lib.log_event(
        adventure,
        "dice roll",
        {"expr": args.expr, "seed": seed, "count": args.count},
        {"totals": totals, "total": output["total"], "expr": args.expr},
        side_effects=["log/events.jsonl"],
    )
    output["logFile"] = str(log_path.relative_to(adventure))
    _lib.emit(output)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help(sys.stderr)
        return 2
    try:
        if args.command == "roll":
            return cmd_roll(args)
        raise _lib.UsageError(f"unknown command: {args.command}")
    except _lib.UsageError as exc:
        _lib.emit_error(str(exc), code="usage")
        return 2
    except (_lib.AdventureError, ValueError) as exc:
        _lib.emit_error(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
