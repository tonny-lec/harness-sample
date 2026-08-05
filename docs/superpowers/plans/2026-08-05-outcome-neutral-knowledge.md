# 知識抽出の成否中立化 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 内容ガイドの「失敗から得た知識」を「確定した事実と知識(成否を問わず、不確実だったことが確定したら書く)」へ拡張し、現在系文書と既存記憶の見出しを揃える。

**Architecture:** 文書のみの変更。ルール(AGENTS.md)と書式ガイド(memory index)に新項目名と記録条件を置き、README / state-lifecycle の列挙と既存記憶 4 件の見出しを追従させる。hooks・tests・specs/plans(歴史文書)は不変。spec: `docs/superpowers/specs/2026-08-05-outcome-neutral-knowledge-design.md`。

**Tech Stack:** Markdown のみ。コードなし。

## Global Constraints

- ドキュメントは日本語
- ブランチ `feat/outcome-neutral-knowledge` 上で作業(main 直コミット禁止)
- specs / plans / hooks / tests は変更しない
- 既存記憶 4 件は見出し 1 行のみ変更(内容・frontmatter・`generated.at` は不変)
- コミットメッセージ末尾に `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` を付ける

---

### Task 1: ルール・書式ガイド・追従文書の改訂

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/memory/index.md`
- Modify: `README.md`
- Modify: `docs/state-lifecycle.md`

**Interfaces:**
- Consumes: なし
- Produces: 新項目名「確定した事実と知識」と記録条件の規定(Task 2 の記憶改名がこれに揃える)

- [ ] **Step 1: AGENTS.md の内容ガイドを差し替える**

次の置換を適用する(old は現行テキストと完全一致):

old:

```markdown
  行動ログではなく推論: 計画 / 仮説と検証結果(予想と合っていたか)/
  発見 / 判断とその理由(採らなかった案を含む)/ 失敗から得た知識。
```

new:

```markdown
  行動ログではなく推論: 計画 / 仮説と検証結果(予想と合っていたか)/
  発見 / 判断とその理由(採らなかった案を含む)/ 確定した事実と知識
  (不確実だったことが検証で確定したら、成功・失敗を問わず書く。
  自明な成功は書かない)。
```

- [ ] **Step 2: docs/memory/index.md の書式ブロックと説明文を更新する**

置換 1(書式 fence 内の見出し):

old: `# 失敗から得た知識`
new: `# 確定した事実と知識`

置換 2(fence 直後の説明段落の先頭):

old:

```markdown
空の見出しは削ってよい。`generated.by` の actor は、エージェントは
```

new:

```markdown
空の見出しは削ってよい。「確定した事実と知識」には、不確実だったことが検証で
確定した内容を成功・失敗を問わず書く(自明な成功は書かない)。
`generated.by` の actor は、エージェントは
```

- [ ] **Step 3: README.md の 2 箇所を更新する**

置換 1(手順 2 の箇条書き):

old:

```markdown
- コマンド・テスト・検証の結果を確認した直後に、その時点の推論(計画・仮説と
  検証結果・発見・判断とその理由・失敗から得た知識)を記録する
```

new:

```markdown
- コマンド・テスト・検証の結果を確認した直後に、その時点の推論(計画・仮説と
  検証結果・発見・判断とその理由・確定した事実と知識)を記録する
```

置換 2(制約節):

old:

```markdown
- 本ハーネスはモデルの private reasoning を保存するものではありません。後続判断に
  必要な計画、仮説、発見、判断理由、失敗から得た知識を明示的に外部化します。
```

new:

```markdown
- 本ハーネスはモデルの private reasoning を保存するものではありません。後続判断に
  必要な計画、仮説、発見、判断理由、確定した事実と知識を明示的に外部化します。
```

- [ ] **Step 4: docs/state-lifecycle.md の 2 箇所を更新する**

置換 1(2 節):

old:

```markdown
担当タスクのノートへ記録します。記録するのはコマンドの羅列ではなく、計画、仮説と
検証結果(予想と合っていたか)、発見、判断とその理由、失敗から得た知識です。
```

new:

```markdown
担当タスクのノートへ記録します。記録するのはコマンドの羅列ではなく、計画、仮説と
検証結果(予想と合っていたか)、発見、判断とその理由、確定した事実と知識です。
```

置換 2(5 節):

old:

```markdown
新設し、ルート `index.md` にカテゴリを追記します)。記録する項目は、計画、仮説と
検証結果、発見、判断とその理由、失敗から得た知識です。空の項目は省略できます。
```

new:

```markdown
新設し、ルート `index.md` にカテゴリを追記します)。記録する項目は、計画、仮説と
検証結果、発見、判断とその理由、確定した事実と知識です。空の項目は省略できます。
```

- [ ] **Step 5: 検証する**

Run: `grep -rn "失敗から得た知識" AGENTS.md README.md docs/state-lifecycle.md docs/memory/index.md; echo "exit=$?"`
Expected: 0 ヒット(exit=1)。

Run: `grep -c "確定した事実と知識" AGENTS.md README.md docs/state-lifecycle.md docs/memory/index.md`
Expected: AGENTS.md:1 / README.md:2 / docs/state-lifecycle.md:2 / docs/memory/index.md:2。

- [ ] **Step 6: コミット**

```bash
git add AGENTS.md docs/memory/index.md README.md docs/state-lifecycle.md
git commit -m "feat: 内容ガイドを「確定した事実と知識」へ拡張(成否を問わず確定したら書く)"
```

---

### Task 2: 既存記憶 4 件の見出し改名と全体検証

**Files:**
- Modify: `docs/memory/documentation/readme-authoring.md`
- Modify: `docs/memory/documentation/proofreading.md`
- Modify: `docs/memory/policy/superpowers-usage.md`
- Modify: `docs/memory/testing/post-compact-review.md`

**Interfaces:**
- Consumes: Task 1 の新項目名「確定した事実と知識」
- Produces: なし(最終タスク)

- [ ] **Step 1: 4 ファイルの見出しを改名する**

各ファイルで見出し行 `# 失敗から得た知識` を `# 確定した事実と知識` に置換する。
**見出し行以外(本文・frontmatter)は 1 文字も変えない**(`generated.at` も更新しない
— 見出し改名は知識の更新ではない)。

- [ ] **Step 2: 本文・frontmatter が不変であることを確認する**

Run: `git diff --stat && git diff`
Expected: 4 ファイルとも変更は見出し 1 行のみ(±1 行の対)。frontmatter に差分がない。

- [ ] **Step 3: 全体検証を実行する**

```bash
# (1) 旧見出しが現在系文書 + memory から消えた(specs/plans の歴史文書のみ残存)
grep -rn "失敗から得た知識" AGENTS.md README.md docs/state-lifecycle.md docs/memory/; echo "exit=$?"
# (2) 新項目名の分布
grep -rc "確定した事実と知識" AGENTS.md README.md docs/state-lifecycle.md docs/memory/index.md docs/memory/documentation/readme-authoring.md docs/memory/documentation/proofreading.md docs/memory/policy/superpowers-usage.md docs/memory/testing/post-compact-review.md
# (3) hooks / tests 無変更の確認
python3 tests/test_post_tool_use.py && python3 tests/test_pre_compact.py
```

Expected: (1) 0 ヒット(exit=1)。(2) AGENTS.md:1 / README.md:2 / state-lifecycle:2 / index:2 / 記憶 4 件は各 1。(3) 両方 `all tests passed`。

- [ ] **Step 4: コミット**

```bash
git add docs/memory/
git commit -m "refactor: 既存記憶 4 件の見出しを「確定した事実と知識」へ一括改名(内容不変)"
```
