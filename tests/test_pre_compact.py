#!/usr/bin/env python3
"""tests/test_pre_compact.py — stdlib のみ。python3 tests/test_pre_compact.py で実行。"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / ".codex" / "hooks" / "pre_compact.py"


def run_hook(payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=30,
    )


def make_workdir(tmp: str) -> tuple[Path, Path]:
    cwd = Path(tmp) / "proj"
    cwd.mkdir()
    transcript = Path(tmp) / "transcript.jsonl"
    transcript.write_text('{"role":"user"}\n', encoding="utf-8")
    return cwd, transcript


def test_snapshot_created() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd, transcript = make_workdir(tmp)
        proc = run_hook({"cwd": str(cwd), "transcript_path": str(transcript), "turn_id": "turn_abc12345"})
        assert proc.returncode == 0, proc.stderr
        snaps = list((cwd / ".harness" / "compaction-snapshots").glob("*.jsonl"))
        assert len(snaps) == 1, snaps
        assert snaps[0].read_text(encoding="utf-8") == '{"role":"user"}\n'


def test_rotation_keeps_10() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd, transcript = make_workdir(tmp)
        snap_dir = cwd / ".harness" / "compaction-snapshots"
        snap_dir.mkdir(parents=True)
        for i in range(12):
            f = snap_dir / f"20250101-0000{i:02d}-old.jsonl"
            f.write_text("x", encoding="utf-8")
        proc = run_hook({"cwd": str(cwd), "transcript_path": str(transcript), "turn_id": "t"})
        assert proc.returncode == 0, proc.stderr
        assert len(list(snap_dir.glob("*.jsonl"))) == 10


def test_stale_notes_no_warning() -> None:
    """鮮度警告は廃止済み: ノートが古くても stdout は空(複数セッション対応 spec)。"""
    with tempfile.TemporaryDirectory() as tmp:
        cwd, transcript = make_workdir(tmp)
        old = time.time() - 3600
        # レガシー単一ファイルと新形式ディレクトリの両方が古くても警告しない
        legacy = cwd / "working-notes.md"
        legacy.write_text("## 現在の状態と次の一手\n", encoding="utf-8")
        os.utime(legacy, (old, old))
        notes_dir = cwd / "working-notes"
        notes_dir.mkdir()
        note = notes_dir / "sample-task.md"
        note.write_text("## 現在の状態と次の一手\n", encoding="utf-8")
        os.utime(note, (old, old))
        proc = run_hook({"cwd": str(cwd), "transcript_path": str(transcript), "turn_id": "t"})
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip() == "", proc.stdout


def test_missing_transcript_is_noop() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp) / "proj"
        cwd.mkdir()
        proc = run_hook({"cwd": str(cwd), "transcript_path": str(Path(tmp) / "none.jsonl"), "turn_id": "t"})
        assert proc.returncode == 0, proc.stderr


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all tests passed")
