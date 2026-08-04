# working-notes 複数セッション対応 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 作業ノートを単一の `working-notes.md` からタスク単位の `working-notes/<topic>.md` へ分割し、同一ディレクトリで並行する複数セッションがノートを上書きし合わないようにする。

**Architecture:** ノートの選択はエージェントの AGENTS.md ルールが担い、hook は決定論的処理(transcript 退避・通知)のみに純化する。SessionStart hook と PreCompact の鮮度警告は廃止する。spec: `docs/superpowers/specs/2026-08-04-multi-session-working-notes-design.md`。

**Tech Stack:** Python 3 標準ライブラリのみ(hook・テストとも)。テストは `python3 tests/<file>.py` で実行する自前ランナー形式。

## Global Constraints

- hook とテストは Python 3 標準ライブラリのみ使用(依存追加禁止)
- ドキュメント・コメントは日本語
- ブランチ `feat/multi-session-working-notes` 上で作業(main 直コミット禁止)
- ノートのパスは `working-notes/<topic>.md`(`<topic>` は worklog `YYYY-MM-DD-<topic>.md` と同じ短いケバブケース)
- 各タスク完了時にコミットする

---

### Task 1: PreCompact の鮮度警告を廃止する

**Files:**
- Modify: `.codex/hooks/pre_compact.py`
- Test: `tests/test_pre_compact.py`

**Interfaces:**
- Consumes: なし
- Produces: `pre_compact.py` は transcript スナップショット退避のみを行い、stdout には何も出力しない(後続タスクのドキュメントがこの挙動を記述する)

- [ ] **Step 1: 鮮度警告テスト 2 件を「警告しないこと」のテストに置き換える**

`tests/test_pre_compact.py` の `test_stale_notes_warns` と `test_fresh_notes_silent` の 2 関数を削除し、代わりに次の 1 関数を追加する。旧実装は `working-notes.md`(レガシー単一ファイル)が古いと警告を出すため、このテストは旧実装では FAIL する(red が確認できる)。

```python
def test_stale_notes_no_warning() -> None:
    """鮮度警告は廃止済み: ノートが古くても stdout は空(複数セッション対応 spec)。"""
    with tempfile.TemporaryDirectory() as tmp:
        cwd, transcript = make_workdir(tmp)
        old = time.time() - 3600
        # レガシー単一ファイルと新形式ディレクトリの両方が古くても警告しない
        legacy = cwd / "working-notes.md"
        legacy.write_text("## 現在の状態と次の一手\n", encoding="utf-8")
        os.utime(legacy, (old, old))
        notes_dir = cwd / "working-notes"
        notes_dir.mkdir()
        note = notes_dir / "sample-task.md"
        note.write_text("## 現在の状態と次の一手\n", encoding="utf-8")
        os.utime(note, (old, old))
        proc = run_hook({"cwd": str(cwd), "transcript_path": str(transcript), "turn_id": "t"})
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip() == "", proc.stdout
```

`import os` と `import time` は既存のまま残す(このテストが使う)。

- [ ] **Step 2: テストを実行して FAIL を確認する**

Run: `python3 tests/test_pre_compact.py`
Expected: `test_stale_notes_no_warning` で AssertionError(stdout に `systemMessage` の JSON が出るため)。他のテストは PASS。

- [ ] **Step 3: pre_compact.py から鮮度警告を削除する**

`.codex/hooks/pre_compact.py` 全体を次の内容に置き換える(`STALE_SECONDS`・notes 判定ブロックの削除、docstring の更新):

```python
#!/usr/bin/env python3
"""Codex PreCompact hook: transcript のスナップショット保存。

設計: docs/superpowers/specs/2026-08-01-state-externalization-design.md 1-3節、
および docs/superpowers/specs/2026-08-04-multi-session-working-notes-design.md。
compaction はブロックしない。モデルへの注入は行わない(仕様上不可)。
ノート鮮度の警告は複数セッション対応で廃止した: hook はセッションとノートの
対応を知り得ず、mtime 判定は他セッションの更新で偽陰性になるため。
"""
import json
import shutil
import sys
import time
from pathlib import Path

KEEP = 10


def main() -> int:
    payload = json.load(sys.stdin)
    cwd = Path(payload.get("cwd") or ".")

    transcript = payload.get("transcript_path") or ""
    src = Path(transcript)
    if src.is_file():
        snap_dir = cwd / ".harness" / "compaction-snapshots"
        snap_dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        turn = (payload.get("turn_id") or "x")[:12]
        shutil.copy2(src, snap_dir / f"{stamp}-{turn}.jsonl")
        for old in sorted(snap_dir.glob("*.jsonl"))[:-KEEP]:
            old.unlink()
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: テストを実行して全件 PASS を確認する**

Run: `python3 tests/test_pre_compact.py`
Expected: `PASS test_missing_transcript_is_noop` / `PASS test_rotation_keeps_10` / `PASS test_snapshot_created` / `PASS test_stale_notes_no_warning` / `all tests passed`

- [ ] **Step 5: コミット**

```bash
git add .codex/hooks/pre_compact.py tests/test_pre_compact.py
git commit -m "feat: PreCompact の鮮度警告を廃止(複数セッションで偽陰性になるため)"
```

---

### Task 2: SessionStart hook を廃止する

**Files:**
- Modify: `.codex/hooks.json`
- Delete: `.codex/hooks/session_start.py`
- Delete: `tests/test_session_start.py`

**Interfaces:**
- Consumes: なし
- Produces: hooks.json は PreCompact / PostCompact の 2 イベントのみ登録(後続タスクのドキュメントがこの構成を記述する)

- [ ] **Step 1: hooks.json から SessionStart 登録を削除する**

`.codex/hooks.json` 全体を次の内容に置き換える:

```json
{
  "hooks": {
    "PreCompact": [
      {
        "matcher": "manual|auto",
        "hooks": [
          { "type": "command", "command": "python3 .codex/hooks/pre_compact.py" }
        ]
      }
    ],
    "PostCompact": [
      {
        "matcher": "manual|auto",
        "hooks": [
          { "type": "command", "command": "python3 .codex/hooks/post_compact.py" }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: hook スクリプトとテストを削除する**

```bash
git rm .codex/hooks/session_start.py tests/test_session_start.py
```

- [ ] **Step 3: JSON の妥当性と残テストを確認する**

Run: `python3 -m json.tool .codex/hooks.json >/dev/null && python3 tests/test_pre_compact.py`
Expected: JSON エラーなし、`all tests passed`

- [ ] **Step 4: コミット**

```bash
git add .codex/hooks.json
git commit -m "feat: SessionStart hook を廃止(複数ノートから担当ノートを hook は選べない)"
```

---

### Task 3: ノートをタスク単位に分割する(AGENTS.md / .gitignore / PostCompact 文言)

**Files:**
- Modify: `AGENTS.md`
- Modify: `.gitignore`
- Modify: `.codex/hooks/post_compact.py`

**Interfaces:**
- Consumes: なし
- Produces: ノートパス規約 `working-notes/<topic>.md`(Task 4 のドキュメントがこの規約を記述する)

- [ ] **Step 1: AGENTS.md のルールを複数ノート前提に書き換える**

`AGENTS.md` 全体を次の内容に置き換える(spec「AGENTS.md の新ルール文面」の転記):

```markdown
# AGENTS.md

## 推論の外部化

- タスク開始時に `working-notes/` を確認する。担当タスクのノート
  `working-notes/<topic>.md` があればそれを読んで再開し、なければ作成する
  (`<topic>` は完了時の worklog と同じ短いケバブケース)。
  他タスクのノートは読んでよいが、編集しない。
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
  過去タスクの経緯は `docs/worklog/index.md` から辿る。
- タスク完了時、担当タスクのノートを OKF 形式で `docs/worklog/YYYY-MM-DD-<topic>.md`
  へ移し、`docs/worklog/index.md` に 1 行追記し、そのノートファイルを削除する。
  完了時はこの手順が「追記する」ルールより優先される。
```

- [ ] **Step 2: .gitignore を更新する**

`.gitignore` 全体を次の内容に置き換える(旧 `working-notes.md` は移行安全策として残す。最終レビュー指摘 #1 反映):

```gitignore
working-notes.md
working-notes/
.harness/
```

- [ ] **Step 3: post_compact.py の通知文言を更新する**

`.codex/hooks/post_compact.py` 全体を次の内容に置き換える(文言のみ変更):

```python
#!/usr/bin/env python3
"""Codex PostCompact hook: compaction 発生をユーザーへ通知する。"""
import json
import sys


def main() -> int:
    sys.stdin.read()  # payload は使わないが読み切る
    print(json.dumps({
        "systemMessage": "compaction が実行されました。エージェントは担当タスクのノート(working-notes/<topic>.md)を読み直して状態を確認します。"
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: post_compact.py の動作を確認する**

Run: `printf '{}' | python3 .codex/hooks/post_compact.py`
Expected: `working-notes/<topic>.md` を含む `systemMessage` の JSON が 1 行出力され、終了コード 0

- [ ] **Step 5: コミット**

```bash
git add AGENTS.md .gitignore .codex/hooks/post_compact.py
git commit -m "feat: 作業ノートをタスク単位の working-notes/<topic>.md に分割"
```

---

### Task 4: ドキュメントを複数ノート運用に追従させる

**Files:**
- Modify: `README.md`
- Modify: `docs/state-lifecycle.md`

**Interfaces:**
- Consumes: Task 1〜3 の最終挙動(SessionStart なし・鮮度警告なし・`working-notes/<topic>.md` 規約)
- Produces: なし(最終タスク)

- [ ] **Step 1: README.md を書き換える**

`README.md` 全体を次の内容に置き換える:

````markdown
# Codex 状態外部化ハーネス

Codex CLI の compaction やセッション再開をまたいで、作業の目的・現在地・判断理由を
リポジトリ内のファイルから復元できるようにする最小構成のハーネスです。

会話履歴だけに状態を預けず、作業中の要点をタスクごとの `working-notes/<topic>.md`、
完了したタスクの知識を `docs/worklog/` に残します。複数セッションを同じディレクトリで
並行させても、タスクが異なればノートは衝突しません。hook は推論を生成するのではなく、
compaction 前の生ログ退避と compaction 発生の通知を担当します。

## 対応状況

| 項目 | 状態 |
|---|---|
| Codex CLI 向けの記録ルール(複数セッション対応) | 実装済み |
| PreCompact / PostCompact hook | 実装済み |
| hook の単体テスト | 実装済み |
| Codex CLI 実機での一連の E2E 検証 | 単一セッション運用で完了(docs/worklog/2026-08-02-phase1-e2e.md)。複数セッション並行の実機検証は未実施 |
| Claude Code 対応 | 未実装(フェーズ2) |

## 前提条件

- Codex CLI
- Python 3(hook は標準ライブラリだけを使用)
- Git 管理されたプロジェクト

## 自分のプロジェクトへ導入する

このリポジトリを取得済みとして、以下のファイルを導入先へ追加します。

```text
<your-project>/
├── AGENTS.md
├── .gitignore
├── .codex/
│   ├── hooks.json
│   └── hooks/
│       ├── pre_compact.py
│       └── post_compact.py
└── docs/
    └── worklog/
        └── index.md
```

### 1. hook をコピーする

`SOURCE` と `TARGET` を実際の絶対パスに置き換えて実行します。

```bash
SOURCE=/path/to/harness-sample
TARGET=/path/to/your-project

mkdir -p "$TARGET/.codex/hooks"
cp "$SOURCE/.codex/hooks.json" "$TARGET/.codex/hooks.json"
cp "$SOURCE/.codex/hooks/pre_compact.py" "$TARGET/.codex/hooks/pre_compact.py"
cp "$SOURCE/.codex/hooks/post_compact.py" "$TARGET/.codex/hooks/post_compact.py"
```

既存の `.codex/hooks.json` がある場合は上書きせず、`PreCompact` と `PostCompact` の
登録を既存設定へマージしてください。

### 2. 記録ルールを AGENTS.md へ追加する

このリポジトリの [AGENTS.md](AGENTS.md) にある「推論の外部化」セクションを、導入先の
`AGENTS.md` へ追加します。既存の指示は残してください。

このルールが次を担当します。

- タスク開始時に `working-notes/` から担当タスクのノートを見つける(なければ作る)
- 選択、仮説、検証結果、発見、計画変更を発生時点で記録する
- ノート冒頭の「現在の状態と次の一手」を最新に保つ
- 作業再開時と compaction 後に担当ノートを読み直す
- タスク完了時に記録を `docs/worklog/` へ移す

### 3. 一時ファイルを Git 管理外にする

導入先の `.gitignore` に次を追加します。

```gitignore
working-notes.md
working-notes/
.harness/
```

`working-notes/` は進行中タスクの状態、`.harness/compaction-snapshots/` は compaction 前の
生ログ退避先です。完了後に残す知識は `docs/worklog/` へ移して Git 管理します。

以前の単一ファイル構成(`working-notes.md`)から移行する場合は、残っているファイルを
手動で `working-notes/<topic>.md` へ移してください。旧 `working-notes.md` の ignore 指定は、
移行が済むまでの誤コミットを防ぐ安全策として残しています。

### 4. worklog を初期化する

導入先に `docs/worklog/index.md` を作り、このリポジトリの
[worklog index](docs/worklog/index.md) にある frontmatter とエントリ書式を使います。
このサンプル固有の「エントリ一覧」はコピーせず、導入先の記録だけを並べてください。

### 5. 設定を確認する

導入先のルートで次を実行します。

```bash
python3 -m json.tool .codex/hooks.json >/dev/null
printf '{"cwd":".","transcript_path":""}\n' | python3 .codex/hooks/pre_compact.py
```

どちらも何も表示せず正常終了すれば設定は妥当です。最後に、そのプロジェクトを作業
ディレクトリとして Codex CLI を起動し、hook 設定の読み込みエラーや警告がないことを
確認してください。

ノートはタスクごとに次の形式で作られます。

```markdown
## 現在の状態と次の一手

- 目的: <このタスクで達成すること>
- 状態: <いま分かっていること>
- 次の一手: <次に行う判断または作業>

## 推論の記録
```

## 普段の使い方

1. Codex と通常どおりタスクを進めます。複数セッションを並行させる場合は、
   セッションごとに別のタスクを割り当てます。
2. タスク開始時に、Codex が `working-notes/` から担当タスクのノートを見つけます
   (なければ `working-notes/<topic>.md` を作ります)。
3. AGENTS.md の条件に該当する判断や発見が起きると、Codex が担当ノートを更新します。
4. compaction 前には transcript が `.harness/compaction-snapshots/` へ退避されます。
5. セッション再開時・compaction 後には、AGENTS.md のルールに従って担当ノートを読み直します。
6. タスク完了時には、担当ノートを `docs/worklog/YYYY-MM-DD-<topic>.md` へ移し、index に追加します。

重要なのは、hook 自体は計画や判断理由を書き出さないことです。推論の外部化は
AGENTS.md の記録ルールが主に担い、hook は取りこぼしを減らす補助層として働きます。

## 仕組み

| 層 | 担当 | 動作 |
|---|---|---|
| 平時 | `AGENTS.md` | 担当ノートの発見・作成と、判断・仮説・発見・状態の随時記録 |
| compaction 前 | `pre_compact.py` | transcript を退避する |
| compaction 後 | `post_compact.py` | compaction の発生とノート再確認を通知する |
| 起動・再開時 | `AGENTS.md` | 担当タスクのノートを読み直す |
| タスク完了後 | `docs/worklog/` | 蒸留した推論を OKF 形式の Markdown として保持する |

スナップショットは直近10件だけを保持するコールドストレージです。通常の復元には
担当タスクのノートと worklog を使い、生ログは取りこぼしを調べる最終手段とします。

## このリポジトリでのテスト

```bash
python3 tests/test_pre_compact.py
```

テストはスナップショット作成とローテーション、鮮度警告を出さないこと、transcript
不在時の no-op を確認します。単一セッション運用での hook 発火とタスク完了までの
一連の挙動は、実機 E2E で確認済みです(docs/worklog/2026-08-02-phase1-e2e.md)。

## 制約

- 起動・再開時や compaction 後の状態復元は AGENTS.md のルールに依存します。hook に
  よる機械的なコンテキスト注入は行いません(複数ノートのうち担当ノートを hook が
  特定できないため。設計 spec 参照)。
- 同じタスクを複数セッションで同時に進める運用は対象外です。同名ノートを共有する
  形になり、上書き競合が起きえます。
- transcript のスナップショットには会話内容がそのまま含まれます。`.harness/` を
  Git 管理外のままにし、共有やバックアップ時の取り扱いに注意してください。
- 現在の実装は Codex CLI 向けです。設計書にある Claude Code 対応はまだありません。
- 本ハーネスはモデルの private reasoning を保存するものではありません。後続判断に
  必要な計画、仮説、発見、判断理由、失敗から得た知識を明示的に外部化します。

## 詳細資料

- [状態外部化の設計](docs/superpowers/specs/2026-08-01-state-externalization-design.md)
- [working-notes 複数セッション対応の設計](docs/superpowers/specs/2026-08-04-multi-session-working-notes-design.md)
- [フェーズ1の実装計画](docs/superpowers/plans/2026-08-02-phase1-codex-state-externalization.md)
- [worklog index](docs/worklog/index.md)
````

- [ ] **Step 2: docs/state-lifecycle.md を書き換える**

`docs/state-lifecycle.md` 全体を次の内容に置き換える:

````markdown
# Codex の作業状態が保存・復元されるまで

この文書は、Codex がタスクを始めてから完了するまでに、作業状態がどのように
ファイルへ残り、compaction やセッション再開をまたいで復元されるかを時系列で説明します。
導入手順は [README](../README.md)、設計上の判断は
[状態外部化の設計](superpowers/specs/2026-08-01-state-externalization-design.md)と
[working-notes 複数セッション対応の設計](superpowers/specs/2026-08-04-multi-session-working-notes-design.md)を参照してください。

## 全体像

状態の保存先は、用途の異なる3種類に分かれます。

| 保存先 | 役割 | 普段の参照頻度 |
|---|---|---|
| `working-notes/<topic>.md` | 進行中タスクごとの現在地と、後続判断に必要な推論を保持する | 高い |
| `docs/worklog/` | 完了したタスクから得た知識を恒久的に保持する | 必要なとき |
| `.harness/compaction-snapshots/` | compaction 前の transcript を生ログのまま退避する | 低い(最終手段) |

ノートはタスクごとに 1 ファイルです。複数セッションを同じディレクトリで並行させても、
セッションごとに別のタスクを進めている限り、互いのノートを上書きしません。

基本の流れは次のとおりです。

```text
タスク開始・再開
  │ AGENTS.md: working-notes/ から担当ノートを見つける(なければ作る)
  ▼
平時の作業
  │ AGENTS.md: 判断・仮説・発見を発生時点で担当ノートに記録する
  ▼
compaction 前
  │ PreCompact: transcript を退避する
  ▼
compaction 後
  │ PostCompact: 発生を通知し、ノートの再確認を促す
  ▼
作業継続 ────────────────┐
  │                       │ 次の compaction
  ▼                       └───────────────
タスク完了
  │ 担当ノートの知識を蒸留する
  ▼
docs/worklog/ に保存(ノートは削除)
```

## 1. タスク開始・再開時に担当ノートへ辿り着く

タスクを始めるとき、または中断したタスクを再開するとき、Codex は AGENTS.md の
「推論の外部化」ルールに従って `working-notes/` を確認します。担当タスクのノート
`working-notes/<topic>.md` があればそれを読んで再開し、なければ作成します。
`<topic>` は完了時の worklog `YYYY-MM-DD-<topic>.md` と同じ短いケバブケースの語で、
セッションやハーネスが変わっても同じタスクなら同じノートに辿り着けます。
他タスクのノートは読んでも構いませんが、編集してはいけません。

かつては SessionStart hook がノート冒頭をコンテキストへ機械的に注入していましたが、
ノートの複数化にともない廃止しました。hook は「このセッションがどのタスクを担当
するか」を知らないため、正しいノートを選んで注入できず、誤ったノートの注入は
注入しないことより有害だからです。

ノートは二部構成です。

```markdown
## 現在の状態と次の一手

- 目的: 認証エラーの原因を特定する
- 状態: API 呼び出し前の入力検証までは正常
- 決定: 通信層のログを先に確認する
- 次の一手: 失敗レスポンスのステータスとヘッダーを確認する

## 推論の記録
```

## 2. 平時は判断が生まれた時点で記録する

作業中の主な保存機構は hook ではなく、`AGENTS.md` の「推論の外部化」ルールです。
Codex は、次のような事象が起きた時点で担当タスクのノートを更新します。

- 複数案から1案を選んだ
- 仮説を立てた、または検証結果が出た
- 予想外の結果やエラーに遭遇した
- ドキュメント、Web、コードから事実を確認した
- 計画や方針を変更した

記録するのはコマンドの羅列ではありません。「なぜその案を選んだか」「何を予想し、
結果はどうだったか」「次の判断に何が必要か」といった、作業を続けるための推論です。

- 冒頭の「現在の状態と次の一手」は、常に最新状態へ上書きする
- それ以降の「推論の記録」は、判断の経緯が失われないよう追記する

この平時の記録が主防御です。compaction の直前になってから推論を書き出す設計ではない
ため、compaction がいつ発生しても、直前までに明示された状態をファイルから復元できます。

## 3. compaction 前に生ログを退避する

compaction の直前には、`PreCompact` に登録された `.codex/hooks/pre_compact.py` が、
hook payload の `transcript_path` が実在する場合に、そのファイルを
`.harness/compaction-snapshots/<日時>-<turn>.jsonl` へコピーします。

スナップショットはファイル名順で古いものから削除され、直近10件だけが残ります。
transcript が見つからない場合も compaction は妨げず、何も退避せず正常終了します。

以前あった「ノートが30分以上古い」という警告は廃止しました。複数セッションでは
他セッションのノート更新が警告を誤って抑制する(偽陰性)ため、信頼できるシグナルに
ならないからです。ノートの鮮度は平時の記録ルール(手順2)だけが守ります。

生ログには会話内容がそのまま含まれるため、通常の復元元にはしません。まず担当タスクの
ノート、次に `docs/worklog/` を参照し、それでも失われた情報を特定できない場合だけ
スナップショットを使います。`.harness/` は Git 管理や共有の対象外です。

## 4. compaction 後はノートから作業を継続する

compaction 後には、`PostCompact` に登録された `.codex/hooks/post_compact.py` が、
compaction の実行と担当タスクのノートの再確認を通知します。

`post_compact.py` 自身は状態を読み込んだり、コンテキストへ注入したりしません。
Codex では PostCompact から追加コンテキストを渡せないため、復元は `AGENTS.md` の
「compaction 後に担当ノートを読み直す」ルールが担います。

各要素の責任は次のように分かれます。

| 要素 | 担当すること | 担当しないこと |
|---|---|---|
| `AGENTS.md` | 担当ノートの発見・作成、推論の随時記録、再開時・compaction 後の再読 | transcript の自動退避 |
| `pre_compact.py` | 生ログ退避 | 推論の生成、compaction の停止、ノートの読み書き |
| `post_compact.py` | compaction 発生の通知 | 状態の注入 |

## 5. タスク完了時に一時状態を恒久知識へ変える

タスクが完了したら、担当タスクのノートの内容を OKF 形式の
`docs/worklog/YYYY-MM-DD-<topic>.md` へ移します。記録する項目は、計画、仮説と
検証結果、発見、判断とその理由、失敗から得た知識です。空の項目は省略できます。

同時に `docs/worklog/index.md` へ1行追加し、`working-notes/<topic>.md` を削除します。
後続タスクはまず index で関連する記録を探し、必要な worklog だけを読むため、
AGENTS.md や起動時コンテキストを過去の知識で肥大化させずに済みます。

この時点で、進行中の状態だった情報は次のタスクでも参照できる恒久知識になります。
他のセッションが進行中のタスクのノートは `working-notes/` に残ったままであり、
影響を受けません。

## 障害時の復元順序

再開時に情報が足りない場合は、情報量の少ない順に確認します。

1. 担当タスクのノート(`working-notes/<topic>.md`)冒頭の「現在の状態と次の一手」
2. 同ノートの「推論の記録」全文
3. `docs/worklog/index.md` から辿れる関連タスク
4. `.harness/compaction-snapshots/` の直近 transcript

この順序なら、通常は短い状態だけで再開でき、必要な場合に限って詳細や生ログまで
掘り下げられます。
````

- [ ] **Step 3: 古い参照が残っていないことを確認する**

Run: `grep -rn "session_start\|SessionStart\|30分\|working-notes\.md" README.md AGENTS.md docs/state-lifecycle.md .codex/ tests/`
Expected: ヒットするのは (1) README の移行手順にある `working-notes.md`(意図的)、(2) state-lifecycle.md の「30分以上古い」警告の廃止説明(意図的)、(3) tests/test_pre_compact.py のレガシーファイル検証(意図的)のみ。それ以外のヒットは修正漏れなので直す。

- [ ] **Step 4: 全テストを実行する**

Run: `python3 tests/test_pre_compact.py && python3 -m json.tool .codex/hooks.json >/dev/null`
Expected: `all tests passed`、JSON エラーなし

- [ ] **Step 5: コミット**

```bash
git add README.md docs/state-lifecycle.md
git commit -m "docs: README と state-lifecycle を複数ノート運用に追従"
```
