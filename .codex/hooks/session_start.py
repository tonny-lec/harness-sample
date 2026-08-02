#!/usr/bin/env python3
"""Codex SessionStart hook: working-notes.md 冒頭の状態セクションをコンテキストへ注入する。

stdout が additionalContext として注入される(既定上限 2,500 トークン)ため、
「現在の状態と次の一手」セクションのみを出し、全文はファイル参照へ誘導する。
設計: docs/superpowers/specs/2026-08-01-state-externalization-design.md 1-4節。
"""
import json
import sys
from pathlib import Path

STATE_HEADING = "## 現在の状態と次の一手"
FALLBACK_LINES = 40


def extract_state_section(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    in_state = False
    for line in lines:
        if line.startswith("## "):
            if in_state:
                break
            in_state = line.strip() == STATE_HEADING
            if in_state:
                out.append(line)
            continue
        if in_state:
            out.append(line)
    if out:
        return "\n".join(out).strip()
    return "\n".join(lines[:FALLBACK_LINES]).strip()


def main() -> int:
    payload = json.load(sys.stdin)
    notes = Path(payload.get("cwd") or ".") / "working-notes.md"
    if not notes.is_file():
        return 0
    section = extract_state_section(notes.read_text(encoding="utf-8"))
    if not section:
        return 0
    print("前回までの作業ノート(working-notes.md より):")
    print(section)
    print()
    print("続きを始める前に working-notes.md 全文を読んで状態を確認すること。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
