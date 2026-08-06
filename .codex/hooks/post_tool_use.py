#!/usr/bin/env python3
"""Codex PostToolUse hook: 担当タスクのファイルが古いままのとき、確認・状態の書き換えとノートへの追記・作業再開を促す手順を注入する。

設計: docs/superpowers/specs/2026-08-05-rule-firing-reinforcement-design.md。
どのノートがこのセッションのものかは hook には知り得ないため、内容レスの定型
リマインダーのみを注入する(誤ったノートの注入は有害、内容レスの想起は無害)。
複数セッション並行時の偽陰性(他セッションの更新・注入による抑制)は許容する。
例外時は常に exit 0(ツール実行をブロックしない)。
"""
import json
import sys
import time
from pathlib import Path

STALE_SECONDS = 180
COOLDOWN_SECONDS = 180

REMINDER = (
    "working-notes/ の担当タスクのファイルが 3 分以上更新されていません。次の手順を実行してください:\n"
    "1. 現在のタスク専用の状態ファイル `working-notes/<topic>.state.md` とノート `working-notes/<topic>.md` があるか確認し、なければ作成する(別タスクのファイルを流用しない)\n"
    "2. 状態ファイルの内容全体を、現時点の 目的 / 状態 / 決定 / 次の一手 の箇条書きに書き換える(前の内容は消してよい。古い状態を残して積み重ねない)\n"
    "3. 直近の判断・検証結果をノートに追記する(数行)\n"
    "4. 中断していた作業を再開する\n"
    "\n"
    "docs/memory/ への統合はタスク完了時に行う。"
)


def newest_note_mtime(notes_dir: Path) -> float:
    if not notes_dir.is_dir():
        return 0.0
    mtimes = [p.stat().st_mtime for p in notes_dir.glob("*.md")]
    return max(mtimes, default=0.0)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        cwd = Path(payload.get("cwd") or ".")
        now = time.time()
        if now - newest_note_mtime(cwd / "working-notes") <= STALE_SECONDS:
            return 0
        stamp = cwd / ".harness" / "note-reminder-stamp"
        if stamp.is_file() and now - stamp.stat().st_mtime <= COOLDOWN_SECONDS:
            return 0
        stamp.parent.mkdir(parents=True, exist_ok=True)
        stamp.touch()
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": REMINDER,
            }
        }, ensure_ascii=False))
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
