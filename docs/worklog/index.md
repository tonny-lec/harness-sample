---
type: Index
title: Worklog
description: タスクごとの推論の記録(OKF v0.2 バンドル)。1 タスク = 1 ファイル。
timestamp: 2026-08-02T00:00:00Z
---

# Worklog

タスク完了時に `working-notes.md` から移したエントリの一覧。新しいものを上に追記する。

## エントリ一覧

(まだエントリはない)

## エントリの書式

ファイル名: `YYYY-MM-DD-<topic>.md`。frontmatter の必須は `type` のみ、他は推奨。

```text
---
type: Worklog
title: <タスクの短い題>
description: <1 行要約>
tags: [<領域タグ>]
timestamp: <ISO 8601 更新日時>
actor: <書き手。エージェントは <producer>/<version>、人は human:<id>>
---

# 計画
# 仮説と検証結果
# 発見
# 判断とその理由
# 失敗から得た知識
```

空の見出しは削ってよい。関連する過去エントリへは通常の Markdown リンクで参照する。
