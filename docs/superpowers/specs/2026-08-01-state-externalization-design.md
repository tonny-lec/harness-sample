# 設計: 推論と状態の外部化(Codex CLI / Claude Code 両対応)

日付: 2026-08-01(改訂: 同日)
出典: OpenAI「How enabling two settings tripled our scores on the ARC-AGI-3 benchmark」(2026-07-29)
<https://openai.com/index/how-two-settings-tripled-our-arc-agi-3-scores/>

## 背景

記事の要旨: GPT-5.6 Sol の ARC-AGI-3 低スコアの主因はモデルではなくハーネス設定
だった。スコアは設定変更で約 3 倍(13.3% → 38.3%)、出力トークンは 1/6 になった。

失敗していた状態の本質:

> モデルは過去の行動履歴と短い付随メモは確認できたが、その行動を選ぶまでに
> 形成した「計画・仮説・発見・判断理由・失敗から得た知識」を引き継げなかった。
> そのため毎回ほぼ最初からゲームを理解し直していた。

原因は 2 つ: (1) 各アクション後に private reasoning を破棄、(2) コンテキスト超過時
に古いメッセージを黙って捨てる rolling truncation。対策は reasoning の保持と
compaction(要約圧縮)への置き換えだった。

## 記事の知見 → 本ハーネスへの写像

| 記事の問題 | 記事の対策 | 本ハーネスでの残余リスク | 本設計の対策 |
|---|---|---|---|
| reasoning が毎アクション破棄され、計画・仮説・判断理由が消える | retained reasoning | ランタイムは thinking を保持するが、compaction の要約で推論の細部は失われる。タスク完了・セッション終了で全て消える | 推論(計画・仮説・発見・判断理由・失敗知識)を発生時点でファイルに記録し、タスク完了後もアーカイブとして保持する |
| rolling truncation で古い行動が黙って消える | compaction | compaction 自体は両ハーネスにあるが、要約は損失を伴い、何が落ちたか制御できない | PreCompact hook で compaction 直前にノート最新化を強制し、落ちて困るものを事前にファイルへ退避する |
| 評価がモデルでなくハーネスの束を測っていた | ハーネス設定の見直し | (別設計・非スコープ) | — |

## スコープ

- 対象: 推論・状態の外部化ルール(AGENTS.md / CLAUDE.md)と PreCompact hook。
- 非スコープ(将来の別設計): サブエージェント文脈継承の一般ルール化、
  「性能が低く見えたらまずハーネスを疑う」原則の手順化。

## 決定事項

| 項目 | 決定 | 理由 |
|---|---|---|
| 記録の条件 | タスク規模で限定しない。非自明な判断・仮説・発見・失敗が**生じた時点**で記録 | 「3 ステップ超」等の規模条件では 1 ステップの重要な判断が失われる。守るべきは推論であり、その発生はタスク規模と相関しない |
| 記録の内容 | 計画 / 仮説と検証結果 / 発見 / 判断とその理由 / 失敗から得た知識 | 記事で失われていたのは行動ログではなくこの 5 項目。行動中心の「完了したこと」記録では同じ失敗を繰り返す |
| ノートの保持 | **削除しない**。タスク完了時に `docs/worklog/YYYY-MM-DD-<topic>.md` へ移してコミット | 完了時削除は「reasoning の破棄」と同じ失敗の再演。将来のタスクが過去の判断理由・失敗知識を参照できることが記事の核心 |
| 恒久知識の置き場 | `docs/worklog/`(必要時参照)。**AGENTS.md には載せない** | AGENTS.md は毎セッション全量ロードされ肥大化は性能を劣化させる(Codex は project doc 合計 32KiB 上限)。指示書には行動ルールのみを置く |
| 作業ノートのパス | リポジトリ直下 `working-notes.md`(git 管理外)、完了時に worklog へ | ハーネス中立の名前・場所にすることで Codex ↔ Claude Code 間でタスクを引き継げる。scratchpad はセッション固有のため不採用 |
| hook | PreCompact hook を**両ハーネスで**実装対象に含める | Codex CLI にも PreCompact/PostCompact hook がある(hooks.json / config.toml の `[hooks]`)。ルール(プロンプト)だけに頼らず設定で保証するのが記事の教訓そのもの |
| 内容共有方式 | 少量の重複を許容(AGENTS.md と CLAUDE.md に各々記述) | ルールは短く、ハーネス固有語彙(auto-memory・サブエージェント等)を各々に最適化できる |
| 展開順 | フェーズ1: Codex CLI → フェーズ2: Claude Code | ユーザー指定。まずクリーンなプロジェクト(harness-sample)で検証する |

## フェーズ1: Codex CLI 対応(先行)

### 1-1. AGENTS.md(リポジトリルート)

前提事実(検証済み): Codex CLI は AGENTS.md を「グローバル `~/.codex/AGENTS.md`
→ リポジトリルート → cwd」の順で読み、リポジトリルートより上の階層は読まない。
検証後に全プロジェクト共通化する場合は `~/.codex/AGENTS.md` へ昇格する。

追加するルール:

```markdown
## 推論の外部化

- 非自明な判断・仮説・発見・失敗が生じたら、その時点でリポジトリ直下の
  `working-notes.md`(git 管理外)に記録する。タスクの大小を問わない。
- 記録するのは行動ログではなく推論: 計画 / 仮説と検証結果 / 発見 /
  判断とその理由 / 失敗から得た知識。
- 作業再開時・要約圧縮(compaction)後は、続きを始める前に `working-notes.md`
  を読む。過去タスクの経緯が必要なら `docs/worklog/` を参照する。
- タスク完了時、ノートを `docs/worklog/YYYY-MM-DD-<topic>.md` へ移して
  コミットする。削除しない。このファイル(AGENTS.md)には知識を書かない。
```

あわせて `.gitignore` に `working-notes.md` を追加する。

### 1-2. PreCompact hook(Codex)

`hooks.json`(または `config.toml` の `[hooks]`)で PreCompact イベントに
コマンドを登録し、compaction 直前に「`working-notes.md` に未記録の計画・仮説・
判断理由・失敗知識を書き出してから続行せよ」という指示をモデルに提示する。
manual / auto 両トリガーに一致させる。実装形式(シェル/Python)は skill
`harness-tech-choice` の判断基準に従う。

## フェーズ2: Claude Code 対応

- `harness-sample/CLAUDE.md` に同ルールを置いて検証し、有効性確認後に
  `workspace/CLAUDE.md` へ昇格する。Claude Code 版は次を追加:
  - サブエージェント委譲時は、依頼文にノートの該当部分を含めるかパスを渡す
    (サブエージェントは「reasoning を持たない状態」で起動するため)。
  - ユーザー横断の恒久知識は auto-memory へ(プロジェクト知識は worklog へ)。
- PreCompact hook は `.claude/settings.json` の PreCompact イベントで同趣旨を実装。

## 検証方法

1. フェーズ1 完了後、Codex CLI で harness-sample 上のタスクを実行し観察する:
   (a) 非自明な判断の時点で `working-notes.md` が更新される(小タスクでも)、
   (b) compaction 発生時に PreCompact hook が発火しノートが最新化される、
   (c) 完了時に `docs/worklog/` へアーカイブされ、後続タスクがそれを参照できる。
2. hook は実際に compaction を発生させて発火ログを確認する(「動くはず」禁止)。
3. フェーズ2 も同様に Claude Code で確認する。

## 参照

- Codex AGENTS.md 探索順: <https://developers.openai.com/codex/guides/agents-md>
- Codex hooks(PreCompact/PostCompact): <https://developers.openai.com/codex/hooks>
