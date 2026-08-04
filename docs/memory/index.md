---
type: Index
title: Memory
description: タスクから蒸留した記憶(OKF v0.2 バンドル)。カテゴリごとに配置し、同トピックは 1 ファイルに統合する。
---

# Memory

タスク完了時に担当タスクのノート(`working-notes/<topic>.md`)から統合した記憶。
同じトピックの新しい知見は既存ファイルを更新する(経緯は git 履歴が担う)。

## カテゴリ

- [harness/](harness/index.md) — ハーネス自体の挙動・検証の知見
- [documentation/](documentation/index.md) — 文書の作成・校閲の知見
- [testing/](testing/index.md) — テスト設計・網羅性の知見
- [policy/](policy/index.md) — リポジトリ運用方針

合うカテゴリがない記憶は新しいカテゴリを作り、この一覧に 1 行追記する。

## 記憶の書式

ファイル名: `<category>/<topic>.md`(日付なし・短いケバブケース)。

```text
---
type: Memory
title: <記憶の短い題>
description: <1 行要約>
tags: [<横断タグ>]
generated: { by: <actor>, at: <ISO 8601 最終更新日時> }
---

# 計画
# 仮説と検証結果
# 発見
# 判断とその理由
# 失敗から得た知識
```

空の見出しは削ってよい。`generated.by` の actor は、エージェントは
`<producer>/<version>`、人は `human:<id>`。必要な記憶にだけ任意で
`verified: {by, at}` / `status: draft|stable|deprecated` /
`stale_after: YYYY-MM-DD` を付ける。記憶間のリンクはバンドルルート絶対パス
(例: `/harness/e2e-verification.md`)を推奨する。
