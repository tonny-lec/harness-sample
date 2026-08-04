#!/usr/bin/env python3
"""Codex PreCompact hook: transcript のスナップショット保存。

設計: docs/superpowers/specs/2026-08-01-state-externalization-design.md 1-3節、
および docs/superpowers/specs/2026-08-04-multi-session-working-notes-design.md。
compaction はブロックしない。モデルへの注入は行わない(仕様上不可)。
ノート鮮度の警告は複数セッション対応で廃止した: hook はセッションとノートの
対応を知り得ず、mtime 判定は他セッションの更新で偽陰性になるため。
例外時は常に exit 0(compaction をブロックしない)。
"""
import json
import shutil
import sys
import time
from pathlib import Path

KEEP = 10


def main() -> int:
    try:
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
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
