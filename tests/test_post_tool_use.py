#!/usr/bin/env python3
"""tests/test_post_tool_use.py — stdlib のみ。python3 tests/test_post_tool_use.py で実行。"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / ".codex" / "hooks" / "post_tool_use.py"


def run_hook(cwd: Path, raw: str = None) -> subprocess.CompletedProcess:
    data = raw if raw is not None else json.dumps({"cwd": str(cwd)})
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=data,
        capture_output=True,
        text=True,
        timeout=30,
    )


def make_note(cwd: Path, age_seconds: float = 0.0) -> Path:
    notes = cwd / "working-notes"
    notes.mkdir(exist_ok=True)
    note = notes / "sample-task.md"
    note.write_text("## 現在の状態と次の一手\n", encoding="utf-8")
    if age_seconds:
        old = time.time() - age_seconds
        os.utime(note, (old, old))
    return note


def make_stamp(cwd: Path, age_seconds: float = 0.0) -> Path:
    stamp = cwd / ".harness" / "note-reminder-stamp"
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.touch()
    if age_seconds:
        old = time.time() - age_seconds
        os.utime(stamp, (old, old))
    return stamp


def reminder_emitted(proc: subprocess.CompletedProcess) -> bool:
    if not proc.stdout.strip():
        return False
    out = json.loads(proc.stdout)
    return "working-notes/ の担当ノート" in proc.stdout and "additionalContext" in proc.stdout and isinstance(out, dict)


def test_no_notes_reminds() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        proc = run_hook(cwd)
        assert proc.returncode == 0, proc.stderr
        assert reminder_emitted(proc), proc.stdout
        assert (cwd / ".harness" / "note-reminder-stamp").is_file()


def test_fresh_note_silent() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        make_note(cwd)
        proc = run_hook(cwd)
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip() == "", proc.stdout


def test_stale_note_reminds() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        make_note(cwd, age_seconds=600)
        proc = run_hook(cwd)
        assert proc.returncode == 0, proc.stderr
        assert reminder_emitted(proc), proc.stdout


def test_cooldown_suppresses() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        make_note(cwd, age_seconds=600)
        make_stamp(cwd)  # 直前に注入済み
        proc = run_hook(cwd)
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip() == "", proc.stdout


def test_expired_stamp_reminds_and_touches() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        make_note(cwd, age_seconds=600)
        stamp = make_stamp(cwd, age_seconds=600)
        proc = run_hook(cwd)
        assert proc.returncode == 0, proc.stderr
        assert reminder_emitted(proc), proc.stdout
        assert time.time() - stamp.stat().st_mtime < 60  # stamp が更新された


def test_malformed_stdin_silent() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        proc = run_hook(Path(tmp), raw="not json")
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip() == "", proc.stdout


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all tests passed")
