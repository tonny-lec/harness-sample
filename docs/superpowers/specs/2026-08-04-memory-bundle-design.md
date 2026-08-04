# 設計: worklog の記憶化(docs/memory/ バンドルへの再編)

日付: 2026-08-04
先行設計: [状態外部化の設計](2026-08-01-state-externalization-design.md)、
[working-notes 複数セッション対応の設計](2026-08-04-multi-session-working-notes-design.md)
一次資料: OKF v0.2 仕様
<https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf>(SPEC.md)

## 背景と課題

現在の `docs/worklog/` は「タスク完了ごとに日付付きファイルを追記する」記録型の構成に
なっている。しかし、この置き場の目的は作業ログを残すことではなく、**後続タスクが参照
できる記憶を育てる**ことにある。記録型の構成には次の問題がある。

- 同じトピックの知見がタスクのたびに別ファイルへ分散し、検索性と一覧性が落ちる
  (実例: 誤字チェックの知見が `2026-08-04-readme-typo-check.md` と
  `2026-08-04-state-lifecycle-typos.md` の 2 ファイルに割れている)。
- ファイル名の日付は知識の同一性と無関係であり、Concept ID(OKF ではパスが ID)を
  不安定にする。
- フラット構成のため、件数が増えると index の 1 行一覧だけでは領域ごとの俯瞰が
  できなくなる。

OKF v0.2 で確認済みの事実(一次資料より):

- Bundle は階層構造が前提で、各階層に予約ファイル `index.md`(段階的開示)を
  置ける。カテゴリフォルダは仕様に沿った構成である。
- Concept ID は「ファイルパスから `.md` を除いたもの」。日付なしの安定パスが
  リンク安定性の面でも推奨される(バンドルルート絶対パス `/dir/file.md` 形式)。
- 発見メカニズムは「type / tags でのフィルタ + index の段階的開示 + 任意の
  検索ツール」。**grep はまさに仕様が想定する消費方法**であり、専用ツールは不要。
- frontmatter は `type` のみ必須。信頼性・鮮度の語彙として
  `generated: {by, at}` / `verified` / `status` / `stale_after` が定義済み。
- 「Consumers MUST tolerate broken links」(壊れたリンクの許容)が規定されている。

## 決定事項

| 項目 | 決定 | 理由 |
|---|---|---|
| ディレクトリ名 | `docs/worklog/` → `docs/memory/` に改名 | 「記録ではなく記憶」というコンセプトを名前にも反映する。worklog という名前は日付追記型を想起させ、更新・統合型の運用と不一致 |
| ファイル名 | 日付を外し `docs/memory/<category>/<topic>.md` | 日付は知識の同一性と無関係。パス = Concept ID(OKF)を安定させる。更新日時は frontmatter `generated.at` が担う |
| 記憶の更新 | 同トピックの新しい知見は**既存ファイルを更新・統合**する(`generated.at` を最新化)。別ファイルを増やさない | 知識を 1 箇所に集約して熟成させる記憶モデル。経緯・履歴は git が担う |
| カテゴリ | 初期セット(harness / documentation / testing / policy)+ 合うものがなければエージェントが新設(新設時はルート index に追記) | 既存 8 件から導出した最小セット。固定リストは想定外領域のたびに人の判断が要り、完全自由は類義カテゴリの乱立を招く |
| index | ルート `index.md` = カテゴリ一覧(1 行説明付き)、各カテゴリ `index.md` = 記憶一覧(1 行要約付き) | OKF の段階的開示。エージェントはルート → カテゴリ → 個別ファイルの順に必要な分だけ読む |
| frontmatter | `type: Memory` に統一。`title` / `description` / `tags` は推奨。`timestamp` + `actor` を廃止し OKF v0.2 の `generated: {by, at}` に一本化 | v0.2 の語彙に準拠し検索面(フィルタ対象)を明確化する。actor 表記規約(`<producer>/<version>`, `human:<id>`)は `generated.by` にそのまま使う |
| 任意フィールド | `verified` / `status` / `stale_after` は書式ガイドに記載し、必要になった記憶にだけ使う(必須にしない) | 記憶の鮮度・信頼度の語彙は用意するが、全件必須は棚卸し運用の負担が現規模(8件)に過剰(YAGNI) |
| 本文見出し | 従来の 5 項目(計画 / 仮説と検証結果 / 発見 / 判断とその理由 / 失敗から得た知識)を推奨のまま維持。空は省略可。統合ファイルは知見単位の再構成を許容 | 記録すべき内容(推論 5 項目)は変わらない。統合時に時系列のまま連結すると記憶ではなく記録に戻るため、再構成を明示的に許す |
| 検索ルール | AGENTS.md に規定: タスク開始時にルート index を確認。作業中に技術判断・予想外の結果・未知の領域に直面したら、着手前に `docs/memory/` を grep(tags / title / description / 見出し)して関連記憶を読む | 「grep で検索」は OKF が想定する消費方法そのもの。検索スクリプトはエージェントの既存検索能力で足りるため作らない(YAGNI) |
| 完了時ルール | 「worklog へ移す」→「記憶へ統合する」に改訂: 同トピックの記憶を検索 → あれば更新、なければカテゴリを選んで新規(なければカテゴリ新設)。該当 index を更新し、working-note を削除 | 記憶の更新・統合原則をタスク完了フローに組み込む |
| 記憶間リンク | バンドルルート絶対パス(例: `/harness/e2e-verification.md`)を推奨 | OKF 推奨形式。ファイルのカテゴリ内移動に強い |
| 過去文書の扱い | 過去の spec / plan / 記憶本文中の `docs/worklog/` 参照は書き換えない(リンク切れを許容)。「現在」を記述する文書(README / state-lifecycle.md / AGENTS.md)のみ新パスへ追従 | 歴史的記録の改変を避ける。OKF の「壊れたリンクを許容せよ」規定に依拠 |
| hooks | 変更なし | 記憶の読み書きはすべて AGENTS.md ルール(エージェントの判断)であり、hook はセッションとタスクの対応を知り得ない(先行設計の判断を踏襲) |

## 移行マッピング

既存 8 件を次の 6 記憶に再編する。統合 2 組は「同トピック 1 ファイル」原則の適用。

```
docs/memory/
├── index.md                          # カテゴリ一覧
├── harness/
│   ├── index.md
│   └── e2e-verification.md          ← 2026-08-02-phase1-e2e + 2026-08-04-multi-session-e2e を統合
├── documentation/
│   ├── index.md
│   ├── readme-authoring.md          ← 2026-08-02-readme-draft
│   ├── explanatory-guides.md        ← 2026-08-02-state-lifecycle-guide
│   └── proofreading.md              ← 2026-08-04-readme-typo-check + 2026-08-04-state-lifecycle-typos を統合
├── testing/
│   ├── index.md
│   └── pre-compact-coverage.md      ← 2026-08-04-pre-compact-test-coverage
└── policy/
    ├── index.md
    └── superpowers-usage.md         ← 2026-08-02-disable-superpowers-for-repo
```

移行の要件:

- 元 8 件の知見(発見・判断とその理由・失敗から得た知識)が、いずれかの記憶に
  すべて含まれること(消失なし)。統合ファイルでは重複を除き、相反する知見は
  新しい方を採り古い方は「過去の判断」として文脈付きで残す。
- 各記憶の `generated.at` は元エントリの最新日時、`generated.by` は主たる書き手
  (統合時は最新版の書き手)とする。
- 移行後、`docs/worklog/` ディレクトリは削除する。

## frontmatter の書式

```yaml
---
type: Memory
title: <記憶の短い題>
description: <1 行要約>
tags: [<横断タグ>]
generated: { by: <actor>, at: <ISO 8601 最終更新日時> }
---
```

- `generated.by` の actor 表記は OKF §7 に従う: エージェントは
  `<producer>/<version>`(例: `claude-code/fable-5`)、人は `human:<id>`。
- 任意フィールド(必要になった記憶にだけ付ける):
  - `verified: {by, at}` またはそのリスト — 内容を検証した記録
  - `status: draft | stable | deprecated`(無指定は stable)
  - `stale_after: YYYY-MM-DD` — この日以降は要再確認という絶対日付

## AGENTS.md の新ルール文面

「推論の外部化」セクションの該当 2 箇所を次のように改訂する(他の箇条書きは不変)。

```markdown
- 作業再開時・compaction 後は、続きを始める前に担当タスクのノートを読む。
- タスク開始時に `docs/memory/index.md` で関連カテゴリを確認する。作業中に
  技術判断・予想外の結果・未知の領域に直面したら、着手前に `docs/memory/` を
  grep(tags / title / description / 見出し)して関連する記憶を読む。
- タスク完了時、担当タスクのノートの知見を `docs/memory/` の記憶へ統合する:
  同トピックの記憶があれば既存ファイルを更新して `generated.at` を最新化し、
  なければカテゴリを選んで `docs/memory/<category>/<topic>.md` を新規作成する
  (合うカテゴリがなければ新設し、ルート `index.md` にカテゴリを追記する)。
  該当カテゴリの `index.md` を更新し、ノートファイルを削除する。
  完了時はこの手順が「追記する」ルールより優先される。
```

(現行の「過去タスクの経緯は `docs/worklog/index.md` から辿る」の 1 文は
タスク開始時ルールに吸収して削除する。)

## 変更ファイル一覧

| ファイル | 変更 |
|---|---|
| `docs/memory/**` | 新設(ルート index + カテゴリ index 4 件 + 記憶 6 件。上記マッピングどおり) |
| `docs/worklog/**` | 削除(全 8 エントリ + index.md) |
| `AGENTS.md` | 検索ルール新設・完了時ルール改訂(上記文面) |
| `README.md` | worklog 言及(導入手順 4・普段の使い方・仕組み表・対応状況表・詳細資料)を memory 構成へ追従。記憶の書式・カテゴリ運用の説明に更新 |
| `docs/state-lifecycle.md` | 全体像の表・5 節(完了時)・障害時の復元順序を memory 構成へ追従 |
| 過去の spec / plan / 記憶本文 | 変更しない(`docs/worklog/` へのリンク切れは許容) |

hooks・tests は変更しない。

## エッジケースの扱い

- **カテゴリ選択に迷う記憶**: tags で横断分類できるため、フォルダはどちらか 1 つに
  置き、もう一方の観点は tags に載せる(ファイルの重複配置はしない)。
- **統合で肥大した記憶**: 1 ファイルが長くなり複数の独立した知見を含むように
  なったら、その時点で別 Concept に分割する(分割は通常の完了時フローの中で行う。
  機械的な行数上限は設けない)。
- **`docs/memory/` が空のカテゴリ**: 作らない。記憶が最初に生まれるときに
  カテゴリごと作る(空フォルダの先行作成はしない)。

## 検証方法

1. 移行の完全性: ルート index → カテゴリ index → 全 6 記憶が辿れる。元 8 件の
   「発見・判断とその理由・失敗から得た知識」の各項目が新記憶のいずれかに存在する
   (スポットチェックではなく全項目を突き合わせる)。
2. 検索の実例: `grep -rn "e2e" docs/memory/`(tags ヒット)と
   `grep -rln "compaction" docs/memory/`(本文ヒット)で期待の記憶が見つかる。
3. 参照の整合: `grep -rn "docs/worklog" AGENTS.md README.md docs/state-lifecycle.md`
   が 0 件(過去の spec / plan は対象外)。
4. 既存テスト: `python3 tests/test_pre_compact.py` が green のまま
   (hooks 無変更の確認)。
5. 実機確認(移行後の運用で観察): タスク完了時に記憶への統合(新規ではなく更新に
   なるケースを含む)と、判断前の grep 検索が行われるか。
