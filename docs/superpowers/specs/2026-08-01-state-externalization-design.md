# 設計: 長時間タスクの状態外部化(Codex CLI / Claude Code 両対応)

日付: 2026-08-01
出典: OpenAI「How enabling two settings tripled our scores on the ARC-AGI-3 benchmark」(2026-07-29)
<https://openai.com/index/how-two-settings-tripled-our-arc-agi-3-scores/>

## 背景と目的

記事の要旨: GPT-5.6 Sol の ARC-AGI-3 低スコアの主因はモデルではなくハーネス設定
だった。(1) 各アクション後に private reasoning を破棄していた、(2) コンテキスト
超過時に古いメッセージを捨てる rolling truncation を使っていた。reasoning の保持と
compaction(要約圧縮)への置き換えでスコアは約 3 倍(13.3% → 38.3%)、出力トークン
は 1/6 になった。教訓は「エージェントは過去の思考・行動を覚えているときに最も
性能が出る」「評価はモデル単体ではなくハーネスとの束を測っている」。

Claude Code / Codex CLI はいずれも reasoning 保持と compaction をランタイムが既に
行うため、API 設定をそのまま持ち込む話ではない。ただし compaction は要約であり
損失を伴う。本設計は、その残余リスクに対する能動的対策として、長時間タスクの
学び・決定・進行状態を**ファイルに外部化**するルールを両ハーネスの指示書
(AGENTS.md / CLAUDE.md)に導入する。

## スコープ

- 対象: 長時間タスクの状態外部化ルールのみ。
- 非スコープ(将来の別設計): サブエージェント文脈継承の一般ルール化、
  「性能が低く見えたらまずハーネスを疑う」原則の手順化。

## 決定事項

| 項目 | 決定 | 理由 |
|---|---|---|
| 実装形態 | 指示書への常時ロードルール(数行) | skill は発火忘れのリスクがあり、「覚えていない状態」で発火し損ねる失敗モードが対策対象そのものと重なる |
| 作業ノートのパス | リポジトリ直下 `working-notes.md`(git 管理外) | ハーネス中立の名前にすることで、Codex で始めたタスクを Claude Code で再開できる(逆も同様)。scratchpad はセッション固有のため不採用 |
| 内容共有方式 | 少量の重複を許容(AGENTS.md と CLAUDE.md に各々記述) | ルールは数行であり、ハーネス固有語彙(auto-memory・サブエージェント等)を各々に最適化できる。@import による密結合を避ける |
| 展開順 | フェーズ1: Codex CLI(AGENTS.md)→ フェーズ2: Claude Code(CLAUDE.md) | ユーザー指定。まずクリーンなプロジェクト(harness-sample)で検証する |

## フェーズ1: Codex CLI 対応(先行)

配置: `harness-sample/AGENTS.md`(リポジトリルート)。

前提事実(検証済み): Codex CLI は AGENTS.md を「グローバル `~/.codex/AGENTS.md`
→ リポジトリルート → cwd まで下る」順で読み、リポジトリルートより上の階層
(workspace/ 等)は読まない。よってプロジェクト固有の配置はリポジトリルート一択。
検証後に全プロジェクト共通化する場合は `~/.codex/AGENTS.md` へ昇格する。

追加するルール(AGENTS.md):

```markdown
## 長時間タスクの状態外部化

- 3 ステップ超の計画実行、または探索を伴う調査を開始したら、リポジトリ直下に
  作業ノート `working-notes.md`(git 管理外)を作成する。
- 各ステップ完了時に追記する: 完了したこと / 学んだこと・判明した制約 / 次の一手。
  会話に書いただけの重要な発見は「未記録」と見なす。
- 要約圧縮(compaction)後・セッション再開時は、作業を続ける前にまず
  `working-notes.md` を読む。
- タスク完了時にノートは削除する。恒久的な学びは AGENTS.md へ移す。
```

あわせて `.gitignore` に `working-notes.md` を追加する。

## フェーズ2: Claude Code 対応

配置: まず `harness-sample/CLAUDE.md` に同ルールを置いて検証し、有効性を確認後に
`workspace/CLAUDE.md`(全プロジェクト共通)へ昇格する。

Claude Code 版はハーネス固有の 2 行を追加する:

```markdown
- サブエージェント委譲時は、依頼文にノートの該当部分を含めるかパスを渡す。
- 恒久的な学びは CLAUDE.md か auto-memory へ移す(ノートには残さない)。
```

## 将来拡張(設計のみ、今回は実装しない)

Claude Code の PreCompact hook で、compaction 直前に「`working-notes.md` を最新化
せよ」というリマインドを注入する。ルールが習慣として機能しない場合の機械的保険。
実装時は skill `harness-tech-choice` の判断基準に従う。Codex CLI 側には同等の
hook 機構がないため、当面はルールのみで運用する。

## 検証方法

1. フェーズ1 完了後、Codex CLI で harness-sample 上の長時間タスク(3 ステップ超)
   を 1 件実行する。
2. 観察点: (a) `working-notes.md` が作成され各ステップで更新されること、
   (b) compaction またはセッション再開後、ノート参照から作業を再開できること、
   (c) タスク完了時にノートが削除されること。
3. フェーズ2 も同様に Claude Code で 1 件実行して確認する。
