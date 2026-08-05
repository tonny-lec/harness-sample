---
type: Memory
title: 導入者向け README 草案
description: 構成2案を比較し、導入ファースト構成で現行実装に沿う README を作成した。
tags: [readme, documentation, codex-hooks, state-externalization]
generated: { by: openai/codex, at: 2026-08-02T00:00:00+09:00 }
---

# 計画

リポジトリの実装、設計書、実装計画を再確認し、既存資料からは決められない主読者を
確認する。主読者に合う構成を2案比較してから1案を選び、README 草案を作成する。

# 仮説と検証結果

- 仮説: 主読者が導入者なら、背景や内部構造から始めるより、課題・前提・導入・確認の
  順にしたほうが最短で利用開始できる。
- 検証結果: 主読者は「このハーネスを自分のプロジェクトへ導入したい利用者」と確認した。
  詳細な背景と設計判断は既存の設計書にすでに記載されている。
- 検証結果: 実装は `AGENTS.md` の記録ルール、PreCompact / PostCompact /
  SessionStart hook、OKF worklog、PreCompact / SessionStart の単体テストで構成される。
- 検証結果: 単体テスト8件、`.codex/hooks.json` の JSON 検証、README のリンク先存在確認、
  `git diff --check` がすべて成功した。

# 発見

- PreCompact は transcript の退避、直近10件へのローテーション、30分以上古いノートの
  警告を担当する。
- PostCompact は compaction 発生を通知し、SessionStart は起動・再開時に
  `working-notes.md` の状態セクションを注入する。
- hook 自体は推論を書き出さない。推論の随時記録は `AGENTS.md` のルールが担う。
- Claude Code 対応は設計上のフェーズ2であり未実装。Codex CLI 実機でタスク全体を通す
  E2E 検証も未完了である。
- `.codex/config.toml` と既存 worklog の変更は README 作業以前から存在するため、
  導入対象にも今回の変更範囲にも含めなかった。

# 判断とその理由

- 案A「導入ファースト」を採用した。構成は、課題、対応状況、前提条件、導入手順、
  普段の使い方、仕組み、テスト、制約、詳細資料の順。主読者が最短で試せるため。
- 案B「仕組みファースト」は採用しなかった。設計理解には向くが導入までが長くなり、
  既存設計書との重複も増えるため。
- README では Codex CLI 対応だけを実装済みとし、Claude Code 対応と実機 E2E を
  完了済みと表現しない。
- 導入手順は `.codex/` 全体のコピーを指示せず、3つの hook と `hooks.json` だけを
  明示した。README 作業と無関係な設定を導入先へ持ち込まないため。

# 確定した事実と知識

- 最初の最小ノート例では見出しを `#` にしたが、`session_start.py` が状態セクションと
  認識する文字列は `## 現在の状態と次の一手` である。README の例を `##` に修正した。
  フォールバックで出力できるだけでは、本来の状態セクション抽出を検証したことにならない。
