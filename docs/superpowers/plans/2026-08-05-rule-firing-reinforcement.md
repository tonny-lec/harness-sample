# 記録・検索ルールの発火保証 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 記録・検索ルールのアンカーを行動境界(ツール実行結果の確認直後)へ移し、PostToolUse hook によるリマインダー注入で機械的に裏打ちして、セッション中盤でもルールが発火するようにする。

**Architecture:** 案 A(AGENTS.md ルール改訂)+ 案 B(新規 `post_tool_use.py`: working-notes/ の最新 mtime が 3 分超過なら 2 行の定型リマインダーを additionalContext 注入、クールダウン 3 分)。あわせて hook 全般をフェイルオープン化(`pre_compact.py` の懸案解消を含む)。spec: `docs/superpowers/specs/2026-08-05-rule-firing-reinforcement-design.md`。

**Tech Stack:** Python 3 標準ライブラリのみ。テストは `python3 tests/<file>.py` の自前ランナー形式。

## Global Constraints

- hook とテストは Python 3 標準ライブラリのみ使用(依存追加禁止)
- ドキュメント・コメントは日本語
- ブランチ `feat/rule-firing-reinforcement` 上で作業(main 直コミット禁止)
- hook は例外時に常に exit 0(ツール実行・compaction をブロックしない)
- 定数: `STALE_SECONDS = 180` / `COOLDOWN_SECONDS = 180`(hook 冒頭)
- stamp ファイルは `.harness/note-reminder-stamp`(git 管理外)
- コミットメッセージ末尾に `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` を付ける

---

### Task 1: PostToolUse リマインダー hook(TDD)

**Files:**
- Create: `.codex/hooks/post_tool_use.py`
- Test: `tests/test_post_tool_use.py`(新規)

**Interfaces:**
- Consumes: なし
- Produces: `.codex/hooks/post_tool_use.py`(Task 3 が hooks.json に登録する)。stdin に JSON payload(`cwd` を使用)を受け、条件を満たすときだけ additionalContext の JSON を 1 行出力する

- [ ] **Step 1: 出力スキーマを一次資料で確認する**

<https://learn.chatgpt.com/docs/hooks>(旧 developers.openai.com/codex/hooks)の PostToolUse の出力例を確認し、`additionalContext` を包む正確な JSON キー構造を控える。確認結果(スキーマと出典箇所)を報告に記載する。取得できない場合は下記 Step 4 のコードにある `hookSpecificOutput.additionalContext` 形式を暫定採用し、その旨を DONE_WITH_CONCERNS で報告する(実機 E2E で最終確認するため)。

- [ ] **Step 2: 失敗するテストを書く**

`tests/test_post_tool_use.py` を次の内容で作成する(Step 1 でスキーマが異なると判明した場合、アサーションは「stdout の JSON に `additionalContext` キーが含まれ、値にリマインダー文が入る」という検査方針を保ったままキー参照だけ合わせる):

```python
#!/usr/bin/env python3
"""tests/test_post_tool_use.py — stdlib のみ。python3 tests/test_post_tool_use.py で実行。"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / ".codex" / "hooks" / "post_tool_use.py"


def run_hook(cwd: Path, raw: str = None) -> subprocess.CompletedProcess:
    data = raw if raw is not None else json.dumps({"cwd": str(cwd)})
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=data,
        capture_output=True,
        text=True,
        timeout=30,
    )


def make_note(cwd: Path, age_seconds: float = 0.0) -> Path:
    notes = cwd / "working-notes"
    notes.mkdir(exist_ok=True)
    note = notes / "sample-task.md"
    note.write_text("## 現在の状態と次の一手\n", encoding="utf-8")
    if age_seconds:
        old = time.time() - age_seconds
        os.utime(note, (old, old))
    return note


def make_stamp(cwd: Path, age_seconds: float = 0.0) -> Path:
    stamp = cwd / ".harness" / "note-reminder-stamp"
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.touch()
    if age_seconds:
        old = time.time() - age_seconds
        os.utime(stamp, (old, old))
    return stamp


def reminder_emitted(proc: subprocess.CompletedProcess) -> bool:
    if not proc.stdout.strip():
        return False
    out = json.loads(proc.stdout)
    return "リマインダー" in proc.stdout and "additionalContext" in proc.stdout and isinstance(out, dict)


def test_no_notes_reminds() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        proc = run_hook(cwd)
        assert proc.returncode == 0, proc.stderr
        assert reminder_emitted(proc), proc.stdout
        assert (cwd / ".harness" / "note-reminder-stamp").is_file()


def test_fresh_note_silent() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        make_note(cwd)
        proc = run_hook(cwd)
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip() == "", proc.stdout


def test_stale_note_reminds() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        make_note(cwd, age_seconds=600)
        proc = run_hook(cwd)
        assert proc.returncode == 0, proc.stderr
        assert reminder_emitted(proc), proc.stdout


def test_cooldown_suppresses() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        make_note(cwd, age_seconds=600)
        make_stamp(cwd)  # 直前に注入済み
        proc = run_hook(cwd)
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip() == "", proc.stdout


def test_expired_stamp_reminds_and_touches() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        make_note(cwd, age_seconds=600)
        stamp = make_stamp(cwd, age_seconds=600)
        proc = run_hook(cwd)
        assert proc.returncode == 0, proc.stderr
        assert reminder_emitted(proc), proc.stdout
        assert time.time() - stamp.stat().st_mtime < 60  # stamp が更新された


def test_malformed_stdin_silent() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        proc = run_hook(Path(tmp), raw="not json")
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip() == "", proc.stdout


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all tests passed")
```

- [ ] **Step 3: テストを実行して FAIL を確認する**

Run: `python3 tests/test_post_tool_use.py`
Expected: hook ファイルが存在しないため最初のテストで失敗(FileNotFoundError 等)。

- [ ] **Step 4: hook を実装する**

`.codex/hooks/post_tool_use.py` を次の内容で作成する(Step 1 でスキーマが異なると判明した場合は出力部のキー構造だけ合わせる):

```python
#!/usr/bin/env python3
"""Codex PostToolUse hook: 作業ノートが古いままのとき、記録・検索ルールの想起を注入する。

設計: docs/superpowers/specs/2026-08-05-rule-firing-reinforcement-design.md。
どのノートがこのセッションのものかは hook には知り得ないため、内容レスの定型
リマインダーのみを注入する(誤ったノートの注入は有害、内容レスの想起は無害)。
複数セッション並行時の偽陰性(他セッションの更新・注入による抑制)は許容する。
例外時は常に exit 0(ツール実行をブロックしない)。
"""
import json
import sys
import time
from pathlib import Path

STALE_SECONDS = 180
COOLDOWN_SECONDS = 180

REMINDER = (
    "リマインダー: working-notes/ の担当ノートが 3 分以上更新されていません。"
    "直近の判断・検証結果をノートに記録し、関連する docs/memory/ を grep で"
    "確認してください(AGENTS.md「推論の外部化」)。"
)


def newest_note_mtime(notes_dir: Path) -> float:
    if not notes_dir.is_dir():
        return 0.0
    mtimes = [p.stat().st_mtime for p in notes_dir.glob("*.md")]
    return max(mtimes, default=0.0)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        cwd = Path(payload.get("cwd") or ".")
        now = time.time()
        if now - newest_note_mtime(cwd / "working-notes") <= STALE_SECONDS:
            return 0
        stamp = cwd / ".harness" / "note-reminder-stamp"
        if stamp.is_file() and now - stamp.stat().st_mtime <= COOLDOWN_SECONDS:
            return 0
        stamp.parent.mkdir(parents=True, exist_ok=True)
        stamp.touch()
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": REMINDER,
            }
        }, ensure_ascii=False))
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: テストを実行して全件 PASS を確認する**

Run: `python3 tests/test_post_tool_use.py`
Expected: `PASS test_cooldown_suppresses` / `PASS test_expired_stamp_reminds_and_touches` / `PASS test_fresh_note_silent` / `PASS test_malformed_stdin_silent` / `PASS test_no_notes_reminds` / `PASS test_stale_note_reminds` / `all tests passed`

- [ ] **Step 6: コミット**

```bash
git add .codex/hooks/post_tool_use.py tests/test_post_tool_use.py
git commit -m "feat: PostToolUse リマインダー hook を追加(ノート3分未更新で記録・検索ルールを想起)"
```

---

### Task 2: pre_compact.py のフェイルオープン化(TDD)

**Files:**
- Modify: `.codex/hooks/pre_compact.py`
- Test: `tests/test_pre_compact.py`

**Interfaces:**
- Consumes: なし
- Produces: 不正 payload でも exit 0 で沈黙する `pre_compact.py`

- [ ] **Step 1: 失敗するテストを追加する**

`tests/test_pre_compact.py` の末尾(`if __name__` ブロックの直前)に次の関数を追加する:

```python
def test_malformed_stdin_silent() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp) / "proj"
        cwd.mkdir()
        proc = subprocess.run(
            [sys.executable, str(HOOK)],
            input="not json",
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip() == "", proc.stdout
```

- [ ] **Step 2: テストを実行して FAIL を確認する**

Run: `python3 tests/test_pre_compact.py`
Expected: `test_malformed_stdin_silent` で失敗(現行実装は `json.load` が例外を投げ、returncode が 0 でない)。他のテストは PASS。

- [ ] **Step 3: pre_compact.py をフェイルオープン化する**

`.codex/hooks/pre_compact.py` の `main()` を次の内容に置き換える(docstring に 1 行追記、本体を try/except で包む。それ以外は不変):

```python
def main() -> int:
    try:
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
    except Exception:
        return 0
    return 0
```

docstring 末尾に追記する 1 行: 「例外時は常に exit 0(compaction をブロックしない)。」

- [ ] **Step 4: テストを実行して全件 PASS を確認する**

Run: `python3 tests/test_pre_compact.py`
Expected: 5 テストすべて PASS、`all tests passed`

- [ ] **Step 5: コミット**

```bash
git add .codex/hooks/pre_compact.py tests/test_pre_compact.py
git commit -m "fix: pre_compact.py をフェイルオープン化(不正 payload で compaction を妨げない)"
```

---

### Task 3: hooks.json 登録と AGENTS.md 改訂

**Files:**
- Modify: `.codex/hooks.json`
- Modify: `AGENTS.md`

**Interfaces:**
- Consumes: Task 1 の `.codex/hooks/post_tool_use.py`
- Produces: PostToolUse が登録された hooks.json(Task 4 のドキュメントがこの構成を記述する)

- [ ] **Step 1: hooks.json に PostToolUse を登録する**

`.codex/hooks.json` 全体を次の内容に置き換える(matcher は一次資料の例示名を起点とした暫定値。実機 E2E で実ツール名を確認して確定する — spec の決定事項):

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
    ],
    "PostToolUse": [
      {
        "matcher": "Bash|apply_patch",
        "hooks": [
          { "type": "command", "command": "python3 .codex/hooks/post_tool_use.py" }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: AGENTS.md を書き換える**

`AGENTS.md` 全体を次の内容に置き換える(記録トリガーの行動境界化・5 事象の内容ガイド化・検索の相乗り。ノート発見・index 確認・二部構成・再開時・完了時は従来どおり):

```markdown
# AGENTS.md

## 推論の外部化

- タスク開始時に `working-notes/` を確認する。担当タスクのノート
  `working-notes/<topic>.md` があればそれを読んで再開し、なければ作成する
  (`<topic>` は短いケバブケース)。
  他タスクのノートは読んでよいが、編集しない。
- タスク開始時に `docs/memory/index.md` で関連カテゴリを確認する。
- コマンド・テスト・検証を実行して結果を確認した直後、その時点の推論を
  担当タスクのノートに記録する。タスクの大小を問わない。記録するのは
  行動ログではなく推論: 計画 / 仮説と検証結果(予想と合っていたか)/
  発見 / 判断とその理由(採らなかった案を含む)/ 失敗から得た知識。
- ノートに記録するとき、同じトピックのキーワードで `docs/memory/` を
  grep し、関連する記憶があれば読む。未知の領域・予想外の結果に直面した
  ときも同様に grep する。
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

- [ ] **Step 3: 検証する**

Run: `python3 -m json.tool .codex/hooks.json >/dev/null && echo "JSON OK" && grep -c "docs/memory" AGENTS.md`
Expected: `JSON OK`、grep は 4(index 確認 1 行・記録時 grep 1 行・完了時統合 2 行)。

- [ ] **Step 4: コミット**

```bash
git add .codex/hooks.json AGENTS.md
git commit -m "feat: PostToolUse hook を登録し、記録・検索ルールを行動境界アンカーへ改訂"
```

---

### Task 4: ドキュメント追従と全体検証

**Files:**
- Modify: `README.md`
- Modify: `docs/state-lifecycle.md`

**Interfaces:**
- Consumes: Task 1〜3 の最終構成(hook 3 本 + リマインダー + 新ルール)
- Produces: なし(最終タスク)

- [ ] **Step 1: README.md を追従させる**

以下の置換・追記をすべて適用する(old テキストが完全一致しない場合は類似表現を探して同趣旨に直し、報告に記載):

1. 冒頭段落(hook の役割の列挙): 「hook は推論を生成するのではなく、compaction 前の生ログ退避と compaction 発生の通知を担当します」→「hook は推論を生成するのではなく、compaction 前の生ログ退避、compaction 発生の通知、ノートが古いままのときのルール想起(リマインダー)を担当します」
2. 導入ファイル構成の tree(`.codex/hooks/` 配下): `post_compact.py` の行の下に `post_tool_use.py` を追加
3. 手順 1 の cp コマンド群: `cp "$SOURCE/.codex/hooks/post_compact.py" ...` の行の直後に次を追加:

   ```bash
   cp "$SOURCE/.codex/hooks/post_tool_use.py" "$TARGET/.codex/hooks/post_tool_use.py"
   ```

4. 手順 1 のマージ注記: 「`PreCompact` と `PostCompact` の登録を既存設定へマージしてください」→「`PreCompact`・`PostCompact`・`PostToolUse` の登録を既存設定へマージしてください」
5. 仕組み表: 「| 平時 | `AGENTS.md` | …」の行の下に次の行を追加:

   ```markdown
   | 平時(補強) | `post_tool_use.py` | ノートが 3 分更新されないままツール実行が続くと、記録・検索ルールの想起を注入する |
   ```

6. 仕組み表直後の段落末尾に次の 1 文を追加: 「リマインダーは全セッション共有の mtime 判定による補助であり、記録の主体はあくまで AGENTS.md ルールです。」
7. テスト節のコマンドブロックに `python3 tests/test_post_tool_use.py` を追加し、直後の説明文を「テストはスナップショット作成とローテーション、鮮度警告を出さないこと、transcript 不在時の no-op、リマインダーの発火条件(ノート鮮度・クールダウン)、不正 payload での沈黙を確認します。」に置き換える
8. 詳細資料の一覧に「[記録・検索ルールの発火保証の設計](docs/superpowers/specs/2026-08-05-rule-firing-reinforcement-design.md)」を追加

- [ ] **Step 2: docs/state-lifecycle.md を追従させる**

以下の置換をすべて適用する:

1. 冒頭の設計参照文に「[記録・検索ルールの発火保証の設計](superpowers/specs/2026-08-05-rule-firing-reinforcement-design.md)」を追加
2. フロー図の「平時の作業」行: 「│ AGENTS.md: 判断・仮説・発見を発生時点で担当ノートに記録する」→「│ AGENTS.md: 結果確認の直後に担当ノートへ記録する(PostToolUse が補強)」
3. 2 節全体を次の内容に置き換える:

   ```markdown
   ## 2. 平時は結果を確認した直後に記録する

   作業中の主な保存機構は hook ではなく、`AGENTS.md` の「推論の外部化」ルールです。
   Codex は、コマンド・テスト・検証を実行して結果を確認した直後に、その時点の推論を
   担当タスクのノートへ記録します。記録するのはコマンドの羅列ではなく、計画、仮説と
   検証結果(予想と合っていたか)、発見、判断とその理由、失敗から得た知識です。

   ノートに記録するときは、同じトピックのキーワードで `docs/memory/` を grep し、
   関連する過去の記憶があれば読みます。未知の領域や予想外の結果に直面したときも
   同様です。

   - 冒頭の「現在の状態と次の一手」は、常に最新状態へ上書きする
   - それ以降の「推論の記録」は、判断の経緯が失われないよう追記する

   この平時の記録が主防御です。さらに補助層として、`PostToolUse` に登録された
   `.codex/hooks/post_tool_use.py` が、ノートが 3 分を超えて更新されないまま
   ツール実行が続いたとき、記録と検索のルールを思い出させる短いリマインダーを
   コンテキストへ注入します(再注入は 3 分のクールダウン付き。ノートを更新すれば
   静かになります)。リマインダーは全セッション共有の mtime 判定による補助であり、
   誤って鳴らなくても記録の主体であるルールが働く限り状態は保たれます。
   ```

4. 4 節の責任分担表: `pre_compact.py` の行の下に次の行を追加:

   ```markdown
   | `post_tool_use.py` | ノート未更新時のルール想起の注入 | ノートの読み書き、推論の生成 |
   ```

- [ ] **Step 3: 全体検証を実行する**

```bash
python3 tests/test_post_tool_use.py
python3 tests/test_pre_compact.py
python3 -m json.tool .codex/hooks.json >/dev/null && echo "JSON OK"
grep -rn "post_tool_use" README.md docs/state-lifecycle.md .codex/hooks.json | wc -l
```

Expected: 両テスト `all tests passed`、`JSON OK`、grep は 5 件以上(README 2+・state-lifecycle 2・hooks.json 1)。

- [ ] **Step 4: コミット**

```bash
git add README.md docs/state-lifecycle.md
git commit -m "docs: リマインダー hook と行動境界アンカーを README / state-lifecycle に反映"
```
