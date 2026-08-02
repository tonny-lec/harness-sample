# Codex 状態外部化ハーネス

Codex CLI の compaction やセッション再開をまたいで、作業の目的・現在地・判断理由を
リポジトリ内のファイルから復元できるようにする最小構成のハーネスです。

会話履歴だけに状態を預けず、作業中の要点を `working-notes.md`、完了したタスクの知識を
`docs/worklog/` に残します。hook は推論を生成するのではなく、compaction 前の退避、
compaction 発生の通知、再開時の状態注入を担当します。

## 対応状況

| 項目 | 状態 |
|---|---|
| Codex CLI 向けの記録ルール | 実装済み |
| PreCompact / PostCompact / SessionStart hook | 実装済み |
| hook の単体テスト | 実装済み |
| Codex CLI 実機での一連の E2E 検証 | 完了(5項目中4件成功、発見されたルール欠陥は修正済み — docs/worklog/2026-08-02-phase1-e2e.md) |
| Claude Code 対応 | 未実装（フェーズ2） |

## 前提条件

- Codex CLI
- Python 3（hook は標準ライブラリだけを使用）
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
│       ├── post_compact.py
│       └── session_start.py
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
cp "$SOURCE/.codex/hooks/session_start.py" "$TARGET/.codex/hooks/session_start.py"
```

既存の `.codex/hooks.json` がある場合は上書きせず、`PreCompact`、`PostCompact`、
`SessionStart` の登録を既存設定へマージしてください。

### 2. 記録ルールを AGENTS.md へ追加する

このリポジトリの [AGENTS.md](AGENTS.md) にある「推論の外部化」セクションを、導入先の
`AGENTS.md` へ追加します。既存の指示は残してください。

このルールが次を担当します。

- 選択、仮説、検証結果、発見、計画変更を発生時点で記録する
- `working-notes.md` 冒頭の「現在の状態と次の一手」を最新に保つ
- 作業再開時と compaction 後にノートを読み直す
- タスク完了時に記録を `docs/worklog/` へ移す

### 3. 一時ファイルを Git 管理外にする

導入先の `.gitignore` に次を追加します。

```gitignore
working-notes.md
.harness/
```

`working-notes.md` は作業中の状態、`.harness/compaction-snapshots/` は compaction 前の
生ログ退避先です。完了後に残す知識は `docs/worklog/` へ移して Git 管理します。

### 4. worklog を初期化する

導入先に `docs/worklog/index.md` を作り、このリポジトリの
[worklog index](docs/worklog/index.md) にある frontmatter とエントリ書式を使います。
このサンプル固有の「エントリ一覧」はコピーせず、導入先の記録だけを並べてください。

### 5. 設定を確認する

導入先のルートで次を実行します。

```bash
python3 -m json.tool .codex/hooks.json >/dev/null
printf '{"cwd":"."}\n' | python3 .codex/hooks/session_start.py
```

`working-notes.md` がまだなければ、2つ目のコマンドは何も表示せず正常終了します。
次の最小ノートを作って再実行すると、「現在の状態と次の一手」だけが出力されます。

```markdown
## 現在の状態と次の一手

- 目的: <このタスクで達成すること>
- 状態: <いま分かっていること>
- 次の一手: <次に行う判断または作業>

## 推論の記録
```

最後に、そのプロジェクトを作業ディレクトリとして Codex CLI を起動し、hook 設定の
読み込みエラーや警告がないことを確認してください。

## 普段の使い方

1. Codex と通常どおりタスクを進めます。
2. AGENTS.md の条件に該当する判断や発見が起きると、Codex が `working-notes.md` を更新します。
3. compaction 前には transcript が `.harness/compaction-snapshots/` へ退避されます。
4. セッション再開時には、`working-notes.md` 冒頭の状態がコンテキストへ注入されます。
5. タスク完了時には、ノートを `docs/worklog/YYYY-MM-DD-<topic>.md` へ移し、index に追加します。

重要なのは、hook 自体は計画や判断理由を書き出さないことです。推論の外部化は
AGENTS.md の記録ルールが主に担い、hook は取りこぼしを減らす補助層として働きます。

## 仕組み

| 層 | 担当 | 動作 |
|---|---|---|
| 平時 | `AGENTS.md` | 判断・仮説・発見と、次の判断に必要な状態を随時記録する |
| compaction 前 | `pre_compact.py` | transcript を退避し、ノートが30分以上古ければ警告する |
| compaction 後 | `post_compact.py` | compaction の発生とノート再確認を通知する |
| 起動・再開時 | `session_start.py` | ノート冒頭の状態セクションだけをコンテキストへ注入する |
| タスク完了後 | `docs/worklog/` | 蒸留した推論を OKF 形式の Markdown として保持する |

スナップショットは直近10件だけを保持するコールドストレージです。通常の復元には
`working-notes.md` と worklog を使い、生ログは取りこぼしを調べる最終手段とします。

## このリポジトリでのテスト

```bash
python3 tests/test_pre_compact.py
python3 tests/test_session_start.py
```

テストはスナップショット作成とローテーション、ノート鮮度警告、状態セクション抽出、
ノート不在時の no-op を確認します。Codex CLI 上での hook 発火とタスク完了までの一連の
挙動は、実機 E2E で確認済みです(docs/worklog/2026-08-02-phase1-e2e.md)。

## 制約

- Codex の PostCompact hook から状態を直接コンテキスト注入することはできません。
  compaction 後の AGENTS.md ルールと、次回起動・再開時の SessionStart で補います。
- transcript のスナップショットには会話内容がそのまま含まれます。`.harness/` を
  Git 管理外のままにし、共有やバックアップ時の取り扱いに注意してください。
- 現在の実装は Codex CLI 向けです。設計書にある Claude Code 対応はまだありません。
- 本ハーネスはモデルの private reasoning を保存するものではありません。後続判断に
  必要な計画、仮説、発見、判断理由、失敗から得た知識を明示的に外部化します。

## 詳細資料

- [状態外部化の設計](docs/superpowers/specs/2026-08-01-state-externalization-design.md)
- [フェーズ1の実装計画](docs/superpowers/plans/2026-08-02-phase1-codex-state-externalization.md)
- [worklog index](docs/worklog/index.md)
