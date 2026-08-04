# worklog の記憶化(docs/memory/ バンドル再編)実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `docs/worklog/`(日付付きフラット構成)を `docs/memory/`(カテゴリ別・日付なし・更新統合型の OKF v0.2 バンドル)へ再編し、AGENTS.md に記憶の検索・統合ルールを規定する。

**Architecture:** 既存 8 エントリを 4 カテゴリ 6 記憶へ移行(1:1 が 4 件、統合が 2 組)。1:1 は `git mv` + frontmatter 変換のみで本文不変。統合 2 件だけ知見の再構成を行い、消失なしを突き合わせで検証する。hooks・tests は無変更。spec: `docs/superpowers/specs/2026-08-04-memory-bundle-design.md`。

**Tech Stack:** Markdown + YAML frontmatter(OKF v0.2)のみ。コードなし。

## Global Constraints

- ドキュメントは日本語
- ブランチ `feat/memory-bundle-design` 上で作業(main 直コミット禁止)
- hooks(`.codex/`)と tests は変更しない
- frontmatter: `type: Memory` 必須。`timestamp` + `actor` は使わず `generated: { by: <actor>, at: <ISO 8601> }` に一本化
- 記憶のパスは `docs/memory/<category>/<topic>.md`(日付なし・短いケバブケース)
- 過去の spec / plan / 記憶本文中の `docs/worklog/` 参照は書き換えない(リンク切れ許容)
- コミットメッセージ末尾に `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` を付ける

---

### Task 1: 1:1 移行 4 件(git mv + frontmatter 変換)

**Files:**
- Move: `docs/worklog/2026-08-02-readme-draft.md` → `docs/memory/documentation/readme-authoring.md`
- Move: `docs/worklog/2026-08-02-state-lifecycle-guide.md` → `docs/memory/documentation/explanatory-guides.md`
- Move: `docs/worklog/2026-08-04-pre-compact-test-coverage.md` → `docs/memory/testing/pre-compact-coverage.md`
- Move: `docs/worklog/2026-08-02-disable-superpowers-for-repo.md` → `docs/memory/policy/superpowers-usage.md`

**Interfaces:**
- Consumes: なし
- Produces: 上記 4 パスの記憶ファイル(Task 3 の index がこれらを列挙する)

- [ ] **Step 1: git mv で 4 ファイルを移動する**

```bash
mkdir -p docs/memory/documentation docs/memory/testing docs/memory/policy
git mv docs/worklog/2026-08-02-readme-draft.md docs/memory/documentation/readme-authoring.md
git mv docs/worklog/2026-08-02-state-lifecycle-guide.md docs/memory/documentation/explanatory-guides.md
git mv docs/worklog/2026-08-04-pre-compact-test-coverage.md docs/memory/testing/pre-compact-coverage.md
git mv docs/worklog/2026-08-02-disable-superpowers-for-repo.md docs/memory/policy/superpowers-usage.md
```

- [ ] **Step 2: 4 ファイルの frontmatter を変換する(本文は 1 文字も変えない)**

各ファイルの frontmatter ブロック(`---` から `---` まで)を次のとおり置き換える。
`type` を `Memory` に、`timestamp` + `actor` の 2 行を `generated` 1 行にする変換で、
`title` / `description` / `tags` は元の値をそのまま維持する。

`docs/memory/documentation/readme-authoring.md`:

```yaml
---
type: Memory
title: 導入者向け README 草案
description: 構成2案を比較し、導入ファースト構成で現行実装に沿う README を作成した。
tags: [readme, documentation, codex-hooks, state-externalization]
generated: { by: openai/codex, at: 2026-08-02T00:00:00+09:00 }
---
```

`docs/memory/documentation/explanatory-guides.md`:

```yaml
---
type: Memory
title: 状態保存・復元ライフサイクルの解説
description: 起動から完了までの処理フローを実装に沿って説明する独立文書を作成した。
tags: [documentation, codex-hooks, state-externalization, lifecycle]
generated: { by: openai/codex, at: 2026-08-02T00:00:00+09:00 }
---
```

`docs/memory/testing/pre-compact-coverage.md`:

```yaml
---
type: Memory
title: PreCompact テストケースの網羅性分析
description: 実装と仕様に対する正常系・分岐・異常系のテスト網羅性を評価した。
tags: [testing, codex-hooks, pre-compact, coverage]
generated: { by: openai/codex, at: 2026-08-04T00:00:00+09:00 }
---
```

`docs/memory/policy/superpowers-usage.md`:

```yaml
---
type: Memory
title: リポジトリ限定の superpowers 不使用方針
description: 個別プラグイン状態のスコープを確認し、AGENTS.md による利用禁止を推奨した。
tags: [codex, plugins, superpowers, configuration]
generated: { by: codex/gpt-5, at: 2026-08-02T23:23:43+09:00 }
---
```

- [ ] **Step 3: 本文が不変であることを確認する**

Run: `git diff --cached -M --stat && git diff -M`
Expected: 4 件が rename として検出され、diff は各ファイルの frontmatter 行(type/timestamp/actor → type/generated)のみ。本文見出し・箇条書きに変更がないこと。

- [ ] **Step 4: コミット**

```bash
git add docs/memory docs/worklog
git commit -m "refactor: worklog 4 件を docs/memory/ へ 1:1 移行(日付なし・OKF v0.2 frontmatter)"
```

---

### Task 2: 統合記憶 2 件の作成(知見の再構成)

**Files:**
- Create: `docs/memory/harness/e2e-verification.md`(← `docs/worklog/2026-08-02-phase1-e2e.md` + `docs/worklog/2026-08-04-multi-session-e2e.md`)
- Create: `docs/memory/documentation/proofreading.md`(← `docs/worklog/2026-08-04-readme-typo-check.md` + `docs/worklog/2026-08-04-state-lifecycle-typos.md`)
- Delete: 上記 4 つの移行元(`git rm`)

**Interfaces:**
- Consumes: なし
- Produces: 上記 2 パスの記憶ファイル(Task 3 の index がこれらを列挙する)

- [ ] **Step 1: 移行元 4 件を読む**

`docs/worklog/` の上記 4 ファイルを全文読み、含まれる知見(計画 / 仮説と検証結果 / 発見 / 判断とその理由 / 失敗から得た知識 の各項目)を列挙する。

- [ ] **Step 2: harness/e2e-verification.md を作成する**

frontmatter は次のとおり(`generated` は新しい方の元エントリに合わせる):

```yaml
---
type: Memory
title: 状態外部化ハーネスの E2E 検証
description: 単一セッション(フェーズ1)と複数セッション並行の実機検証で得た知見
tags: [harness, e2e, codex-hooks, multi-session]
generated: { by: claude-code/fable-5, at: 2026-08-04T00:00:00Z }
---
```

本文の構成要件(時系列の連結ではなく知見単位で再構成する):

- `# 仮説と検証結果` — サブ見出し `## フェーズ1(単一セッション)` に phase1 の (a)〜(e) の結果((e) の再検証経緯を含む)、`## 複数セッション対応` に起動確認・(a) 並行分離・(b) 完了時分離・(c) 再開・gitignore の結果を置く
- `# 発見` — 両エントリの発見をすべて含める: (1) cwd を移動させるスキルとの併用でパス解決が壊れる、(2) 平時ルールと完了時ルールの優先関係が不明瞭だと完了処理が欠ける、(3) 小タスクは 1 プロンプトで完了するため再開検証には人工的な途中ノートが必要
- `# 判断とその理由` — 両エントリの判断をすべて含める: 完了時ルールの優先を明記して解消した判断(hook による自動削除を採らなかった理由を含む)、(c) を人工ノートで検証した判断とその等価性の理由
- 重複する記述は 1 回にまとめ、相反はない(両エントリは別フェーズの検証)ため両方残す

- [ ] **Step 3: documentation/proofreading.md を作成する**

frontmatter(`generated` は新しい方の元エントリに合わせる):

```yaml
---
type: Memory
title: リポジトリ文書の校閲
description: README と state-lifecycle.md の誤字脱字確認で得た手法と結果
tags: [documentation, proofreading, readme, state-lifecycle]
generated: { by: codex/gpt-5, at: 2026-08-04T13:57:19+09:00 }
---
```

本文の構成要件:

- `# 仮説と検証結果` — 対象ごとの結果を 1 行ずつ: README(2026-08-04 時点)は明確な誤字・脱字 0 件、state-lifecycle.md(同)は誤字・脱字・表記ゆれ 0 件
- `# 発見` / `# 判断とその理由` — 元 2 エントリに含まれる手法・判断(例: 節単位で先頭から順にチェックする方針とその理由、「ノート」と「担当タスクのノート」は使い分けであり表記ゆれではないという判断)をすべて残す
- 元エントリに存在しない項目(失敗から得た知識など)は作らない

- [ ] **Step 4: 移行元 4 件を削除する**

```bash
git rm docs/worklog/2026-08-02-phase1-e2e.md docs/worklog/2026-08-04-multi-session-e2e.md docs/worklog/2026-08-04-readme-typo-check.md docs/worklog/2026-08-04-state-lifecycle-typos.md
```

- [ ] **Step 5: 知見消失なしを突き合わせる**

`git show HEAD:docs/worklog/<元ファイル>` などで削除前の全項目一覧(Step 1)と新 2 ファイルを突き合わせ、元 4 件の「発見・判断とその理由・失敗から得た知識」の各項目が新記憶に存在することを 1 項目ずつ確認し、結果(項目数と対応)を報告に記載する。欠落があれば追記する。

- [ ] **Step 6: コミット**

```bash
git add docs/memory docs/worklog
git commit -m "refactor: E2E 検証と校閲の知見を統合記憶へ再構成(同トピック 1 ファイル原則)"
```

---

### Task 3: index 階層の作成と docs/worklog/ の削除

**Files:**
- Create: `docs/memory/index.md`、`docs/memory/harness/index.md`、`docs/memory/documentation/index.md`、`docs/memory/testing/index.md`、`docs/memory/policy/index.md`
- Delete: `docs/worklog/index.md`(これで `docs/worklog/` が消滅)

**Interfaces:**
- Consumes: Task 1・2 が作った 6 記憶のパスとタイトル
- Produces: 段階的開示の入口 `docs/memory/index.md`(Task 4 のドキュメントがこのパスを参照する)

- [ ] **Step 1: ルート index.md を作成する**

`docs/memory/index.md` を次の内容で作成:

````markdown
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
````

- [ ] **Step 2: カテゴリ index 4 件を作成する**

`docs/memory/harness/index.md`:

```markdown
---
type: Index
title: harness
description: ハーネス自体の挙動・検証の知見
---

# harness

- [状態外部化ハーネスの E2E 検証](e2e-verification.md) — 単一セッション・複数セッション並行とも実機で確認済み
```

`docs/memory/documentation/index.md`:

```markdown
---
type: Index
title: documentation
description: 文書の作成・校閲の知見
---

# documentation

- [導入者向け README 草案](readme-authoring.md) — 構成2案を比較し、導入ファースト構成を採用
- [状態保存・復元ライフサイクルの解説](explanatory-guides.md) — 処理フローを実装に沿って説明する独立文書の作成知見
- [リポジトリ文書の校閲](proofreading.md) — README・state-lifecycle.md とも明確な誤字脱字 0 件
```

`docs/memory/testing/index.md`:

```markdown
---
type: Index
title: testing
description: テスト設計・網羅性の知見
---

# testing

- [PreCompact テストケースの網羅性分析](pre-compact-coverage.md) — 実行経路は高網羅、仕様アサーションと堅牢性は中程度
```

`docs/memory/policy/index.md`:

```markdown
---
type: Index
title: policy
description: リポジトリ運用方針
---

# policy

- [リポジトリ限定の superpowers 不使用方針](superpowers-usage.md) — AGENTS.md による利用禁止を推奨
```

- [ ] **Step 3: 旧 index を削除し、worklog が消滅したことを確認する**

```bash
git rm docs/worklog/index.md
ls docs/worklog/ 2>&1 || echo "worklog removed"
```

Expected: `docs/worklog/` ディレクトリが存在しない。

- [ ] **Step 4: index から全記憶が辿れることを確認する**

ルート index に列挙された 4 カテゴリ index が存在し、カテゴリ index に列挙された 6 ファイルがすべて存在することを確認する:

```bash
for f in index.md harness/index.md harness/e2e-verification.md documentation/index.md documentation/readme-authoring.md documentation/explanatory-guides.md documentation/proofreading.md testing/index.md testing/pre-compact-coverage.md policy/index.md policy/superpowers-usage.md; do test -f "docs/memory/$f" && echo "OK $f" || echo "MISSING $f"; done
```

Expected: 全行 OK。

- [ ] **Step 5: コミット**

```bash
git add docs/memory docs/worklog
git commit -m "feat: docs/memory/ の段階的開示 index を整備し docs/worklog/ を廃止"
```

---

### Task 4: ルールとドキュメントの追従・全体検証

**Files:**
- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `docs/state-lifecycle.md`

**Interfaces:**
- Consumes: `docs/memory/index.md`(Task 3)、記憶パス規約 `docs/memory/<category>/<topic>.md`
- Produces: なし(最終タスク)

- [ ] **Step 1: AGENTS.md を書き換える**

`AGENTS.md` 全体を次の内容に置き換える(検索ルールの新設、完了時ルールの統合型への改訂、`<topic>` 注記から worklog 言及を除去。それ以外の箇条書きは従来どおり):

```markdown
# AGENTS.md

## 推論の外部化

- タスク開始時に `working-notes/` を確認する。担当タスクのノート
  `working-notes/<topic>.md` があればそれを読んで再開し、なければ作成する
  (`<topic>` は短いケバブケース)。
  他タスクのノートは読んでよいが、編集しない。
- タスク開始時に `docs/memory/index.md` で関連カテゴリを確認する。作業中に
  技術判断・予想外の結果・未知の領域に直面したら、着手前に `docs/memory/` を
  grep(tags / title / description / 見出し)して関連する記憶を読む。
- 次のいずれかが起きたら、その時点で担当タスクのノートに記録する。
  タスクの大小を問わない:
  - 複数の選択肢から選んだ 1 つとその理由(採らなかった案とそれぞれの理由を記載)
  - 仮説を立てた、または検証して結果が出た
  - 予想と異なる結果・エラーに遭遇した
  - 外部調査(ドキュメント・Web・コード読解)で事実を確認した
  - 計画・方針を変更した
- 記録するのは行動ログではなく推論: 計画 / 仮説と検証結果 / 発見 / 判断とその理由 / 失敗から得た知識。
- ノートは二部構成を保つ: 冒頭の「現在の状態と次の一手」は常に上書きして簡潔に
  最新化する(次の判断に必要な状態)。それ以降の推論の記録は追記する。
- 作業再開時・compaction 後は、続きを始める前に担当タスクのノートを読む。
- タスク完了時、担当タスクのノートの知見を `docs/memory/` の記憶へ統合する:
  同トピックの記憶があれば既存ファイルを更新して `generated.at` を最新化し、
  なければカテゴリを選んで `docs/memory/<category>/<topic>.md` を新規作成する
  (合うカテゴリがなければ新設し、ルート `index.md` にカテゴリを追記する)。
  該当カテゴリの `index.md` を更新し、ノートファイルを削除する。
  完了時はこの手順が「追記する」ルールより優先される。
```

- [ ] **Step 2: README.md を追従させる**

以下の置換をすべて適用する(前後の文はファイル内の現行表記に合わせる。見つからない場合は類似表現を探して同趣旨に直す):

1. 冒頭段落: 「完了したタスクの知識を `docs/worklog/` に残します」→「完了したタスクの知識をカテゴリ別の `docs/memory/` の記憶に統合します」
2. 対応状況表の E2E 行: 「単一セッション運用(docs/worklog/2026-08-02-phase1-e2e.md)・複数セッション並行(docs/worklog/2026-08-04-multi-session-e2e.md)とも完了」→「単一セッション運用・複数セッション並行とも完了(docs/memory/harness/e2e-verification.md)」
3. 導入ファイル構成の tree: `worklog/` と `index.md` の 2 行 →

   ```text
   └── docs/
       └── memory/
           └── index.md
   ```

4. 手順 2 の「このルールが次を担当します」の箇条書き: 「タスク完了時に記録を `docs/worklog/` へ移す」→「タスク完了時に知見を `docs/memory/` の記憶へ統合する(同トピックがあれば更新)」。さらに箇条書きの先頭に「タスク開始時・技術判断の前に `docs/memory/` から関連する記憶を検索して読む」を追加
5. 手順 3 の説明: 「完了後に残す知識は `docs/worklog/` へ移して Git 管理します」→「完了後に残す知識は `docs/memory/` の記憶へ統合して Git 管理します」
6. 手順 4 全体を差し替え:

   ```markdown
   ### 4. memory を初期化する

   導入先に `docs/memory/index.md` を作り、このリポジトリの
   [memory index](docs/memory/index.md) にあるカテゴリ一覧と記憶の書式を使います。
   このサンプル固有のカテゴリと記憶はコピーせず、導入先で生まれた記憶だけを
   配置してください。
   ```

7. 普段の使い方 6: 「タスク完了時には、担当ノートを `docs/worklog/YYYY-MM-DD-<topic>.md` へ移し、index に追加します」→「タスク完了時には、担当ノートの知見を `docs/memory/<category>/<topic>.md` の記憶へ統合し(同トピックがあれば更新)、該当する index を更新します」
8. 仕組み表の「タスク完了後」行: 「`docs/worklog/` | 蒸留した推論を OKF 形式の Markdown として保持する」→「`docs/memory/` | 蒸留した推論をカテゴリ別の記憶として統合・保持する(OKF 形式)」
9. 仕組み表直後の段落: 「通常の復元には担当タスクのノートと worklog を使い」→「通常の復元には担当タスクのノートと記憶(`docs/memory/`)を使い」
10. 詳細資料: 「[worklog index](docs/worklog/index.md)」→「[memory index](docs/memory/index.md)」に置換し、一覧に「[worklog の記憶化の設計](docs/superpowers/specs/2026-08-04-memory-bundle-design.md)」を追加

- [ ] **Step 3: docs/state-lifecycle.md を追従させる**

以下の置換をすべて適用する:

1. 冒頭の設計参照文に「[worklog の記憶化の設計](superpowers/specs/2026-08-04-memory-bundle-design.md)」を追加
2. 全体像の表: 「`docs/worklog/` | 完了したタスクから得た知識を恒久的に保持する」→「`docs/memory/` | 完了したタスクから得た知識をカテゴリ別の記憶として保持する」
3. フロー図の末尾: 「docs/worklog/ に保存(ノートは削除)」→「docs/memory/ に統合(ノートは削除)」
4. 1 節: 「`<topic>` は完了時の worklog `YYYY-MM-DD-<topic>.md` と同じ短いケバブケースの語で、」→「`<topic>` は短いケバブケースの語で、」
5. 3 節: 「まず担当タスクのノート、次に `docs/worklog/` を参照し」→「まず担当タスクのノート、次に `docs/memory/` を参照し」
6. 5 節全体を差し替え:

   ```markdown
   ## 5. タスク完了時に一時状態を記憶へ統合する

   タスクが完了したら、担当タスクのノートの知見を `docs/memory/` の記憶へ統合します。
   まず同トピックの記憶を検索し、あれば既存ファイルを更新して frontmatter の
   `generated.at` を最新化します。なければカテゴリを選んで
   `docs/memory/<category>/<topic>.md` を新規作成します(合うカテゴリがなければ
   新設し、ルート `index.md` にカテゴリを追記します)。記録する項目は、計画、仮説と
   検証結果、発見、判断とその理由、失敗から得た知識です。空の項目は省略できます。

   同時に該当カテゴリの `index.md` を更新し、`working-notes/<topic>.md` を削除します。
   後続タスクはルート index からカテゴリを辿るか、`docs/memory/` を grep して関連する
   記憶だけを読むため、AGENTS.md や起動時コンテキストを過去の知識で肥大化させずに
   済みます。

   この時点で、進行中の状態だった情報は次のタスクでも参照できる記憶になります。
   同じトピックに再び取り組めば、記憶は別ファイルに分散せず 1 ファイルの中で
   更新されていきます(経緯は git 履歴が残します)。他のセッションが進行中の
   タスクのノートは `working-notes/` に残ったままであり、影響を受けません。
   ```

7. 障害時の復元順序: 「3. `docs/worklog/index.md` から辿れる関連タスク」→「3. `docs/memory/index.md` から辿れる関連する記憶(または `docs/memory/` の grep)」

- [ ] **Step 4: 全体検証を実行する**

```bash
# (1) 参照の整合: 現在を記述する 3 文書に docs/worklog が残っていない
grep -rn "docs/worklog" AGENTS.md README.md docs/state-lifecycle.md; echo "exit=$?"
# (2) 検索の実例
grep -rln "e2e" docs/memory/
grep -rln "compaction" docs/memory/
# (3) hooks 無変更の確認
python3 tests/test_pre_compact.py
python3 -m json.tool .codex/hooks.json >/dev/null && echo "JSON OK"
```

Expected: (1) は 0 ヒット(exit=1)。(2) は `harness/e2e-verification.md`(および tags に e2e を含む index)がヒットし、compaction では `harness/e2e-verification.md` と `testing/pre-compact-coverage.md` を含む。(3) は `all tests passed` と `JSON OK`。

- [ ] **Step 5: コミット**

```bash
git add AGENTS.md README.md docs/state-lifecycle.md
git commit -m "docs: 記憶の検索・統合ルールを規定し README / state-lifecycle を memory 構成へ追従"
```
