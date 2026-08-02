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
| reasoning が毎アクション破棄され、計画・仮説・判断理由が消える | retained reasoning | 両ハーネスともセッション内では推論を保持する(Codex: Responses API / Claude: thinking ブロックを履歴で戻す)。失われるのは compaction の要約時・セッション終了時・サブエージェント起動時 | 推論(計画・仮説・発見・判断理由・失敗知識)を発生時点でファイルに記録し、タスク完了後もアーカイブとして保持する |
| rolling truncation で古い行動が黙って消える | compaction(=次の判断に必要な状態を選んで維持するコンテキスト管理。要約はその手段) | compaction 自体は両ハーネスにあるが、何が残るかは制御できない | PreCompact hook で compaction 直前にノート最新化を強制し、「次の判断に必要な状態」を明示的にファイルへ退避する |
| — | — | 「再開時にノートを読む」を指示(プロンプト)に頼ると発動しないことがある | SessionStart hook でノートを機械的にコンテキストへ注入する(プロンプトではなく設定で保証) |
| 評価がモデルでなくハーネスの束を測っていた | ハーネス設定の見直し | (別設計・非スコープ) | — |

## スコープ

- 対象: 推論・状態の外部化ルール(AGENTS.md / CLAUDE.md)、PreCompact hook、
  SessionStart hook。
- 非スコープ(将来の別設計): サブエージェント文脈継承の一般ルール化、
  「性能が低く見えたらまずハーネスを疑う」原則の手順化。

## 決定事項

| 項目 | 決定 | 理由 |
|---|---|---|
| 記録の条件 | タスク規模で限定しない。**観測可能な事象**で列挙する: 選択肢から選んだ(選んだ理由・採らなかった各案の理由を含む) / 仮説を立てた・検証結果が出た / 予想外の結果・エラーに遭遇 / 外部調査で事実確認 / 計画変更 | 「3 ステップ超」等の規模条件では 1 ステップの重要な判断が失われる。「非自明なら記録」のような主観的条件は発動しにくいため、チェック可能な事象で定義する |
| 記録の内容 | 計画 / 仮説と検証結果 / 発見 / 判断とその理由 / 失敗から得た知識 | 記事で失われていたのは行動ログではなくこの 5 項目。行動中心の「完了したこと」記録では同じ失敗を繰り返す |
| ノートの構造 | 二部構成: 冒頭「現在の状態と次の一手」(常に上書き・簡潔)+ 以降は追記型の推論記録 | 全量追記だけでは重要情報が埋もれる。必要なのは保存量の最大化ではなく「次の判断に必要な状態」の維持 |
| ノートの保持 | **削除しない**。タスク完了時に `docs/worklog/YYYY-MM-DD-<topic>.md` へ移してコミット | 完了時削除は「reasoning の破棄」と同じ失敗の再演。将来のタスクが過去の判断理由・失敗知識を参照できることが記事の核心 |
| worklog の形式 | OKF(Open Knowledge Format)v0.2 準拠のバンドルとして構成 | 人間とエージェント双方が読め、ツール不要・diff 可能・可搬。`index.md` の段階的開示により、指示書を肥大させずに過去知識を発見可能にする |
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

あわせて `.gitignore` に `working-notes.md` を追加する。

### 1-2. worklog の形式(OKF)

`docs/worklog/` を OKF v0.2 の Knowledge Bundle として構成する。OKF は
「YAML frontmatter 付き Markdown のディレクトリ」というだけの最小規約で、
必須 frontmatter は `type` のみ。SDK やツールは不要。

```
docs/worklog/
├── index.md                    # 一覧(段階的開示用)。1 エントリ 1 行
└── 2026-08-01-<topic>.md       # 1 タスク = 1 コンセプト
```

各エントリの形式:

```markdown
---
type: Worklog
title: <タスクの短い題>
description: <1 行要約>
tags: [<領域タグ>]
timestamp: <ISO 8601 更新日時>
actor: <書き手。OKF 規約: エージェントは <producer>/<version>、人は human:<id>>
---

# 計画
# 仮説と検証結果
# 発見
# 判断とその理由
# 失敗から得た知識
```

`actor` により「どのハーネス・モデルの推論か」が残り、ハーネス横断運用時に
出所を追跡できる。空の見出しは削って良い。関連する過去エントリへは通常の
Markdown リンクで参照する(OKF の Link 規約)。

### 1-3. PreCompact hook(Codex)

`hooks.json`(または `config.toml` の `[hooks]`)で PreCompact イベントに
コマンドを登録し、compaction 直前に「`working-notes.md` に未記録の計画・仮説・
判断理由・失敗知識を書き出してから続行せよ」という指示をモデルに提示する。
manual / auto 両トリガーに一致させる。実装形式(シェル/Python)は skill
`harness-tech-choice` の判断基準に従う。

### 1-3b. compaction の運用方針

compaction の発火タイミングと要約の生成はランタイム(Codex / Claude Code)に
任せ、本設計では制御しない。守るのは「compaction で何が失われても、次の判断に
必要な状態がファイルから復元できる」ことであり、防御は三層で構成する:

1. **平時(主防御)**: AGENTS.md ルールによる随時記録。推論は発生時点で
   `working-notes.md` に書かれているため、compaction がいつ起きても失うものが
   最小になる。hook はこの習慣の保険であり代替ではない。
2. **compaction 直前(退避)**: PreCompact hook(1-3)。ノート冒頭の
   「現在の状態と次の一手」を最新化させる。
   - 実装時の検証項目: Codex の PreCompact hook でモデルに書き出しを
     行わせられるか(hook の stdout がコンテキスト注入されるか)は一次資料で
     未確認。不可の場合は PostCompact hook にフォールバックする(下記)。
3. **compaction 直後(復元)**: PostCompact hook で「compaction が実行された。
   続行前に `working-notes.md` を読み、冒頭の状態セクションと現在の認識を
   突き合わせよ」という指示を注入する。要約に細部が残らなくても、ノートから
   状態を再構成できる。

手動 `/compact` も matcher(`manual|auto`)で同様に扱う。要約プロンプト自体の
カスタマイズ(何を残すかの誘導)は両ハーネスで可否が異なるため本設計の
スコープ外とし、ノートによる外部化で代替する。

### 1-4. SessionStart hook(Codex)

`hooks.json` の SessionStart イベント(matcher: `startup|resume`)で
`working-notes.md` が存在すればその内容を stdout に出力する。Codex は hook の
stdout を developer context としてセッションに注入するため、「再開時にノートを
読む」がプロンプト規範ではなく設定として保証される。ノートが無ければ何も
出力しない(no-op)。

## フェーズ2: Claude Code 対応

- `harness-sample/CLAUDE.md` に同ルールを置いて検証し、有効性確認後に
  `workspace/CLAUDE.md` へ昇格する。Claude Code 版は次を追加:
  - サブエージェント委譲時は、依頼文にノートの該当部分を含めるかパスを渡す
    (サブエージェントは「reasoning を持たない状態」で起動するため)。
  - ユーザー横断の恒久知識は auto-memory へ(プロジェクト知識は worklog へ)。
- PreCompact hook / SessionStart hook は `.claude/settings.json` の同名イベントで
  同趣旨を実装する(Claude Code の SessionStart も stdout をコンテキストに注入する)。

## 検証方法

1. フェーズ1 完了後、Codex CLI で harness-sample 上のタスクを実行し観察する:
   (a) 列挙した事象(選択・仮説・予想外の結果・事実確認・計画変更)の時点で
   `working-notes.md` が更新される(小タスクでも)、
   (b) compaction 発生時に PreCompact hook が発火しノートが最新化される
   (書き出し誘導が不可なら PostCompact フォールバックが発火し読み直しが起きる)、
   (c) セッション再開時に SessionStart hook がノートをコンテキストへ注入する
   (`codex` を再起動して確認)、
   (d) ノート冒頭の「現在の状態と次の一手」が上書き更新され肥大しない、
   (e) 完了時に OKF 形式で `docs/worklog/` へアーカイブされ `index.md` に
   1 行追記される。後続タスクが index 経由でそれを参照できる。
2. hook は実際に compaction を発生させて発火ログを確認する(「動くはず」禁止)。
3. フェーズ2 も同様に Claude Code で確認する。

## 参照

- Codex AGENTS.md 探索順: <https://developers.openai.com/codex/guides/agents-md>
- Codex hooks(PreCompact/PostCompact/SessionStart): <https://developers.openai.com/codex/hooks>
- OKF 紹介記事: <https://cloud.google.com/blog/ja/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing/>
- OKF v0.2 仕様(SPEC.md): <https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf>
