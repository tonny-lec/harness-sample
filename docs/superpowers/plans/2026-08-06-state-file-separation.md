# 状態ファイル分離 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 「現在の状態と次の一手」を `working-notes/<topic>.state.md` へ分離し、ノート `working-notes/<topic>.md` を推論の記録(追記型)に純化する。

**Architecture:** hooks のロジックは一切変更せず、文字列定数(REMINDER / systemMessage / docstring)と AGENTS.md のルール文面、追従ドキュメントのみを変更する。仕様の出典は [設計 spec](../specs/2026-08-06-state-file-separation-design.md)。文面はすべて spec からの転記であり、実装者が創作しない。

**Tech Stack:** Python 3(標準ライブラリのみ)、Markdown。テストは `python3 tests/test_post_tool_use.py` / `python3 tests/test_pre_compact.py` で実行(pytest 不使用)。

## Global Constraints

- ブランチ `fix/note-maintenance-model` 上で作業する(作成済み。main へ直接コミットしない)。
- hooks のロジック(閾値・クールダウン・発火条件・matcher・glob)を変更しない。変更してよいのは文字列定数と docstring のみ。
- `pre_compact.py` / `.gitignore` / `docs/memory/` 配下は変更しない。
- ドキュメントの文面は本計画に書かれたものをそのまま使う(spec からの転記)。
- コミットメッセージは既存の流儀(`fix:` / `docs:` + 日本語要約)に従う。

---

### Task 1: post_tool_use.py の文言差し替えとテスト更新(TDD)

**Files:**
- Modify: `tests/test_post_tool_use.py`
- Modify: `.codex/hooks/post_tool_use.py`

**Interfaces:**
- Consumes: 既存の `run_hook(cwd, raw)` / `make_note(cwd, age_seconds)` ヘルパー(同ファイル内)
- Produces: `make_state(cwd, age_seconds)` ヘルパーと新 `REMINDER` 文言(後続タスクは使わない。テストと hook で完結)

- [ ] **Step 1: テストを新文言前提に書き換える(失敗するテストを先に作る)**

`tests/test_post_tool_use.py` に次の変更を加える。

(a) `reminder_emitted` の固定部分一致を新文言へ更新:

```python
def reminder_emitted(proc: subprocess.CompletedProcess) -> bool:
    if not proc.stdout.strip():
        return False
    out = json.loads(proc.stdout)
    return (
        "working-notes/ の担当タスクのファイル" in proc.stdout
        and "次の手順を実行してください" in proc.stdout
        and "上書きで最新化" in proc.stdout
        and "additionalContext" in proc.stdout
        and isinstance(out, dict)
    )
```

(b) `make_note` のフィクスチャ内容を推論の記録(旧二部構成の見出しなし)へ変更:

```python
    note.write_text("- 仮説: サンプル\n", encoding="utf-8")
```

(c) `make_note` の直後に `make_state` ヘルパーを追加:

```python
def make_state(cwd: Path, age_seconds: float = 0.0) -> Path:
    notes = cwd / "working-notes"
    notes.mkdir(exist_ok=True)
    state = notes / "sample-task.state.md"
    state.write_text(
        "- 目的: サンプル\n- 状態: 作業中\n- 決定: なし\n- 次の一手: 検証\n",
        encoding="utf-8",
    )
    if age_seconds:
        old = time.time() - age_seconds
        os.utime(state, (old, old))
    return state
```

(d) 状態ファイルだけが新鮮なら沈黙するテストを追加(`test_fresh_note_silent` の直後):

```python
def test_fresh_state_file_silent() -> None:
    # 状態ファイルの上書きだけでも鮮度判定が更新される(glob("*.md") が .state.md を拾う)
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        make_note(cwd, age_seconds=600)
        make_state(cwd)  # 状態ファイルだけ新鮮
        proc = run_hook(cwd)
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip() == "", proc.stdout
```

- [ ] **Step 2: テストを実行して失敗を確認する**

Run: `python3 tests/test_post_tool_use.py`
Expected: `test_expired_stamp_reminds_and_touches` で AssertionError(テストはアルファベット順に実行され、これが最初のリマインド系テスト。旧 REMINDER に「担当タスクのファイル」「上書きで最新化」が含まれないため `reminder_emitted` が False)。
補足: `test_fresh_state_file_silent` は現行実装でも通る(glob は既に `.state.md` にマッチする)。これは退行防止の固定化であり、失敗しないことは想定どおり。

- [ ] **Step 3: post_tool_use.py の REMINDER と docstring を差し替える**

`REMINDER` 定数を次に置き換える:

```python
REMINDER = (
    "working-notes/ の担当タスクのファイルが 3 分以上更新されていません。次の手順を実行してください:\n"
    "1. 現在のタスク専用の状態ファイル `working-notes/<topic>.state.md` とノート `working-notes/<topic>.md` があるか確認し、なければ作成する(別タスクのファイルを流用しない)\n"
    "2. 状態ファイル(目的 / 状態 / 決定 / 次の一手)を上書きで最新化し、直近の判断・検証結果をノートに追記する(数行)\n"
    "3. 中断していた作業を再開する\n"
    "\n"
    "docs/memory/ への統合はタスク完了時に行う。"
)
```

docstring の 1 行目を次に置き換える(2 行目以降は変更しない):

```python
"""Codex PostToolUse hook: 担当タスクのファイルが古いままのとき、確認・状態の上書きとノートへの追記・作業再開を促す手順を注入する。
```

- [ ] **Step 4: テストを実行して全件通ることを確認する**

Run: `python3 tests/test_post_tool_use.py`
Expected: `PASS test_cooldown_suppresses` 〜 `PASS test_stale_note_reminds` の全 7 件(追加分含む)+ `all tests passed`

- [ ] **Step 5: 手動で hook を実行し注入 JSON を目視確認する**

Run: `cd "$(mktemp -d)" && printf '{"cwd":"."}' | python3 /home/tonny/workspace/harness-sample/.codex/hooks/post_tool_use.py`
Expected: `additionalContext` に新文言(1 行目「担当タスクのファイル」、手順 2「上書きで最新化」)が入った JSON が 1 行出力される。

- [ ] **Step 6: コミット**

```bash
git add tests/test_post_tool_use.py .codex/hooks/post_tool_use.py
git commit -m "fix: リマインダーを状態ファイル分離の 2 ファイル構成へ改訂(状態は上書き・ノートは追記)"
```

---

### Task 2: post_compact.py の通知文言の字句追従

**Files:**
- Modify: `.codex/hooks/post_compact.py:14`

**Interfaces:**
- Consumes: なし
- Produces: なし(文言のみ)

- [ ] **Step 1: systemMessage を差し替える**

`post_compact.py` の `systemMessage` の値を次に置き換える:

```python
        "systemMessage": "compaction が実行されました。エージェントは担当タスクの状態ファイル(working-notes/<topic>.state.md)を読み直して状態を確認します。"
```

- [ ] **Step 2: 手動実行で出力を確認する**

Run: `printf '{}' | python3 .codex/hooks/post_compact.py`
Expected: `{"systemMessage": "compaction が実行されました。エージェントは担当タスクの状態ファイル(working-notes/<topic>.state.md)を読み直して状態を確認します。"}` が出力され、終了コード 0。

- [ ] **Step 3: 既存テストが影響を受けていないことを確認する**

Run: `python3 tests/test_pre_compact.py && python3 tests/test_post_tool_use.py`
Expected: 両方とも all tests passed

- [ ] **Step 4: コミット**

```bash
git add .codex/hooks/post_compact.py
git commit -m "fix: PostCompact 通知の再読対象を状態ファイルへ追従"
```

---

### Task 3: AGENTS.md の「推論の外部化」セクション置換

**Files:**
- Modify: `AGENTS.md`(ファイル全体が対象セクション)

**Interfaces:**
- Consumes: なし
- Produces: 後続タスク(README / state-lifecycle)が要約・参照する正となるルール文面

- [ ] **Step 1: セクションを置換する**

`AGENTS.md` の `## 推論の外部化` 以下すべて(現状はファイル末尾まで)を、次に置き換える:

~~~markdown
## 推論の外部化

作業状態は会話履歴ではなくファイルに置く。compaction やセッションの中断で会話が
失われても、ファイルから同じ地点へ復帰するためである。タスクごとに次の 2 ファイルを
`working-notes/` に置く(`<topic>` は短いケバブケース):

- **状態ファイル** `working-notes/<topic>.state.md` — 進行の要約。目的 / 状態 /
  決定 / 次の一手 の箇条書きだけを常に上書きで簡潔に保ち、履歴は持たせない
  (維持するのは保存量ではなく「次の判断に必要な状態」)。
- **ノート** `working-notes/<topic>.md` — 推論の記録。追記で育てる。記録するのは
  行動ログではなく推論: 計画 / 仮説と検証結果(予想と合っていたか)/ 発見 /
  判断とその理由(採らなかった案を含む)/ 確定した事実と知識(不確実だったことが
  検証で確定したら、成功・失敗を問わず書く。自明な成功は書かない)。

ルール:

- タスク開始時、`working-notes/` を確認する。担当タスクの状態ファイルとノートが
  あれば読んで続きから再開し、なければ作成する。他タスクのファイルは読んでよいが、
  編集しない(並行する他セッションの状態を壊さないため)。
- タスク開始時、`docs/memory/index.md` で関連カテゴリを確認し、関連する記憶が
  あれば読んでから着手する(過去タスクで確定した知識を再利用し、同じ調査・
  同じ失敗を繰り返さないため)。
- 作業中に未知の領域へ入るとき・技術的な判断を下すとき・予想外の結果に直面した
  ときは、次の行動の前にそのトピックのキーワードで `docs/memory/` を grep し、
  関連する記憶があれば読む(既知の事実と過去の失敗を判断材料に加えるため)。
- コマンド・テスト・検証を実行して結果を確認した直後、毎回次の 2 つを行う
  (タスクの大小を問わない):
  1. 状態ファイルを上書きで最新化する。
  2. その時点で新しく生まれた推論をノートへ追記する。追記する前に、そのトピックの
     キーワードで `docs/memory/` を grep し、関連する記憶があれば読む(発見が
     既存の記憶と重複・矛盾していないかを確かめるため。矛盾するときは、どちらが
     正しいか検証してから記録する)。
- 作業再開時・compaction 後は、続きを始める前に担当タスクの状態ファイルを読む。
  直前の経緯や判断理由が必要なときはノートも読む(会話履歴に頼らず状態を
  復元するため)。
- タスク完了時、担当タスクのノートの知見を `docs/memory/` の記憶へ統合する:
  同トピックの記憶があれば既存ファイルを更新して `generated.at` を最新化し、
  なければカテゴリを選んで `docs/memory/<category>/<topic>.md` を新規作成する
  (合うカテゴリがなければ新設し、ルート `index.md` にカテゴリを追記する)。
  該当カテゴリの `index.md` を更新し、状態ファイルとノートを削除する(進行中の
  状態は、記憶へ昇格した時点で役目を終えるため)。完了時はこの統合・削除の手順が、
  平時の記録ルール(状態ファイルの上書きとノートへの追記)より優先される。
~~~

- [ ] **Step 2: 旧語彙が残っていないことを確認する**

Run: `grep -n "二部構成\|推論の記録は追記\|現在の状態と次の一手」は常に上書き" AGENTS.md; grep -c "state.md" AGENTS.md`
Expected: 1 つ目は該当なし(終了コード 1)、2 つ目は 1 以上。

- [ ] **Step 3: コミット**

```bash
git add AGENTS.md
git commit -m "feat: 推論の外部化ルールを状態ファイル分離へ改訂(用語定義と目的付きルールへ再構成)"
```

---

### Task 4: README.md の追従

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: Task 3 の AGENTS.md 文面(要約対象)
- Produces: なし

- [ ] **Step 1: 各所を次の対応で書き換える**

(a) 概要(冒頭段落)の 1 文:

- 旧: 「会話履歴だけに状態を預けず、作業中の要点をタスクごとの `working-notes/<topic>.md`、完了したタスクの知識をカテゴリ別の `docs/memory/` の記憶に統合します。」
- 新: 「会話履歴だけに状態を預けず、進行の要約をタスクごとの状態ファイル `working-notes/<topic>.state.md` に、推論をノート `working-notes/<topic>.md` に置き、完了したタスクの知識をカテゴリ別の `docs/memory/` の記憶に統合します。」

(b) 導入手順 2 の「このルールが次を担当します」リストを次に置き換える:

```markdown
- タスク開始時に `working-notes/` から担当タスクの状態ファイルとノートを見つける(なければ作る)
- タスク開始時・行動や判断の前・ノートへ追記する前に、`docs/memory/` から関連する記憶を検索して読む
- コマンド・テスト・検証の結果を確認した直後に、状態ファイル(目的・状態・決定・次の一手)を上書きで最新化し、その時点の推論(計画・仮説と検証結果・発見・判断とその理由・確定した事実と知識)をノートへ追記する
- 作業再開時と compaction 後に担当タスクの状態ファイルを読み直す(経緯が必要なときはノートも読む)
- タスク完了時に知見を `docs/memory/` の記憶へ統合し(同トピックがあれば更新)、状態ファイルとノートを削除する
```

(c) 導入手順 3 の移行の 1 文:

- 旧: 「残っているファイルを手動で `working-notes/<topic>.md` へ移してください。」
- 新: 「残っているファイルは、冒頭の「現在の状態と次の一手」を `working-notes/<topic>.state.md` へ、それ以外を `working-notes/<topic>.md` へ手動で移してください。」

(d) 導入手順 5 末尾の「ノートはタスクごとに次の形式で作られます。」とコード例を次に置き換える:

~~~markdown
ファイルはタスクごとに 2 つ作られます。状態ファイル `working-notes/<topic>.state.md`
は常に上書きで最新に保たれます。

```markdown
- 目的: <このタスクで達成すること>
- 状態: <いま分かっていること>
- 決定: <直近の判断>
- 次の一手: <次に行う判断または作業>
```

ノート `working-notes/<topic>.md` には推論が追記されていきます(例)。

```markdown
- 判断: リマインダー文言を手順型へ改訂する。理由: 語気表現は余計な推論を誘発するため(採らなかった案: 強調表現の追加)
```
~~~

(e) 普段の使い方の 2・3・5・6 を次に置き換える(1・4 は不変):

```markdown
2. タスク開始時に、Codex が `working-notes/` から担当タスクの状態ファイルとノートを見つけます
   (なければ `working-notes/<topic>.state.md` と `working-notes/<topic>.md` を作ります)。
3. コマンド・テスト・検証の結果を確認した直後に、Codex が状態ファイルを上書きで最新化し、
   推論をノートへ追記します。
5. セッション再開時・compaction 後には、AGENTS.md のルールに従って状態ファイルを読み直します
   (経緯が必要なときはノートも読みます)。
6. タスク完了時には、担当ノートの知見を `docs/memory/<category>/<topic>.md` の記憶へ統合し(同トピックがあれば更新)、該当する index を更新して、状態ファイルとノートを削除します。
```

(f) 仕組み表の 4 行を次に置き換える(compaction 前・タスク完了後の行は不変):

```markdown
| 平時 | `AGENTS.md` | 状態ファイルとノートの発見・作成、結果確認直後の状態の上書きと推論の追記 |
| 平時(補強) | `post_tool_use.py` | 担当タスクのファイルが 3 分更新されないままツール実行が続くと、ファイルの確認・状態の上書きとノートへの追記・作業再開を促す手順を注入する |
| compaction 後 | `post_compact.py` | compaction の発生と状態ファイルの再確認を通知する |
| 起動・再開時 | `AGENTS.md` | 担当タスクの状態ファイルを読み直す |
```

(g) 制約の 1 つ目の箇条書きの括弧内:

- 旧: 「(複数ノートのうち担当ノートを hook が特定できないため。設計 spec 参照)」
- 新: 「(複数タスクのファイルのうち担当分を hook が特定できないため。設計 spec 参照)」

制約の 2 つ目の箇条書き:

- 旧: 「同名ノートを共有する形になり、上書き競合が起きえます。」
- 新: 「同名のファイルを共有する形になり、上書き競合が起きえます。」

(h) 詳細資料リストの末尾に追加:

```markdown
- [状態ファイル分離の設計](docs/superpowers/specs/2026-08-06-state-file-separation-design.md)
```

- [ ] **Step 2: 旧語彙の残存を確認する**

Run: `grep -n "二部構成\|冒頭の「現在の状態と次の一手」\|推論の記録は追記" README.md`
Expected: 該当なし(終了コード 1)。(c) の移行文中の「現在の状態と次の一手」は状態ファイルの内容名としての言及なので残ってよい(パターンに含めていない)。

- [ ] **Step 3: コミット**

```bash
git add README.md
git commit -m "docs: README を状態ファイル分離の 2 ファイル構成へ追従"
```

---

### Task 5: docs/state-lifecycle.md の追従

**Files:**
- Modify: `docs/state-lifecycle.md`

**Interfaces:**
- Consumes: Task 3 の AGENTS.md 文面(説明対象)
- Produces: なし

- [ ] **Step 1: 各所を次の対応で書き換える**

(a) 冒頭の参照リストに状態ファイル分離の設計を追加(rule-firing 設計への参照の後):

```markdown
[状態ファイル分離の設計](superpowers/specs/2026-08-06-state-file-separation-design.md)を参照してください。
```

(直前の行の「〜の設計を参照してください。」の結び方は既存文に合わせて調整する)

(b) 全体像の表の 1 行目を次の 2 行に置き換える:

```markdown
| `working-notes/<topic>.state.md` | 進行中タスクの現在地(目的・状態・決定・次の一手)を保持する | 高い |
| `working-notes/<topic>.md` | 後続の判断に必要な推論の記録を保持する | 高い |
```

(c) 表の直後の段落:

- 旧: 「ノートはタスクごとに 1 ファイルです。複数セッションを同じディレクトリで並行させても、セッションごとに別のタスクを進めている限り、互いのノートを上書きしません。」
- 新: 「状態ファイルとノートはタスクごとに 1 組です。複数セッションを同じディレクトリで並行させても、セッションごとに別のタスクを進めている限り、互いのファイルを上書きしません。」

(d) 基本の流れ図の 3 行を修正:

- 「AGENTS.md: working-notes/ から担当ノートを見つける(なければ作る)」→「AGENTS.md: working-notes/ から担当タスクのファイルを見つける(なければ作る)」
- 「AGENTS.md: 結果確認の直後に担当ノートへ記録する(PostToolUse が補強)」→「AGENTS.md: 結果確認の直後に状態を上書きし推論を追記する(PostToolUse が補強)」
- 「PostCompact: 発生を通知し、ノートの再確認を促す」→「PostCompact: 発生を通知し、状態ファイルの再確認を促す」
- 「担当ノートの知識を蒸留する」→「担当ノートの知見を蒸留する」

(e) §1 の見出しと本文:

- 見出し: 「## 1. タスク開始・再開時に担当ノートへ辿り着く」→「## 1. タスク開始・再開時に担当タスクのファイルへ辿り着く」
- 本文 1 段落目: 「担当タスクのノート `working-notes/<topic>.md` があればそれを読んで再開し、なければ作成します。」→「担当タスクの状態ファイル `working-notes/<topic>.state.md` とノート `working-notes/<topic>.md` があればそれを読んで再開し、なければ作成します。」同段落の「他タスクのノートは読んでも構いませんが、編集してはいけません。」→「他タスクのファイルは読んでも構いませんが、編集してはいけません。」
- 「ノートは二部構成です。」とコード例を次に置き換える:

~~~markdown
状態ファイルは進行の要約だけを持ち、常に上書きされます。

```markdown
- 目的: 認証エラーの原因を特定する
- 状態: API 呼び出し前の入力検証までは正常
- 決定: 通信層のログを先に確認する
- 次の一手: 失敗レスポンスのステータスとヘッダーを確認する
```

ノートは推論の記録で、追記で育ちます。維持するのは保存量ではなく
「次の判断に必要な状態」であり、それは状態ファイルが担います。
~~~

(f) §2 の本文:

- 「その時点の推論を担当タスクのノートへ記録します。」を含む段落の該当文: 「Codex は、コマンド・テスト・検証を実行して結果を確認した直後に、その時点の推論を担当タスクのノートへ記録します。」→「Codex は、コマンド・テスト・検証を実行して結果を確認した直後に、状態ファイルを上書きで最新化し、その時点の推論を担当タスクのノートへ追記します。」
- grep の説明段落: 「ノートに記録するときは、同じトピックのキーワードで `docs/memory/` を grep し、関連する過去の記憶があれば読みます。未知の領域や予想外の結果に直面したときも同様です。」→「ノートへ追記する前には、同じトピックのキーワードで `docs/memory/` を grep し、発見が既存の記憶と重複・矛盾していないかを確かめます。未知の領域へ入るときや技術的な判断の前には、既知の事実と過去の失敗を判断材料に加えるため、行動の前に grep して関連する記憶を読みます。」
- 箇条書き 2 件: 「冒頭の「現在の状態と次の一手」は、常に最新状態へ上書きする」「それ以降の「推論の記録」は、判断の経緯が失われないよう追記する」→「状態ファイルは、常に最新状態へ上書きする」「ノートは、判断の経緯が失われないよう追記する」
- リマインダーの説明文: 「ノートが 3 分を超えて更新されないままツール実行が続いたとき、ノートの確認・数行の追記・作業再開を促す短い手順をコンテキストへ注入します(再注入は 3 分のクールダウン付き。ノートを更新すれば静かになります)。」→「担当タスクのファイルが 3 分を超えて更新されないままツール実行が続いたとき、ファイルの確認・状態の上書きと数行の追記・作業再開を促す短い手順をコンテキストへ注入します(再注入は 3 分のクールダウン付き。どちらかのファイルを更新すれば静かになります)。」

(g) §3 の復元説明の 1 文: 「まず担当タスクのノート、次に `docs/memory/` を参照し、」→「まず担当タスクの状態ファイルとノート、次に `docs/memory/` を参照し、」

(h) §4 の本文と表:

- 本文: 「compaction の実行と担当タスクのノートの再確認を通知します。」→「compaction の実行と担当タスクの状態ファイルの再確認を通知します。」
- 「AGENTS.md の「compaction 後に担当ノートを読み直す」ルール」→「AGENTS.md の「compaction 後に状態ファイルを読み直す」ルール」
- 責任分担表の AGENTS.md 行: 「担当ノートの発見・作成、結果確認直後の推論記録、再開時・compaction 後の再読」→「担当タスクのファイルの発見・作成、結果確認直後の状態の上書きと推論の追記、再開時・compaction 後の再読」
- 同表の post_tool_use.py 行: 「ノート未更新時のルール想起の注入」→「ファイル未更新時のルール想起の注入」

(i) §5: 「同時に該当カテゴリの `index.md` を更新し、`working-notes/<topic>.md` を削除します。」→「同時に該当カテゴリの `index.md` を更新し、状態ファイルとノートを削除します。」同節の「他のセッションが進行中のタスクのノートは `working-notes/` に残ったままであり」→「他のセッションが進行中のタスクのファイルは `working-notes/` に残ったままであり」

(j) 障害時の復元順序を次に置き換える:

```markdown
1. 担当タスクの状態ファイル(`working-notes/<topic>.state.md`)
2. 同タスクのノート(`working-notes/<topic>.md`)の推論の記録
3. `docs/memory/index.md` から辿れる関連する記憶(または `docs/memory/` の grep)
4. `.harness/compaction-snapshots/` の直近 transcript
```

- [ ] **Step 2: 旧語彙の残存を確認する**

Run: `grep -n "二部構成" docs/state-lifecycle.md; grep -n "冒頭" docs/state-lifecycle.md`
Expected: 「二部構成」は該当なし(終了コード 1)。「冒頭」は SessionStart 廃止の経緯(歴史的記述)にのみ残ってよい — それ以外にヒットしたら追従漏れなので直す。

- [ ] **Step 3: コミット**

```bash
git add docs/state-lifecycle.md
git commit -m "docs: state-lifecycle を状態ファイル分離へ追従(構造例・責任分担・復元順序)"
```

---

### Task 6: 先行 spec への改訂注記と総合検証

**Files:**
- Modify: `docs/superpowers/specs/2026-08-05-reminder-wording-design.md`
- Modify: `docs/superpowers/specs/2026-08-04-multi-session-working-notes-design.md`

**Interfaces:**
- Consumes: なし
- Produces: なし

- [ ] **Step 1: reminder-wording spec に改訂参照を注記する**

`## 新しい注入文言(REMINDER 定数)` の見出し直後に次の 1 行を追加:

```markdown
(改訂 2026-08-06: 本文言は[状態ファイル分離の設計](2026-08-06-state-file-separation-design.md)で 2 ファイル構成へ差し替えられた)
```

- [ ] **Step 2: multi-session spec に改訂参照を注記する**

決定事項表の「ノートの単位」行の決定セル末尾に追加:

```text
(改訂 2026-08-06: [状態ファイル分離の設計](2026-08-06-state-file-separation-design.md)で 1 タスク 2 ファイルへ)
```

「ノート内部構造」行の決定セル末尾に追加:

```text
(改訂 2026-08-06: 冒頭セクションは状態ファイルへ分離。同上の設計を参照)
```

- [ ] **Step 3: 総合検証を実行する**

Run: `python3 tests/test_post_tool_use.py && python3 tests/test_pre_compact.py && grep -rn "二部構成" AGENTS.md README.md docs/state-lifecycle.md; echo "grep exit: $?"`
Expected: 両テストとも all tests passed。grep は該当なし(exit 1)。

- [ ] **Step 4: コミット**

```bash
git add docs/superpowers/specs/2026-08-05-reminder-wording-design.md docs/superpowers/specs/2026-08-04-multi-session-working-notes-design.md
git commit -m "docs: 先行 spec に状態ファイル分離への改訂参照を注記"
```

---

## 計画外(実装後の観察項目)

spec 検証方法 4 の実機観察(状態ファイルの上書き維持・ノートへの推論追記・リマインダー後の挙動・完了時の両ファイル削除)は、次回の長時間タスクの運用で確認し、知見を通常の完了時フローで `docs/memory/harness/e2e-verification.md` へ統合する。
