# Codex 状態外部化ハーネス

Codex CLI の compaction やセッション再開をまたいで、作業の目的・現在地・判断理由を
リポジトリ内のファイルから復元できるようにする最小構成のハーネスです。

会話履歴だけに状態を預けず、作業中の要点をタスクごとの `working-notes/<topic>.md`、
完了したタスクの知識をカテゴリ別の `docs/memory/` の記憶に統合します。複数セッションを同じディレクトリで
並行させても、タスクが異なればノートは衝突しません。hook は推論を生成するのではなく、
compaction 前の生ログ退避、compaction 発生の通知、ノートが古いままのときのルール想起
(リマインダー)を担当します。

## 対応状況

| 項目 | 状態 |
|---|---|
| Codex CLI 向けの記録ルール(複数セッション対応) | 実装済み |
| PreCompact / PostCompact hook | 実装済み |
| hook の単体テスト | 実装済み |
| Codex CLI 実機での一連の E2E 検証 | 単一セッション運用・複数セッション並行とも完了(docs/memory/harness/e2e-verification.md) |
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
│       ├── post_compact.py
│       └── post_tool_use.py
└── docs/
    └── memory/
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
cp "$SOURCE/.codex/hooks/post_tool_use.py" "$TARGET/.codex/hooks/post_tool_use.py"
```

既存の `.codex/hooks.json` がある場合は上書きせず、`PreCompact`・`PostCompact`・
`PostToolUse` の登録を既存設定へマージしてください。

### 2. 記録ルールを AGENTS.md へ追加する

このリポジトリの [AGENTS.md](AGENTS.md) にある「推論の外部化」セクションを、導入先の
`AGENTS.md` へ追加します。既存の指示は残してください。

このルールが次を担当します。

- タスク開始時・技術判断の前に `docs/memory/` から関連する記憶を検索して読む
- タスク開始時に `working-notes/` から担当タスクのノートを見つける(なければ作る)
- コマンド・テスト・検証の結果を確認した直後に、その時点の推論(計画・仮説と
  検証結果・発見・判断とその理由・失敗から得た知識)を記録する
- ノートに記録するとき、同じトピックのキーワードで `docs/memory/` を grep し、
  関連する記憶があれば読む
- ノート冒頭の「現在の状態と次の一手」を最新に保つ
- 作業再開時と compaction 後に担当ノートを読み直す
- タスク完了時に知見を `docs/memory/` の記憶へ統合する(同トピックがあれば更新)

### 3. 一時ファイルを Git 管理外にする

導入先の `.gitignore` に次を追加します。

```gitignore
working-notes.md
working-notes/
.harness/
```

`working-notes/` は進行中タスクの状態、`.harness/compaction-snapshots/` は compaction 前の
生ログ退避先です。完了後に残す知識は `docs/memory/` の記憶へ統合して Git 管理します。

以前の単一ファイル構成(`working-notes.md`)から移行する場合は、残っているファイルを
手動で `working-notes/<topic>.md` へ移してください。旧 `working-notes.md` の ignore 指定は、
移行が済むまでの誤コミットを防ぐ安全策として残しています。

### 4. memory を初期化する

導入先に `docs/memory/index.md` を作り、このリポジトリの
[memory index](docs/memory/index.md) にあるカテゴリ一覧と記憶の書式を使います。
このサンプル固有のカテゴリと記憶はコピーせず、導入先で生まれた記憶だけを
配置してください。

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
3. コマンド・テスト・検証の結果を確認した直後に、Codex が担当ノートを更新します。
4. compaction 前には transcript が `.harness/compaction-snapshots/` へ退避されます。
5. セッション再開時・compaction 後には、AGENTS.md のルールに従って担当ノートを読み直します。
6. タスク完了時には、担当ノートの知見を `docs/memory/<category>/<topic>.md` の記憶へ統合し(同トピックがあれば更新)、該当する index を更新します。

重要なのは、hook 自体は計画や判断理由を書き出さないことです。推論の外部化は
AGENTS.md の記録ルールが主に担い、hook は取りこぼしを減らす補助層として働きます。

## 仕組み

| 層 | 担当 | 動作 |
|---|---|---|
| 平時 | `AGENTS.md` | 担当ノートの発見・作成と、判断・仮説・発見・状態の随時記録 |
| 平時(補強) | `post_tool_use.py` | ノートが 3 分更新されないままツール実行が続くと、記録・検索ルールの想起を注入する |
| compaction 前 | `pre_compact.py` | transcript を退避する |
| compaction 後 | `post_compact.py` | compaction の発生とノート再確認を通知する |
| 起動・再開時 | `AGENTS.md` | 担当タスクのノートを読み直す |
| タスク完了後 | `docs/memory/` | 蒸留した推論をカテゴリ別の記憶として統合・保持する(OKF 形式) |

スナップショットは直近10件だけを保持するコールドストレージです。通常の復元には
担当タスクのノートと記憶(`docs/memory/`)を使い、生ログは取りこぼしを調べる最終手段とします。
リマインダーは全セッション共有の mtime 判定による補助であり、記録の主体はあくまで
AGENTS.md ルールです。

## このリポジトリでのテスト

```bash
python3 tests/test_pre_compact.py
python3 tests/test_post_tool_use.py
```

テストはスナップショット作成とローテーション、鮮度警告を出さないこと、transcript
不在時の no-op、リマインダーの発火条件(ノート鮮度・クールダウン)、不正 payload
での沈黙を確認します。単一セッション運用での hook 発火とタスク完了までの
一連の挙動は、実機 E2E で確認済みです(docs/memory/harness/e2e-verification.md)。

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
- [memory index](docs/memory/index.md)
- [worklog の記憶化の設計](docs/superpowers/specs/2026-08-04-memory-bundle-design.md)
- [記録・検索ルールの発火保証の設計](docs/superpowers/specs/2026-08-05-rule-firing-reinforcement-design.md)
