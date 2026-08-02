# フェーズ1: Codex CLI 状態外部化 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 設計書 `docs/superpowers/specs/2026-08-01-state-externalization-design.md` のフェーズ1(Codex CLI 対応)を実装する — AGENTS.md ルール、OKF worklog バンドル、PreCompact/PostCompact/SessionStart hook。

**Architecture:** 推論の記録は AGENTS.md ルール(プロンプト層)が担い、hook は決定論的処理のみ行う。PreCompact = トランスクリプトのスナップショット+ノート鮮度警告、PostCompact = ユーザー通知、SessionStart = ノート冒頭の状態セクションをコンテキスト注入。hook はプロジェクト層 `.codex/hooks.json` に登録する。

**Tech Stack:** Python 3(stdlib のみ・依存なし)、Codex CLI hooks(hooks.json)、Markdown + YAML frontmatter(OKF v0.2)。

## Global Constraints

- ドキュメント・メッセージはすべて日本語(コード識別子は英語)。
- AGENTS.md のルール文は設計書 1-1 節のブロックを一言一句そのまま使う(勝手に要約しない)。
- hook スクリプトは Python 3 stdlib のみ。外部依存(uv 含む)を追加しない。
- hook は compaction をブロックしない(`decision`/`continue: false` を出力しない)。
- スナップショット保持は直近 10 件、鮮度警告の閾値は 30 分(設計書 1-3 節)。
- コミットは現在のブランチ `feat/state-externalization-design` に行う。`main` に直接コミットしない。
- コミットメッセージ末尾: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`

## ファイル構成

| パス | 責務 |
|---|---|
| `AGENTS.md` | Codex への行動ルール(推論の外部化)。知識は書かない |
| `.gitignore` | `working-notes.md` と `.harness/` を除外 |
| `docs/worklog/index.md` | OKF バンドルの一覧(段階的開示)+ エントリ書式テンプレート |
| `.codex/hooks.json` | 3 イベントの hook 登録 |
| `.codex/hooks/pre_compact.py` | スナップショット保存・ローテーション・鮮度警告 |
| `.codex/hooks/post_compact.py` | compaction 発生のユーザー通知 |
| `.codex/hooks/session_start.py` | ノート冒頭の状態セクションを stdout(=コンテキスト)へ |
| `tests/test_pre_compact.py` | pre_compact の stdlib 単体テスト(subprocess 実行) |
| `tests/test_session_start.py` | session_start の stdlib 単体テスト(subprocess 実行) |

---

### Task 1: AGENTS.md と .gitignore

**Files:**
- Create: `AGENTS.md`
- Create: `.gitignore`

**Interfaces:**
- Produces: `working-notes.md`(リポジトリ直下・git 管理外)という規約パス。`docs/worklog/index.md` への参照。後続タスクはこのパス規約に従う。

- [ ] **Step 1: AGENTS.md を作成**

```markdown
# AGENTS.md

## 推論の外部化

- 次のいずれかが起きたら、その時点でリポジトリ直下の `working-notes.md` に
  記録する。タスクの大小を問わない:
  - 複数の選択肢から選んだ 1 つとその理由(採らなかった案とそれぞれの理由を記載)
  - 仮説を立てた、または検証して結果が出た
  - 予想と異なる結果・エラーに遭遇した
  - 外部調査(ドキュメント・Web・コード読解)で事実を確認した
  - 計画・方針を変更した
- 記録するのは行動ログではなく推論: 計画 / 仮説と検証結果 / 発見 / 判断とその理由 / 失敗から得た知識。
- ノートは二部構成を保つ: 冒頭の「現在の状態と次の一手」は常に上書きして簡潔に
  最新化する(次の判断に必要な状態)。それ以降の推論の記録は追記する。
- 作業再開時・compaction 後は、続きを始める前に `working-notes.md` を読む。過去タスクの経緯は `docs/worklog/index.md` から辿る。
- タスク完了時、ノートを OKF 形式で `docs/worklog/YYYY-MM-DD-<topic>.md` へ移し、`docs/worklog/index.md` に 1 行追記する。
```

- [ ] **Step 2: .gitignore を作成**

```gitignore
working-notes.md
.harness/
```

- [ ] **Step 3: 検証**

Run: `grep -c '^- ' AGENTS.md && grep -q 'working-notes.md' .gitignore && grep -q '.harness/' .gitignore && echo OK`
Expected: 箇条書き数が表示され `OK` が出る

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md .gitignore
git commit -m "feat: AGENTS.md に推論の外部化ルールを追加

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: worklog OKF バンドル雛形

**Files:**
- Create: `docs/worklog/index.md`

**Interfaces:**
- Consumes: Task 1 の規約(タスク完了時に `docs/worklog/YYYY-MM-DD-<topic>.md` へ移す)。
- Produces: worklog エントリの OKF 書式(frontmatter: `type: Worklog` / `title` / `description` / `tags` / `timestamp` / `actor`、本文見出し 5 項目)。

- [ ] **Step 1: index.md を作成**

```markdown
---
type: Index
title: Worklog
description: タスクごとの推論の記録(OKF v0.2 バンドル)。1 タスク = 1 ファイル。
timestamp: 2026-08-02T00:00:00Z
---

# Worklog

タスク完了時に `working-notes.md` から移したエントリの一覧。新しいものを上に追記する。

## エントリ一覧

(まだエントリはない)

## エントリの書式

ファイル名: `YYYY-MM-DD-<topic>.md`。frontmatter の必須は `type` のみ、他は推奨。

```text
---
type: Worklog
title: <タスクの短い題>
description: <1 行要約>
tags: [<領域タグ>]
timestamp: <ISO 8601 更新日時>
actor: <書き手。エージェントは <producer>/<version>、人は human:<id>>
---

# 計画
# 仮説と検証結果
# 発見
# 判断とその理由
# 失敗から得た知識
```

空の見出しは削ってよい。関連する過去エントリへは通常の Markdown リンクで参照する。
```

- [ ] **Step 2: 検証**

Run: `head -1 docs/worklog/index.md | grep -q -- --- && grep -q 'type: Worklog' docs/worklog/index.md && echo OK`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add docs/worklog/index.md
git commit -m "feat: worklog を OKF バンドルとして初期化

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: PreCompact / PostCompact hook スクリプト

**Files:**
- Create: `.codex/hooks/pre_compact.py`
- Create: `.codex/hooks/post_compact.py`
- Test: `tests/test_pre_compact.py`

**Interfaces:**
- Consumes: Codex hook payload(stdin JSON。使用フィールド: `cwd`, `transcript_path`, `turn_id`)。
- Produces: `.harness/compaction-snapshots/<stamp>-<turn>.jsonl`(直近 10 件)、鮮度警告時の stdout JSON `{"systemMessage": "..."}`。Task 5 が `.codex/hooks/pre_compact.py` / `post_compact.py` のパスで登録する。

- [ ] **Step 1: 失敗するテストを書く**

```python
#!/usr/bin/env python3
"""tests/test_pre_compact.py — stdlib のみ。python3 tests/test_pre_compact.py で実行。"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / ".codex" / "hooks" / "pre_compact.py"


def run_hook(payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=30,
    )


def make_workdir(tmp: str) -> tuple[Path, Path]:
    cwd = Path(tmp) / "proj"
    cwd.mkdir()
    transcript = Path(tmp) / "transcript.jsonl"
    transcript.write_text('{"role":"user"}\n', encoding="utf-8")
    return cwd, transcript


def test_snapshot_created() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd, transcript = make_workdir(tmp)
        proc = run_hook({"cwd": str(cwd), "transcript_path": str(transcript), "turn_id": "turn_abc12345"})
        assert proc.returncode == 0, proc.stderr
        snaps = list((cwd / ".harness" / "compaction-snapshots").glob("*.jsonl"))
        assert len(snaps) == 1, snaps
        assert snaps[0].read_text(encoding="utf-8") == '{"role":"user"}\n'


def test_rotation_keeps_10() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd, transcript = make_workdir(tmp)
        snap_dir = cwd / ".harness" / "compaction-snapshots"
        snap_dir.mkdir(parents=True)
        for i in range(12):
            f = snap_dir / f"20250101-0000{i:02d}-old.jsonl"
            f.write_text("x", encoding="utf-8")
        proc = run_hook({"cwd": str(cwd), "transcript_path": str(transcript), "turn_id": "t"})
        assert proc.returncode == 0, proc.stderr
        assert len(list(snap_dir.glob("*.jsonl"))) == 10


def test_stale_notes_warns() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd, transcript = make_workdir(tmp)
        notes = cwd / "working-notes.md"
        notes.write_text("## 現在の状態と次の一手\n", encoding="utf-8")
        old = time.time() - 3600
        os.utime(notes, (old, old))
        proc = run_hook({"cwd": str(cwd), "transcript_path": str(transcript), "turn_id": "t"})
        out = json.loads(proc.stdout)
        assert "systemMessage" in out, proc.stdout


def test_fresh_notes_silent() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd, transcript = make_workdir(tmp)
        (cwd / "working-notes.md").write_text("## 現在の状態と次の一手\n", encoding="utf-8")
        proc = run_hook({"cwd": str(cwd), "transcript_path": str(transcript), "turn_id": "t"})
        assert proc.stdout.strip() == "", proc.stdout


def test_missing_transcript_is_noop() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp) / "proj"
        cwd.mkdir()
        proc = run_hook({"cwd": str(cwd), "transcript_path": str(Path(tmp) / "none.jsonl"), "turn_id": "t"})
        assert proc.returncode == 0, proc.stderr


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all tests passed")
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 tests/test_pre_compact.py`
Expected: FAIL(`.codex/hooks/pre_compact.py` が存在しないため `FileNotFoundError` 等)

- [ ] **Step 3: pre_compact.py を実装**

```python
#!/usr/bin/env python3
"""Codex PreCompact hook: transcript のスナップショット保存とノート鮮度の警告。

設計: docs/superpowers/specs/2026-08-01-state-externalization-design.md 1-3節。
compaction はブロックしない。モデルへの注入は行わない(仕様上不可)。
"""
import json
import shutil
import sys
import time
from pathlib import Path

KEEP = 10
STALE_SECONDS = 30 * 60


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

    notes = cwd / "working-notes.md"
    if notes.is_file() and time.time() - notes.stat().st_mtime > STALE_SECONDS:
        print(json.dumps({
            "systemMessage": "working-notes.md が30分以上更新されないまま compaction が実行されます。状態の取りこぼしに注意してください。"
        }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 tests/test_pre_compact.py`
Expected: `PASS` ×5 と `all tests passed`

- [ ] **Step 5: post_compact.py を実装**(通知のみ・テストは目視で足りる)

```python
#!/usr/bin/env python3
"""Codex PostCompact hook: compaction 発生をユーザーへ通知する。"""
import json
import sys


def main() -> int:
    sys.stdin.read()  # payload は使わないが読み切る
    print(json.dumps({
        "systemMessage": "compaction が実行されました。エージェントは working-notes.md を読み直して状態を確認します。"
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: post_compact.py の動作確認**

Run: `echo '{}' | python3 .codex/hooks/post_compact.py`
Expected: `{"systemMessage": "compaction が実行されました。..."}` が 1 行出る

- [ ] **Step 7: Commit**

```bash
git add .codex/hooks/pre_compact.py .codex/hooks/post_compact.py tests/test_pre_compact.py
git commit -m "feat: PreCompact/PostCompact hook を実装(スナップショット・鮮度警告・通知)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: SessionStart hook スクリプト

**Files:**
- Create: `.codex/hooks/session_start.py`
- Test: `tests/test_session_start.py`

**Interfaces:**
- Consumes: Codex hook payload(stdin JSON。使用フィールド: `cwd`)。`working-notes.md` の二部構成(冒頭 `## 現在の状態と次の一手`)。
- Produces: stdout のプレーンテキスト(Codex が additionalContext としてコンテキストへ注入。既定上限 2,500 トークンのため状態セクションのみ)。Task 5 が `.codex/hooks/session_start.py` のパスで登録する。

- [ ] **Step 1: 失敗するテストを書く**

```python
#!/usr/bin/env python3
"""tests/test_session_start.py — stdlib のみ。python3 tests/test_session_start.py で実行。"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / ".codex" / "hooks" / "session_start.py"

NOTES = """## 現在の状態と次の一手

- 状態: Task 3 まで完了
- 次の一手: Task 4 のテストを書く

## 推論の記録

- 2026-08-02 選択: A案を採用。理由: ...
"""


def run_hook(cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"cwd": str(cwd)}),
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_no_notes_is_silent() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        proc = run_hook(Path(tmp))
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip() == "", proc.stdout


def test_state_section_injected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "working-notes.md").write_text(NOTES, encoding="utf-8")
        proc = run_hook(Path(tmp))
        assert "現在の状態と次の一手" in proc.stdout
        assert "Task 4 のテストを書く" in proc.stdout
        # 推論の記録(追記部)は注入しない
        assert "A案を採用" not in proc.stdout
        # 全文への誘導がある
        assert "working-notes.md" in proc.stdout


def test_notes_without_state_section_fallback() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "working-notes.md").write_text("メモだけがある\n", encoding="utf-8")
        proc = run_hook(Path(tmp))
        assert "working-notes.md" in proc.stdout
        assert "メモだけがある" in proc.stdout


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all tests passed")
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 tests/test_session_start.py`
Expected: FAIL(hook 未実装)

- [ ] **Step 3: session_start.py を実装**

```python
#!/usr/bin/env python3
"""Codex SessionStart hook: working-notes.md 冒頭の状態セクションをコンテキストへ注入する。

stdout が additionalContext として注入される(既定上限 2,500 トークン)ため、
「現在の状態と次の一手」セクションのみを出し、全文はファイル参照へ誘導する。
設計: docs/superpowers/specs/2026-08-01-state-externalization-design.md 1-4節。
"""
import json
import sys
from pathlib import Path

STATE_HEADING = "## 現在の状態と次の一手"
FALLBACK_LINES = 40


def extract_state_section(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    in_state = False
    for line in lines:
        if line.startswith("## "):
            if in_state:
                break
            in_state = line.strip() == STATE_HEADING
            if in_state:
                out.append(line)
            continue
        if in_state:
            out.append(line)
    if out:
        return "\n".join(out).strip()
    return "\n".join(lines[:FALLBACK_LINES]).strip()


def main() -> int:
    payload = json.load(sys.stdin)
    notes = Path(payload.get("cwd") or ".") / "working-notes.md"
    if not notes.is_file():
        return 0
    section = extract_state_section(notes.read_text(encoding="utf-8"))
    if not section:
        return 0
    print("前回までの作業ノート(working-notes.md より):")
    print(section)
    print()
    print("続きを始める前に working-notes.md 全文を読んで状態を確認すること。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 tests/test_session_start.py`
Expected: `PASS` ×3 と `all tests passed`

- [ ] **Step 5: Commit**

```bash
git add .codex/hooks/session_start.py tests/test_session_start.py
git commit -m "feat: SessionStart hook を実装(状態セクションのコンテキスト注入)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: hooks.json 登録

**Files:**
- Create: `.codex/hooks.json`

**Interfaces:**
- Consumes: Task 3・4 のスクリプトパス(`.codex/hooks/*.py`)。
- Produces: プロジェクト層の hook 登録。Codex がこのプロジェクトを trusted として扱っている必要がある。

- [ ] **Step 1: hooks.json を作成**

```json
{
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
  "SessionStart": [
    {
      "matcher": "startup|resume",
      "hooks": [
        { "type": "command", "command": "python3 .codex/hooks/session_start.py" }
      ]
    }
  ]
}
```

- [ ] **Step 2: JSON として妥当か検証**

Run: `python3 -m json.tool .codex/hooks.json > /dev/null && echo OK`
Expected: `OK`

- [ ] **Step 3: スキーマの実機確認(スポットチェック)**

`codex` をこのリポジトリで起動し、起動時に hooks.json のパースエラー・警告が出ないことを確認する。エラーが出た場合は一次資料
<https://developers.openai.com/codex/hooks> の設定例と突き合わせてフィールド名を修正する(このステップが本計画で唯一、実機仕様に合わせた調整を許す箇所)。

- [ ] **Step 4: Commit**

```bash
git add .codex/hooks.json
git commit -m "feat: Codex hooks.json に 3 イベントを登録

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: E2E 検証(実機・手動)

**Files:** なし(検証のみ。結果は working-notes.md に記録し、完了時に worklog 化する)

設計書「検証方法」の (a)〜(e) を Codex CLI で実際に確認する。**実行せずに「動くはず」としない。**

- [ ] **Step 1: 記録トリガーの確認 (a)**

このリポジトリで `codex` を起動し、小さなタスク(例: 「README.md の草案を作って。構成は 2 案比較して選んで」)を依頼する。
Expected: 選択・判断が発生した時点で `working-notes.md` が作成され、二部構成(冒頭に状態セクション)で記録される。

- [ ] **Step 2: SessionStart 注入の確認 (c)**

`working-notes.md` がある状態で `codex` を再起動し、「今の作業状態を説明して」と聞く。
Expected: ノートを読んだ内容(状態セクション)を踏まえた回答が返る。hook の発火は Codex の UI / ログでも確認する。

- [ ] **Step 3: PreCompact / PostCompact の確認 (b)**

セッション内で `/compact` を手動実行する。
Expected: `.harness/compaction-snapshots/` に `.jsonl` が 1 件でき、PostCompact の systemMessage が UI に表示される。`working-notes.md` の mtime を `touch -d '1 hour ago' working-notes.md` で古くしてから再度 `/compact` し、鮮度警告の systemMessage が出ることも確認する。

- [ ] **Step 4: 状態セクションの上書き確認 (d)**

タスクを続行させ、`working-notes.md` 冒頭の「現在の状態と次の一手」が追記ではなく上書きで最新化されていることを目視確認する。

- [ ] **Step 5: worklog 化の確認 (e)**

タスクを完了させる。
Expected: `docs/worklog/2026-MM-DD-<topic>.md` が OKF frontmatter 付きで作られ、`docs/worklog/index.md` に 1 行追記され、`working-notes.md` が消えている(移動)。

- [ ] **Step 6: 検証結果を worklog へ記録して Commit**

E2E で観察した事実(うまく発動しなかったルールがあればそれも)を `docs/worklog/2026-MM-DD-phase1-e2e.md` に OKF 形式で記録する。

```bash
git add docs/worklog/
git commit -m "docs: フェーズ1 E2E 検証結果を worklog に記録

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```
