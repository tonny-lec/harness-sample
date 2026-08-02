#!/usr/bin/env python3
"""tests/test_session_start.py — stdlib のみ。python3 tests/test_session_start.py で実行。"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / ".codex" / "hooks" / "session_start.py"

NOTES = """## 現在の状態と次の一手

- 状態: Task 3 まで完了
- 次の一手: Task 4 のテストを書く

## 推論の記録

- 2026-08-02 選択: A案を採用。理由: ...
"""


def run_hook(cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"cwd": str(cwd)}),
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_no_notes_is_silent() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        proc = run_hook(Path(tmp))
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip() == "", proc.stdout


def test_state_section_injected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "working-notes.md").write_text(NOTES, encoding="utf-8")
        proc = run_hook(Path(tmp))
        assert "現在の状態と次の一手" in proc.stdout
        assert "Task 4 のテストを書く" in proc.stdout
        # 推論の記録(追記部)は注入しない
        assert "A案を採用" not in proc.stdout
        # 全文への誘導がある
        assert "working-notes.md" in proc.stdout


def test_notes_without_state_section_fallback() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "working-notes.md").write_text("メモだけがある\n", encoding="utf-8")
        proc = run_hook(Path(tmp))
        assert "working-notes.md" in proc.stdout
        assert "メモだけがある" in proc.stdout


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all tests passed")
