#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""``step`` —— git 步进的唯一入口（串行执行）。

子命令：
* ``step commit --message <msg> [--all] [--tag <name>]``
* ``step tag <name> [--force]``

所有 ``git add/commit/tag`` 只经由本工具；它以 ``<adventure>/.git/trpg.lock`` 上的
flock 串行化，避免多 channel 并发导致 ``index.lock`` 竞争。无变更时提交安全跳过。
"""

from __future__ import annotations

import argparse
import sys

import _lib

INPUTS = "commit: --message <msg> [--all] [--tag <name>]；tag: <name> [--force]"
OUTPUTS = "JSON: {committed, commit, tag} / {tag, commit}"
SIDE_EFFECTS = "git add -A / git commit / git tag；追加 log/events.jsonl"


def _has_changes(adventure) -> bool:
    status = _lib.git_run(adventure, ["status", "--porcelain"]).stdout.strip()
    return bool(status)


def _is_git_repo(adventure) -> bool:
    proc = _lib.git_run(adventure, ["rev-parse", "--git-dir"])
    return proc.returncode == 0


def do_commit(adventure, message: str, tag: str | None = None, *, force_tag: bool = False) -> dict:
    """串行执行 git add/commit（可选 tag），返回结果字典。不写 log、不打印。"""
    if not _is_git_repo(adventure):
        raise _lib.AdventureError(f"not a git repository: {adventure}")

    result: dict = {"ok": True, "command": "step commit", "adventure": str(adventure)}
    with _lib.git_lock(adventure):
        _lib.ensure_git_identity(adventure)
        _lib.git_run(adventure, ["add", "-A"], check=True)

        if _has_changes(adventure):
            proc = _lib.git_run(adventure, ["commit", "-m", message])
            if proc.returncode != 0:
                raise _lib.AdventureError(
                    f"git commit failed: {(proc.stderr or proc.stdout).strip()}"
                )
            sha = _lib.git_run(adventure, ["rev-parse", "--short", "HEAD"]).stdout.strip()
            result.update({"committed": True, "commit": sha, "message": message})
        else:
            result.update({"committed": False, "reason": "no changes to commit"})

        if tag:
            tag_args = ["tag"] + (["-f"] if force_tag else []) + [tag]
            tag_proc = _lib.git_run(adventure, tag_args)
            if tag_proc.returncode != 0:
                raise _lib.AdventureError(
                    f"git tag failed: {(tag_proc.stderr or tag_proc.stdout).strip()}"
                )
            result["tag"] = tag
    return result


def do_tag(adventure, name: str, *, force: bool = False) -> dict:
    """串行执行 git tag，返回结果字典。不写 log、不打印。"""
    if not _is_git_repo(adventure):
        raise _lib.AdventureError(f"not a git repository: {adventure}")
    git_args = ["tag"]
    if force:
        git_args.append("-f")
    git_args.append(name)
    with _lib.git_lock(adventure):
        proc = _lib.git_run(adventure, git_args)
        if proc.returncode != 0:
            raise _lib.AdventureError(
                f"git tag failed: {(proc.stderr or proc.stdout).strip()}"
            )
        sha = _lib.git_run(adventure, ["rev-parse", "--short", "HEAD"]).stdout.strip()
    return {
        "ok": True,
        "command": "step tag",
        "tag": name,
        "commit": sha,
        "forced": force,
        "adventure": str(adventure),
    }


def cmd_commit(args: argparse.Namespace) -> int:
    adventure = _lib.find_adventure(adventure=args.adventure)
    result = do_commit(adventure, args.message, args.tag)
    _lib.log_event(
        adventure,
        "step commit",
        {"message": args.message, "all": args.all, "tag": args.tag},
        result,
        side_effects=["git commit"] + ([f"git tag {args.tag}"] if args.tag else []) + ["log/events.jsonl"],
    )
    _lib.emit(result)
    return 0


def cmd_tag(args: argparse.Namespace) -> int:
    adventure = _lib.find_adventure(adventure=args.adventure)
    output = do_tag(adventure, args.name, force=args.force)
    _lib.log_event(
        adventure,
        "step tag",
        {"name": args.name, "force": args.force},
        output,
        side_effects=[f"git tag {args.name}", "log/events.jsonl"],
    )
    _lib.emit(output)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="step",
        description=(
            "git 步进的唯一入口：提交粒度 = 每条消息/每步；边界 tag 标记场景与 flow 阶段。\n"
            "所有 git 操作经 .git/trpg.lock 串行，避免并发 index.lock。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_lib.help_epilog(
            inputs=INPUTS,
            outputs=OUTPUTS,
            side_effects=SIDE_EFFECTS,
            exit_codes="0 成功；1 业务失败；2 用法错误",
        ),
    )
    parser.add_argument("--version", action="version", version=f"step {_lib.VERSION}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    commit = sub.add_parser(
        "commit",
        help="串行 git add/commit（无变更安全跳过）",
        description="git add -A 后提交；无变更则不提交（退出码仍为 0）。--tag 时提交后打 tag。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_lib.help_epilog(
            inputs=INPUTS,
            outputs=OUTPUTS,
            side_effects=SIDE_EFFECTS,
            exit_codes="0 成功；1 业务失败；2 用法错误",
        ),
    )
    commit.add_argument("--message", "-m", required=True, help="提交信息（建议结构化）")
    commit.add_argument("--all", action="store_true", help="暂存全部变更（do_commit 恒执行 git add -A；保留以兼容契约）")
    commit.add_argument("--tag", default=None, help="提交后附带打 tag，如 phase/combat")
    commit.add_argument("--adventure", default=None, help="冒险目录；缺省向上找 AGENTS.md")

    tag = sub.add_parser(
        "tag",
        help="串行打边界 tag",
        description="在当前 HEAD 打 tag，用于标记场景/阶段边界。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_lib.help_epilog(
            inputs=INPUTS,
            outputs=OUTPUTS,
            side_effects=SIDE_EFFECTS,
            exit_codes="0 成功；1 业务失败；2 用法错误",
        ),
    )
    tag.add_argument("name", help="tag 名称，如 scene/003-central-room")
    tag.add_argument("--force", action="store_true", help="覆盖同名 tag")
    tag.add_argument("--adventure", default=None, help="冒险目录；缺省向上找 AGENTS.md")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help(sys.stderr)
        return 2
    try:
        return {"commit": cmd_commit, "tag": cmd_tag}[args.command](args)
    except _lib.UsageError as exc:
        _lib.emit_error(str(exc), code="usage")
        return 2
    except (_lib.AdventureError, OSError) as exc:
        _lib.emit_error(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
