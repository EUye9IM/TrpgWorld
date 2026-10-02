#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""TrpgWorld 工具共享库。

本模块被 ``tools/`` 下的所有确定性 CLI 工具导入使用。它只依赖 Python 标准库，
因此既可以用 ``uv run tools/<tool>.py`` 也可以用 ``python3 tools/<tool>.py`` 运行。

提供的能力：

* 冒险目录定位（``--adventure`` 或从当前目录向上查找 ``AGENTS.md``）。
* 统一的 JSON 标准输出。
* ``log/events.jsonl`` 审计追加（每次工具调用一条）。
* 基于 ``flock`` 的 git 串行锁（``<adventure>/.git/trpg.lock``）。
* 声明式 World State mask：JSON 路径 glob 匹配、首命中定档、投影组装。
"""

from __future__ import annotations

import fcntl
import fnmatch
import json
import os
import re
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

VERSION = "1.0.0"

#: 认为“可见”的哨兵值：public 表示所有人可见。
PUBLIC = "public"


class AdventureError(Exception):
    """业务级错误：对应退出码 1。"""


class UsageError(Exception):
    """用法级错误：对应退出码 2。"""


# ---------------------------------------------------------------------------
# 基础：JSON / 时间 / 输出
# ---------------------------------------------------------------------------

def iso_now() -> str:
    """返回带时区的 UTC ISO-8601 时间戳。"""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def emit(obj: Any) -> None:
    """把对象以 JSON 打印到 stdout（UTF-8，不转义非 ASCII）。"""
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def emit_error(message: str, *, code: str = "error", extra: dict | None = None) -> None:
    """把错误以 JSON 打印到 stdout（契约：标准输出始终是 JSON）。"""
    payload: dict[str, Any] = {"ok": False, "error": code, "message": message}
    if extra:
        payload.update(extra)
    emit(payload)


def read_json(path: str | Path, default: Any = None) -> Any:
    """读取 JSON 文件；不存在或为空时返回 ``default``。"""
    p = Path(path)
    if not p.exists():
        return default
    text = p.read_text(encoding="utf-8").strip()
    if not text:
        return default
    return json.loads(text)


def write_json(path: str | Path, obj: Any) -> Path:
    """原子写 JSON 文件（UTF-8，缩进 2，末尾换行）。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, p)
    return p


# ---------------------------------------------------------------------------
# 冒险目录定位
# ---------------------------------------------------------------------------

def find_adventure(*, adventure: str | None = None, start: str | Path | None = None) -> Path:
    """定位冒险目录。

    * 显式 ``--adventure <path>`` 优先（路径必须存在）。
    * 否则从 ``start``（默认当前目录）向上查找含 ``AGENTS.md`` 的目录。
    """
    if adventure:
        p = Path(adventure).expanduser().resolve()
        if not p.is_dir():
            raise AdventureError(f"adventure directory does not exist: {p}")
        return p

    p = Path(start if start is not None else Path.cwd()).expanduser().resolve()
    for cand in (p, *p.parents):
        if (cand / "AGENTS.md").exists():
            return cand
    raise AdventureError(
        "could not locate adventure directory: pass --adventure <path> or run inside "
        "a directory containing AGENTS.md"
    )


# ---------------------------------------------------------------------------
# 审计日志 log/events.jsonl
# ---------------------------------------------------------------------------

def log_event(
    adventure: str | Path,
    tool: str,
    args: dict | None = None,
    result: Any = None,
    side_effects: list[str] | None = None,
) -> Path:
    """向 ``<adventure>/log/events.jsonl`` 追加一条工具调用记录。"""
    adv = Path(adventure)
    log_dir = adv / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": iso_now(),
        "tool": tool,
        "args": args or {},
        "result": result,
        "sideEffects": side_effects or [],
    }
    path = log_dir / "events.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    return path


# ---------------------------------------------------------------------------
# git 串行锁
# ---------------------------------------------------------------------------

@contextmanager
def git_lock(adventure: str | Path, *, timeout: float = 30.0) -> Iterator[None]:
    """用 ``<adventure>/.git/trpg.lock`` 上的 flock 串行化 git 操作。

    多个 channel 可能并发触发提交；统一由 ``step *`` 走本锁，避免 ``index.lock`` 竞争。
    """
    adv = Path(adventure)
    lock_path = adv / ".git" / "trpg.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fh = lock_path.open("w", encoding="utf-8")
    deadline = time.monotonic() + timeout
    try:
        while True:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() > deadline:
                    raise AdventureError(
                        f"timed out waiting for git lock: {lock_path}"
                    )
                time.sleep(0.05)
        yield
    finally:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        finally:
            fh.close()


def git_init(adventure: str | Path) -> subprocess.CompletedProcess:
    """在目标目录执行 ``git init``（目录需已存在）。"""
    return subprocess.run(
        ["git", "-C", str(Path(adventure)), "init", "-q"], capture_output=True, text=True
    )


def git_run(
    adventure: str | Path,
    args: list[str],
    *,
    check: bool = False,
) -> subprocess.CompletedProcess:
    """在冒险目录内运行 git 子命令。"""
    cmd = ["git", "-C", str(Path(adventure)), *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise AdventureError(
            f"git {' '.join(args)} failed ({proc.returncode}): "
            f"{(proc.stderr or proc.stdout).strip()}"
        )
    return proc


def ensure_git_identity(adventure: str | Path) -> None:
    """确保仓库内可用 git 提交（缺 user.name/email 时写本地兜底配置）。"""
    name = git_run(adventure, ["config", "user.name"]).stdout.strip()
    email = git_run(adventure, ["config", "user.email"]).stdout.strip()
    if not name:
        git_run(adventure, ["config", "user.name", "TrpgWorld"])
    if not email:
        git_run(adventure, ["config", "user.email", "trpgworld@localhost"])


# ---------------------------------------------------------------------------
# World State mask：JSON 路径 glob
# ---------------------------------------------------------------------------

def _split_path(path: str) -> list[str]:
    return [seg for seg in str(path).split("/") if seg != ""]


def match_path(pattern: str, path: str) -> bool:
    """JSON 路径 glob 匹配。

    * ``*``  匹配恰好一层（段内也可用通配，如 ``true_*``）。
    * ``**`` 匹配零层或多层子树。
    * 其余按字面匹配。
    """
    pat = _split_path(pattern)
    segs = _split_path(path)

    def rec(pi: int, si: int) -> bool:
        if pi == len(pat):
            return si == len(segs)
        if pat[pi] == "**":
            for nxt in range(si, len(segs) + 1):
                if rec(pi + 1, nxt):
                    return True
            return False
        if si >= len(segs):
            return False
        if pat[pi] == "*":
            return rec(pi + 1, si + 1)
        if fnmatch.fnmatchcase(segs[si], pat[pi]):
            return rec(pi + 1, si + 1)
        return False

    return rec(0, 0)


def iter_leaves(obj: Any, prefix: str = "") -> Iterator[tuple[str, Any]]:
    """遍历 JSON 对象，产出 ``(路径, 叶子值)``。

    空 dict / 空 list 也视为叶子，便于整棵子树被 mask 规则命中或放行。
    """
    if isinstance(obj, dict):
        if not obj:
            yield prefix, obj
            return
        for key, value in obj.items():
            yield from iter_leaves(value, f"{prefix}/{key}")
    elif isinstance(obj, list):
        if not obj:
            yield prefix, obj
            return
        for idx, value in enumerate(obj):
            yield from iter_leaves(value, f"{prefix}/{idx}")
    else:
        yield prefix, obj


def _audience_allows(audience: Any, role: str) -> bool:
    """判断某条 audience 声明是否允许该 role。"""
    if audience is None:
        return False
    if isinstance(audience, str):
        return audience == PUBLIC or audience == role or audience == "*"
    if isinstance(audience, (list, tuple, set)):
        return role in audience or PUBLIC in audience or "*" in audience
    return False


def decide_path(
    path: str,
    visibility: dict,
    role: str,
) -> tuple[str | None, Any, bool]:
    """按 visibility mask 判定单条路径。

    返回 ``(命中的 rule pattern 或 None, audience, visible)``。
    规则列表「首个命中定档」，未命中则用 ``default``。
    """
    for rule in visibility.get("rules", []) or []:
        pattern = rule.get("pattern")
        if pattern and match_path(pattern, path):
            audience = rule.get("audience")
            return pattern, audience, _audience_allows(audience, role)
    default = visibility.get("default", PUBLIC)
    return None, default, _audience_allows(default, role)


def set_path(root: dict, path: str, value: Any) -> None:
    """按 JSON 路径把值写进（可能为空的）嵌套结构。"""
    segs = _split_path(path)
    if not segs:
        return
    cur: Any = root
    for i, seg in enumerate(segs[:-1]):
        nxt = segs[i + 1]
        want_list = nxt.isdigit()
        if isinstance(cur, list):
            idx = int(seg)
            while len(cur) <= idx:
                cur.append(None)
            if cur[idx] is None:
                cur[idx] = [] if want_list else {}
            cur = cur[idx]
        else:
            if seg not in cur or cur[seg] is None:
                cur[seg] = [] if want_list else {}
            cur = cur[seg]
    last = segs[-1]
    if isinstance(cur, list):
        idx = int(last)
        while len(cur) <= idx:
            cur.append(None)
        cur[idx] = value
    else:
        cur[last] = value


def build_projection(
    state: Any,
    visibility: dict,
    role: str,
) -> tuple[Any, list[dict]]:
    """按 mask 为 role 组装可见投影，并返回逐路径审计明细。"""
    projection: dict[str, Any] = {}
    details: list[dict] = []
    for path, value in iter_leaves(state):
        pattern, audience, visible = decide_path(path, visibility, role)
        details.append(
            {
                "path": path,
                "rule": pattern if pattern is not None else "default",
                "audience": audience,
                "visible": visible,
            }
        )
        if visible:
            set_path(projection, path, value)
    return projection, details


def read_visibility(adventure: str | Path) -> dict:
    """读取 ``world/visibility.json``；缺省为全公开、无规则。"""
    data = read_json(Path(adventure) / "world" / "visibility.json", None)
    if not isinstance(data, dict):
        return {"default": PUBLIC, "rules": []}
    data.setdefault("default", PUBLIC)
    data.setdefault("rules", [])
    return data


# ---------------------------------------------------------------------------
# CLI 辅助
# ---------------------------------------------------------------------------

def safe_id(value: Any, *, kind: str = "id") -> str:
    """校验角色/频道等标识符，禁止路径穿越。

    标识符会被拼进 ``<adventure>/roles/<id>/``、``channels/<id>/`` 等路径；若允许
    ``/``、``\\``、``..`` 等字符，就能读写冒险目录之外的文件，破坏「可见性靠文件
    位置保证」这一安全前提。非法的标识符一律按用法错误（退出码 2）拒绝。
    """
    text = str(value or "")
    if (
        not text
        or text in {".", ".."}
        or "/" in text
        or "\\" in text
        or "\x00" in text
        or any(ord(ch) < 32 for ch in text)
    ):
        raise UsageError(
            f"invalid {kind}: {value!r} "
            "(must be non-empty and must not contain path separators, NUL or control chars)"
        )
    return text


def slugify(text: str, *, fallback: str = "item") -> str:
    """把标题转为文件系统安全的 slug（保留中文与字母数字）。"""
    text = (text or "").strip()
    text = re.sub(r"^[\s\d.、)）:：\-]+", "", text)
    text = re.sub(r"[\\/:*?\"<>|\n\r\t]+", "-", text)
    text = re.sub(r"[\s,，。;；]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-.")
    return text or fallback


def help_epilog(*, inputs: str, outputs: str, side_effects: str, exit_codes: str) -> str:
    """统一格式的 ``--help`` epilog：输入/输出/副作用/退出码。

    配合 ``argparse.RawDescriptionHelpFormatter`` 使用以保留换行。
    """
    return (
        f"输入: {inputs}\n"
        f"输出: {outputs} (stdout JSON)\n"
        f"副作用: {side_effects}\n"
        f"退出码: {exit_codes}"
    )
