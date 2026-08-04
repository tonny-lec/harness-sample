#!/usr/bin/env python3
"""Codex PostCompact hook: compaction 発生をユーザーへ通知する。"""
import json
import sys


def main() -> int:
    sys.stdin.read()  # payload は使わないが読み切る
    print(json.dumps({
        "systemMessage": "compaction が実行されました。エージェントは担当タスクのノート(working-notes/<topic>.md)を読み直して状態を確認します。"
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
