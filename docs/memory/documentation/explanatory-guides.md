---
type: Memory
title: 状態保存・復元ライフサイクルの解説
description: 起動から完了までの処理フローを実装に沿って説明する独立文書を作成した。
tags: [documentation, codex-hooks, state-externalization, lifecycle]
generated: { by: openai/codex, at: 2026-08-02T00:00:00+09:00 }
---

# 計画

既存 README の導入手順とは役割を分け、起動・平時・compaction 前後・再開・完了という
時間的な流れを軸に、状態の保存先と各 hook の責任を説明する。

# 仮説と検証結果

- 仮説: 既存 README が導入ファーストであるため、新規文書を処理フロー中心にすると
  重複を抑えながら仕組みを説明できる。
- 検証結果: `AGENTS.md`、3つの hook、hook 登録、単体テストを照合し、実装の流れが
  起動・平時・PreCompact・PostCompact・再開・worklog 化に対応することを確認した。
- 検証結果: PreCompact の単体テスト5件、SessionStart の単体テスト3件、hook JSON、
  文書リンク、`git diff --check` がすべて成功した。

# 発見

- 通常の状態復元には `working-notes.md`、恒久知識には `docs/worklog/`、不足情報の
  最終確認には `.harness/compaction-snapshots/` と、保存先ごとに役割が異なる。
- `post_compact.py` は通知だけを行い、状態注入はしない。compaction 直後の再読は
  `AGENTS.md`、起動・再開時の状態出力は `session_start.py` が担当する。
- 単体テストは通るが、Codex CLI 上で hook 発火からタスク完了までを通す実機 E2E は
  引き続き未完了である。

# 判断とその理由

- ユーザー指定の案Aを採用し、`docs/state-lifecycle.md` を新規作成した。既存 README を
  変更しなかったのは、未追跡のユーザー変更を保護し、導入手順と仕組み解説の役割を
  分けるため。
- 案Bは採用しなかった。既存 README と設計書の構成・内容との重複が増えるため。
- 実装済みの単体動作と未完了の実機 E2E を明確に分け、後者を検証済みとは記載しない。

