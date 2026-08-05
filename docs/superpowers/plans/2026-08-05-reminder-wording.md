# リマインダー文言の手順型改訂 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** PostToolUse リマインダーの注入文言を番号付き手順型(確認→なければ作成→追記→再開 + 統合時期の規定)へ改訂し、実機検証の知見を記憶へ統合する。

**Architecture:** `post_tool_use.py` の `REMINDER` 定数とテストのアサーションのみ変更(ロジック・閾値・発火条件は不変)。追従はドキュメント 3 箇所 + 記憶 2 ファイル。spec: `docs/superpowers/specs/2026-08-05-reminder-wording-design.md`。

**Tech Stack:** Python 3 標準ライブラリ + Markdown。

## Global Constraints

- ドキュメント・コメントは日本語
- ブランチ `fix/reminder-wording` 上で作業(main 直コミット禁止)
- hook のロジック・閾値・発火条件・hooks.json・AGENTS.md は変更しない
- コミットメッセージ末尾に `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` を付ける

---

### Task 1: REMINDER 文言とテストアサーションの更新

**Files:**
- Modify: `.codex/hooks/post_tool_use.py`(`REMINDER` 定数のみ)
- Modify: `tests/test_post_tool_use.py`(`reminder_emitted` のみ)

**Interfaces:**
- Consumes: なし
- Produces: 新文言(Task 2 のドキュメント・記憶がこの趣旨を記述する)

**注**: 本タスクは文言置換であり、旧文言も新アサーションの固定部分(「working-notes/ の担当ノート」)を含むため TDD の red が構成できない。代わりに Step 3 の手動実行で新文言の注入を直接確認する。

- [ ] **Step 1: REMINDER 定数を差し替える**

`.codex/hooks/post_tool_use.py` の `REMINDER` 定義を次の内容に置き換える(定数以外は変更しない):

```python
REMINDER = (
    "working-notes/ の担当ノートが 3 分以上更新されていません。次の手順を実行してください:\n"
    "1. 現在のタスク専用のノート `working-notes/<topic>.md` があるか確認し、なければ作成する(別タスクのノートを流用しない)\n"
    "2. そのノートに現在の状態と直近の判断・検証結果を追記する(数行)\n"
    "3. 中断していた作業を再開する\n"
    "\n"
    "docs/memory/ への統合はタスク完了時に行う。"
)
```

- [ ] **Step 2: テストのアサーションを固定部分一致へ更新する**

`tests/test_post_tool_use.py` の `reminder_emitted` を次の内容に置き換える:

```python
def reminder_emitted(proc: subprocess.CompletedProcess) -> bool:
    if not proc.stdout.strip():
        return False
    out = json.loads(proc.stdout)
    return "working-notes/ の担当ノート" in proc.stdout and "additionalContext" in proc.stdout and isinstance(out, dict)
```

- [ ] **Step 3: テストと手動実行で確認する**

Run: `python3 tests/test_post_tool_use.py && python3 tests/test_pre_compact.py`
Expected: 両方 `all tests passed`

Run: `printf '{"cwd":"%s"}' "$(mktemp -d)" | python3 .codex/hooks/post_tool_use.py`
Expected: 出力 JSON の `additionalContext` に新文言(「次の手順を実行してください」「1. 現在のタスク専用のノート」「docs/memory/ への統合はタスク完了時に行う。」)が含まれ、旧ラベル「リマインダー:」が含まれない。

- [ ] **Step 4: コミット**

```bash
git add .codex/hooks/post_tool_use.py tests/test_post_tool_use.py
git commit -m "fix: リマインダー文言を手順型へ改訂(確認→作成→追記→再開。語気表現を排除)"
```

---

### Task 2: ドキュメント追従と実機知見の記憶統合

**Files:**
- Modify: `docs/state-lifecycle.md`
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-08-05-rule-firing-reinforcement-design.md`
- Modify: `docs/memory/harness/e2e-verification.md`
- Modify: `docs/memory/harness/index.md`

**Interfaces:**
- Consumes: Task 1 の新文言の趣旨(ノートの確認・追記・作業再開を促す手順)
- Produces: なし(最終タスク)

- [ ] **Step 1: state-lifecycle §2 の説明を更新する**

old:

```markdown
ツール実行が続いたとき、記録と検索のルールを思い出させる短いリマインダーを
コンテキストへ注入します(再注入は 3 分のクールダウン付き。ノートを更新すれば
```

new:

```markdown
ツール実行が続いたとき、ノートの確認・数行の追記・作業再開を促す短い手順を
コンテキストへ注入します(再注入は 3 分のクールダウン付き。ノートを更新すれば
```

(old が完全一致しない場合は該当文を探して同趣旨に直し、報告に記載)

- [ ] **Step 2: README 仕組み表の説明を更新する**

old:

```markdown
| 平時(補強) | `post_tool_use.py` | ノートが 3 分更新されないままツール実行が続くと、記録・検索ルールの想起を注入する |
```

new:

```markdown
| 平時(補強) | `post_tool_use.py` | ノートが 3 分更新されないままツール実行が続くと、ノートの確認・追記・作業再開を促す手順を注入する |
```

- [ ] **Step 3: rule-firing spec に改訂参照を注記する**

`docs/superpowers/specs/2026-08-05-rule-firing-reinforcement-design.md` の決定事項テーブル「注入内容」行の決定セル末尾に次を追記する:

old: `| 注入内容 | 2 文の定型文(ノート更新と memory grep のルール想起)。ノートの中身は注入しない |`
new: `| 注入内容 | 2 文の定型文(ノート更新と memory grep のルール想起)。ノートの中身は注入しない(文言は[リマインダー文言の手順型改訂](2026-08-05-reminder-wording-design.md)で改訂) |`

- [ ] **Step 4: 実機知見を e2e-verification.md へ統合する**

`docs/memory/harness/e2e-verification.md` に次の変更を加える:

1. frontmatter: `description` を「単一セッション(フェーズ1)・複数セッション並行・記憶運用(docs/memory/)・リマインダー hook の実機検証で得た知見」に、`tags` に `post-tool-use` を追加、`generated.at` を実装時点の現在時刻(`date +%Y-%m-%dT%H:%M:%S%:z` の値)に更新(`generated.by: claude-code/fable-5` は維持)
2. 「## 記憶運用(docs/memory/)」サブセクションの後に次を追加:

   ```markdown
   ## リマインダー hook(PostToolUse)

   [発火保証の設計](../../superpowers/specs/2026-08-05-rule-firing-reinforcement-design.md)の検証方法 2 を実機(別環境・長時間タスク)で検証した。

   - 発火: ✅ matcher `*` で hook の発火・注入を確認した
   - 文言の副作用: ⚠️ 当初文言(記録 + memory grep の想起)は知識整理モードを誘発し、(a) 作業途中での中途半端なまとめ・統合の前倒し、(b) まとめ後に作業へ復帰しない、の 2 症状の恐れが観測された。また「追記を促す」だけではノート未作成・別タスクのノート使い回しに対応できない
   - 対応: 文言を番号付き手順型(確認 → なければ作成 → 追記 → 再開 + 統合時期の規定)へ改訂した([リマインダー文言の手順型改訂](../../superpowers/specs/2026-08-05-reminder-wording-design.md))。改訂後の行動変化は次回の長時間タスクで観察する
   ```

3. 「# 確定した事実と知識」セクションを末尾(「# 判断とその理由」の後)に新設し、次を追加:

   ```markdown
   # 確定した事実と知識

   - Codex は語気・含みのある言葉(「すぐ」等)に敏感で余計な推論をする。強調表現ではなく「これをしたら次はこれ」という番号付き手順型の指示のほうが精度が高い(実機観察で確認)。
   - 割り込み型のナッジ(リマインダー注入)には、作業範囲の限定(数行)と復帰指示を手順の構造として含める必要がある。指示がないとナッジ対応が自然な区切りに見え、作業へ復帰しない。
   ```

- [ ] **Step 5: harness/index.md の要約を更新する**

old:

```markdown
- [状態外部化ハーネスの E2E 検証](e2e-verification.md) — 単一セッション・複数セッション並行・記憶運用とも実機で確認済み
```

new:

```markdown
- [状態外部化ハーネスの E2E 検証](e2e-verification.md) — 単一セッション・複数セッション並行・記憶運用・リマインダー hook の発火とも実機で確認済み
```

- [ ] **Step 6: 全体検証を実行する**

```bash
python3 tests/test_post_tool_use.py && python3 tests/test_pre_compact.py
grep -n "記録・検索ルールの想起\|記録と検索のルールを思い出させる" README.md docs/state-lifecycle.md; echo "old-desc exit=$?"
grep -rn "リマインダー:" .codex/hooks/post_tool_use.py; echo "old-label exit=$?"
grep -c "確定した事実と知識" docs/memory/harness/e2e-verification.md
```

Expected: テスト両方 green、旧説明 0 件(exit=1)、旧ラベル 0 件(exit=1)、e2e-verification に新見出し 1 件。

- [ ] **Step 7: コミット**

```bash
git add docs/state-lifecycle.md README.md docs/superpowers/specs/2026-08-05-rule-firing-reinforcement-design.md docs/memory/
git commit -m "docs: リマインダー改訂を文書へ反映し、実機検証の知見を記憶へ統合"
```
