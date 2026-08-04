---
type: Worklog
title: 複数セッション対応の実機 E2E 検証
description: working-notes 分割後の並行 2 セッション・再開・完了フローの検証結果
tags: [harness, e2e, multi-session]
timestamp: 2026-08-04T00:00:00Z
actor: claude-code/fable-5
---

# 計画

[複数セッション対応の設計](../superpowers/specs/2026-08-04-multi-session-working-notes-design.md)の検証方法 2・3 を実機 codex で検証。同一ディレクトリで 2 セッションを並行起動し、別タスク(README 誤字チェック / PreCompact テスト網羅性分析)を実行した。

# 仮説と検証結果

- 起動確認: ✅ SessionStart 登録を削除した hooks.json で、Codex CLI が警告・エラーなく起動した
- (a) 並行分離: ✅ 各セッションが別名の `working-notes/<topic>.md` を作成し、互いのノートを上書きしなかった
- (b) 完了時の分離: ✅ 完了したタスクのノートだけが `docs/worklog/` へ移って削除され、他セッションのノートは残った
- (c) 再開: ✅ 途中状態のノート(`state-lifecycle-typos`: 3節までチェック済みの設定)を置いた状態で新セッションに曖昧に続きを依頼したところ、AGENTS.md ルールに従ってノートを読み、未着手の 4 節以降だけを実施し、完了時に worklog 化とノート削除まで行った。SessionStart hook なしでもルールのみで状態復元が機能した
- gitignore: ✅ `working-notes/` 配下が untracked に出ないことを確認(`git check-ignore` で旧 `working-notes.md` パターンも有効)

# 発見

- 小さいタスクは 1 プロンプトで完了し、ノートが即 worklog へ蒸留されるため、(a)(b) の検証だけでは再開経路 (c) を通れない。(c) の検証には途中状態のノートを人工的に用意する必要があった。

# 判断とその理由

(c) は人工的に作成した途中ノートで検証した。実運用での中断はタイミングの再現が難しく、ノートが規約どおりの二部構成であれば「新セッションがノートを発見して読む → 次の一手から再開する」という検証対象の経路は同一のため、等価な検証と判断した。
