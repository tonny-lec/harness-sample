---
type: Memory
title: リポジトリ文書の校閲
description: README と state-lifecycle.md の誤字脱字確認で得た手法と結果
tags: [documentation, proofreading, readme, state-lifecycle]
generated: { by: codex/gpt-5, at: 2026-08-04T16:17:05+09:00 }
---

# 仮説と検証結果

- README(2026-08-04 16:17 JST 時点): 現行の全 181 行を通読して確認し、明確な誤字・脱字は 0 件だった。「起きえます」(168 行目)は「起き得ます」と同義で誤字と断定できず、「設計 spec 参照」(166 行目)も表記上の選択であり脱字と断定できない境界事例として区別した。
- `docs/state-lifecycle.md`(同時点): 節単位で前半・後半に分けて確認し、誤字・脱字・表記ゆれは 0 件だった。

# 発見

- README: 誤字・脱字として報告すべき箇所は 0 件だった。表記や文体の改善候補は存在しうるが、今回の依頼範囲(客観的な誤字脱字)とは区別する必要がある。

# 判断とその理由

- state-lifecycle.md: 「ノート」と「担当タスクのノート」は併存するが、文脈上の使い分けであり表記ゆれではないと判断した。
- state-lifecycle.md: 全文を一括確認する案ではなく、節単位で先頭から順に確認する方針を採用した。中断・再開時に確認済み範囲を明示でき、重複確認や確認漏れを防げるため。前半は「全体像」から「3. compaction 前に生ログを退避する」まで、後半は「4. compaction 後はノートから作業を継続する」から「障害時の復元順序」までと区切って進捗を記録した。修正対象がなかったため、`docs/state-lifecycle.md` 自体は変更しなかった。
- README: 誤字・脱字の報告に限定し、任意の表記統一や文章改善は指摘件数へ含めない。依頼範囲を広げず、客観的に誤りといえる箇所だけを報告するため。

# 失敗から得た知識

- `using-superpowers` の本文が示す `skills/references/codex-tools.md` は実配置と一致せず、実ファイルは `skills/using-superpowers/references/codex-tools.md` にあった。参照ファイルが見つからない場合は、スキル配下をファイル名で検索して実配置を確認する。
