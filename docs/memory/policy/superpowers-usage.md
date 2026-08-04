---
type: Memory
title: リポジトリ限定の superpowers 不使用方針
description: 個別プラグイン状態のスコープを確認し、AGENTS.md による利用禁止を推奨した。
tags: [codex, plugins, superpowers, configuration]
generated: { by: codex/gpt-5, at: 2026-08-02T23:23:43+09:00 }
---

# 計画

Codex CLI 0.146.0 の公式マニュアル、実機のプラグイン状態、公式ソースを確認し、superpowers だけをこのリポジトリで使わない方法と影響範囲を分ける。

# 仮説と検証結果

- 仮説: project-scoped `.codex/config.toml` で superpowers 個別の `enabled` を上書きできる。
- 結果: 一般設定は trusted project の `.codex/config.toml` がユーザー設定より優先されるが、公式ソースは `plugins` を user-level entries と明記する。実機でも `-c 'plugins."superpowers@openai-curated".enabled=false'` は `codex plugin list --json` の enabled 状態を変えなかったため、個別状態の project-scoped 上書きは採用しない。
- 結果: `codex -c features.plugins=false features list` は `plugins stable false` を返した。project-scoped `.codex/config.toml` で同じ feature を無効化すれば、このリポジトリだけ全プラグインを停止できる。

# 発見

- 実機の `superpowers@openai-curated` は installed, enabled。個別状態は `~/.codex/config.toml` の `[plugins."superpowers@openai-curated"] enabled = true` に保持されている。
- 公式マニュアルは、プラグイン状態変更後に新規セッションを開始するよう説明している。
- `superpowers:using-superpowers` はユーザーの直接指示や `AGENTS.md` がスキルより優先すると定めている。このため repo-local `AGENTS.md` に不使用を明記する方法なら、他プラグインを維持したまま目的を満たせる。

# 判断とその理由

- 推奨: repo-local `AGENTS.md` に、このリポジトリでは superpowers プラグイン由来のスキルを使用しない、と明記する。対象を superpowers だけに限定でき、他プラグインを止めないため。
- 採らなかった案: グローバルの個別プラグイン状態を無効にする。全リポジトリへ影響するため。
- 代替案: `.codex/config.toml` に `[features] plugins = false` を置く。確実に repo-local だが、superpowers 以外も停止するため要件より広い。

# 失敗から得た知識

- Markdown のバッククォートを含む検索式は二重引用符内でシェルに渡さない。発生した生エラーは `/tmp/harness-sample-plugin-search-error.txt` に保存した。
- `codex plugin` は `--strict-config` 非対応。生エラーは `/tmp/harness-sample-plugin-strict-config-error.txt` に保存した。
- `codex debug prompt-input` はこの実行環境で read-only filesystem エラーとなり、sandbox 外でも再現した。生エラーは `/tmp/harness-sample-prompt-input-sandbox-error.txt` に保存し、公式ソースと CLI の設定上書き結果で判断した。
