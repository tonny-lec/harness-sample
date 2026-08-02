#!/usr/bin/env python3
"""Codex PreCompact hook: transcript のスナップショット保存とノート鮮度の警告。

設計: docs/superpowers/specs/2026-08-01-state-externalization-design.md 1-3節。
compaction はブロックしない。モデルへの注入は行わない(仕様上不可)。
"""
import json
import shutil
import sys
import time
from pathlib import Path

KEEP = 10
STALE_SECONDS = 30 * 60


def main() -> int:
    payload = json.load(sys.stdin)
    cwd = Path(payload.get("cwd") or ".")

    transcript = payload.get("transcript_path") or ""
    src = Path(transcript)
    if src.is_file():
        snap_dir = cwd / ".harness" / "compaction-snapshots"
        snap_dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        turn = (payload.get("turn_id") or "x")[:12]
        shutil.copy2(src, snap_dir / f"{stamp}-{turn}.jsonl")
        for old in sorted(snap_dir.glob("*.jsonl"))[:-KEEP]:
            old.unlink()

    notes = cwd / "working-notes.md"
    if notes.is_file() and time.time() - notes.stat().st_mtime > STALE_SECONDS:
        print(json.dumps({
            "systemMessage": "working-notes.md が30分以上更新されないまま compaction が実行されます。状態の取りこぼしに注意してください。"
        }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
