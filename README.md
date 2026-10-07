# OpenwebUI-SearchGuard

Open WebUI の Native Web Search を、Bonsai2 で安定運用するための Guard Filter です。

本リポジトリは、Bonsai2-27B + Open WebUI Native Web Search を実運用しながら、検索ツールの回数制御、検索結果の検証、fetch 制御、日付 preflight、tool-loop 終了処理、raw `<tool_call>` の観測などを段階的に追加・検証してきた記録でもあります。

## Current version

**v0.8.24**

0.8.24 は **診断専用のリリース**です。0.8.23 の検索・fetch・recovery・final-answer の挙動を変更せず、raw `<tool_call>` がどの状態で発生するかを観測するログを追加しています。

主な対象ファイル:

- `guard0824.py` — 現行 Guard
- `Bonsai2-WebSearch-SystemPrompt.txt` — Bonsai2 用の証拠重視 Web Search system prompt

## 0.8.24 の目的

過去の実測で、Bonsai2 が native tool call を発行せず、assistant の通常テキストとして raw `<tool_call>...</tool_call>` を出す事象が確認されました。

0.8.24 では、この事象について原因を仮定せず、次を観測します。

- `RAW_TOOL_CALL_DIAG` ログ
- raw marker（`<tool_call>`, `<function=`, `<parameter`, `</tool_call>`）
- content 内の最初の `<tool_call>` 位置
- raw text の短い preview
- その hop の tool / tool_choice / final_mode / fetch_suspended
- search / fetch の試行数と成功数
- native tool_calls の有無
- probe state が前 hop から持ち越されたか

**0.8.24 では、これらの診断値を使って検索動作そのものを変更しません。**

## 主要な制御

0.8.24 の Guard には、概ね次の層があります。

### Tool quota

- `max_searches` — 成功した `search_web` の上限
- `max_fetches` — 成功した `fetch_url` の上限
- `max_total_tool_turns` — native tool-call を含む assistant turn のハード上限
- `disable_parallel_tool_calls` — Bonsai2 では既定で parallel tool call を無効化

重要: これらは同じカウンタではありません。

- `search_attempts` / `fetch_attempts` = 試行数
- `search_count` / `fetch_count` = 成功数
- `turns` = tool_calls を出した assistant turn 数
- `hop` = Guard の request/hop 単位

たとえば、fetch がエラーになっても成功 fetch quota は消費しませんが、native tool-call turn 自体は turn cap の対象になります。

### Search result audit / recovery

検索結果について、ユーザーの主要 entity が検索結果に含まれているかを read-only audit します。

結果が不十分な場合は、残りの検索 quota を使って one-shot recovery を行える構成です。

### Fetch gate

検索結果から取得候補 URL を分類し、

- entity が検索結果 evidence に含まれる URL = `OK`
- query に entity が含まれるのに evidence に entity がない URL = `SUSPECT`

として fetch gate に反映します。

`SUSPECT` の実際の扱いは valve 設定に依存します。

また、duplicate fetch の抑止と、一部の重複 fetch に対する temporary fetch suspension があります。

### Current-date preflight

相対時間表現を含む current/latest 系の質問では、Guard 自身が日時を取得し、モデルに absolute date/time を渡します。

0.8.21 以降は時刻も minute precision で提供します。

## 0.8.23 の final-answer 処理

0.8.23 では、tool limit に到達した後も最終回答を生成できるよう、tool を閉じた final-answer hop を用意しています。

さらに final-answer hop だけで raw `<tool_call>` markup を除去し、

- native `tool_calls` を落とす
- `finish_reason=tool_calls` を `stop` に変換
- 空回答時は retrieved result を使った fallback を提供

という処理を行います。

**通常の non-final hop はこの処理で書き換えません。**

## 0.8.24 の重要なログ

代表的なログ:

```
[Bonsai2 Web Search Guard] RAW_TOOL_CALL_DIAG ...
```

特に、

- `native_calls=[]`
- `xml_in_content=True`
- `xml_in_reasoning=False`
- `finish=stop`
- `final_mode=NO`
- `action=OBSERVE_ONLY`

の組み合わせは、raw tool-call XML が通常の assistant content として到達したことを示します。

0.8.24 の診断では、この XML の生成元（モデル、llama.cpp/parser、Open WebUI の tool loop、Guard state の組み合わせ）は **未確定**です。

## 現在のベンチマークで確認できたこと

2026-10-07 時点の実運用テストでは、次の傾向が確認されています。

### 正常に機能しやすいケース

- 公式サイトから現在の CEO 等を 1 件確認する単純な検索
- 公式一次情報を明示的に探す single-target search
- 検索結果から正しい公式ページを一度で選べる単純タスク

### 弱点が出やすいケース

- 複数候補から販売ページを選んで価格を確認する
- 日付条件の厳しい複数ニュースを調べる
- 複数テーマを同時に調査する
- 検索結果から次に fetch すべき URL を計画する
- fetch 失敗後に最適な代替検索を選ぶ
- 公式サイトは発見できても、証拠となる役員ページ等を選ばずトップページを fetch する

実例では、検索結果自体には正しい販売店や公式ページが存在する一方、Bonsai2 が別の商品ページやトップページを先に fetch して tool turn を消費するケースが確認されています。

このため、現時点では **DDGS だけが検索品質のボトルネックとは判断していません**。検索基盤、モデルの query generation / result selection、Web Loader / fetch の3層を分けて評価する必要があります。

## 既知の限界

1. `max_total_tool_turns` と search/fetch 成功 quota は別概念です。
2. 検索結果の発見に成功しても、モデルが適切な URL を選ぶとは限りません。
3. fetch は対象サイト側の JavaScript / anti-bot / security checkpoint の影響を受けます。
4. 16K context では、検索履歴と fetch 結果の増加が model-side の検索判断に影響する可能性があります。ただし prompt の文字数と token 数は同一ではありません。
5. raw `<tool_call>` の根本原因は 0.8.24 の時点では確定していません。

## System prompt

`Bonsai2-WebSearch-SystemPrompt.txt` では、証拠重視・entity identity の維持・検索結果と fetch 結果の区別・不足情報を推測で補完しないことを明示しています。

また、検索回数について prompt 側にも上限方針があります。実運用時の Guard valve と prompt の上限は別レイヤーなので、値が一致しているとは限りません。

## Version history

### 0.8.24
Diagnostics only.

- `RAW_TOOL_CALL_DIAG`
- per-hop diagnostic snapshot
- raw XML detection precision improvement
- raw markers / XML offset / preview / probe age diagnostics
- no search/fetch/final-answer behavior change

### 0.8.23
- current date + time preflight restored
- final-answer mode after tool limit
- final-hop raw tool-call stripping
- final-answer fallback
- tool history flattening in final mode

### 0.8.22
- separated tool execution limit from final-answer generation
- tools closed after limit while answer generation continues
- retrieved results flattened into final-answer input
- empty final-answer fallback

### 0.8.21
- current date + time preflight

### 0.8.20
- current date preflight

### 0.8.19
- fixed main-entity selection around date strings

## Status

**0.8.24 is the observation baseline.**

現在は 0.8.24 を動かしたままベンチマークを蓄積し、モデル由来・検索基盤由来・fetch 由来の問題を分離することを優先しています。

0.8.24 自体の検索挙動を変更する 0.8.25 は、観測データが十分に揃ってから検討します。
