---
type: Memory
title: PostCompact hook レビュー
description: 通知 JSON は現行契約に適合するが、相対パス起動と非 UTF-8 stdout に改善余地がある
tags: [testing, codex-hooks, post-compact, portability]
generated: { by: codex/gpt-5, at: 2026-08-04T16:54:33+09:00 }
---

# 計画

`.codex/hooks/post_compact.py` の責務、Codex hook の入出力契約、登録方法、既存テストを照合し、正常系と失敗条件を subprocess で確認する。

# 仮説と検証結果

- 仮説: `systemMessage` だけを返す JSON は PostCompact の有効な出力である。検証結果: 2026-08-04 取得の公式 Codex manual で、PostCompact は common output fields の `systemMessage` をサポートすると確認した。既定 locale で出力を `python3 -m json.tool` に渡しても成功した。
- 仮説: `.codex/hooks.json` の相対 command はセッション cwd がサブディレクトリだと壊れる。検証結果: `docs/` から同じ command を実行すると exit 2 となり、`docs/.codex/hooks/post_compact.py` が存在しないため起動できなかった。公式 manual も repo-local hook は git root から解決するよう推奨している。
- 仮説: `ensure_ascii=False` は stdout が ASCII の環境で失敗する。検証結果: `PYTHONUTF8=0 PYTHONCOERCECLOCALE=0 LC_ALL=C` で exit 1 と `UnicodeEncodeError` を再現した。

# 発見

- `tests/` には PostCompact 専用テストがなく、正常 JSON、サブディレクトリ cwd、非 UTF-8 stdout の回帰を検知できない。
- `sys.stdin.read()` は payload を使わない現設計では機能判断に寄与しないが、Codex が JSON object を stdin へ渡して EOF を閉じる契約では直ちに不具合ではない。

# 判断とその理由

- 最優先は `.codex/hooks.json` の command を git root 基準にすること。一般的なサブディレクトリ開始で hook 自体が起動しないため。対象スクリプト単体より統合部の問題だが、実効性に直結する。
- 次に `json.dumps` の ASCII escape を許可すること。JSON の意味は変えず、stdout encoding への依存を除去できる。stdout を UTF-8 に再設定する案もあるが、この通知では ASCII-only JSON の方が小さく移植性が高い。
- PostCompact 専用 subprocess テストを追加し、正常系と上記2条件を固定する。目視確認だけでは環境依存の失敗を継続検知できないため。

# 確定した事実と知識

- skill の Codex 補足ファイルは skill ルート直下ではなく `skills/using-superpowers/references/codex-tools.md` に配置されていた。参照元の相対パスが曖昧な場合は、skill パッケージ内で実体を限定検索してから読む。
