---
title: スタイルガイド
area: reference
verification: meta
last_verified: 2026-05-11
description: "ドキュメント執筆ルール"
tags: [meta, styleguide]
sources: []
related:
  cli: []
  config_db: []
  yang: []
  _no_related: true
---

# スタイルガイド

本ページは、[SONiC](../reference/glossary.md#term-sonic) 非公式日本語ドキュメント (`docs/`) を執筆する際の文体・構造・タグ・引用ルールをまとめた執筆者向けリファレンスである。Writer / Reviewer / Verifier いずれのロールでも、本ガイドに沿って差分を作る。例外を設ける場合は本文または PR 説明にその理由を明示する。

## 概要

本リポジトリは AI エージェントによる継続的な再構成を前提としている。文体・frontmatter・引用形式が揃っていない場合、機械的な品質監査 (`frontmatter_lint.py` / Reviewer prompt) が落ちて merge が止まる。したがって本ガイドは「人間の好みを揃える」よりも「機械チェックが通る最低ライン」を定義することを目的とする。

## frontmatter ルール

frontmatter のフィールド定義は [`meta/templates/SCHEMA.md`](https://github.com/aoki-taquan/sonic-unofficial-docs/blob/main/meta/templates/SCHEMA.md) を一次情報源とする。以下は実務的な抜粋である。

| キー | 必須 | 値 |
|------|------|----|
| `title` | はい | 表示タイトル (40 字目安) |
| `area` | はい | `routing` / `switching` / `overlay` / `acl-qos` / `system` / `management` / `platform` / `architecture` / `internals` / `reference` |
| `verification` | はい | `hld-only` / `issue-confirmed` / `code-verified` / `discrepancy-found` / `runbook-verified` / `stub` / `meta` |
| `last_verified` | はい | `YYYY-MM-DD` |
| `sources` | はい | 一次情報のリスト。`meta` ページは空配列可 |
| `monitor` | 条件付 | `verification: discrepancy-found` のとき必須 |
| `page_kind` | optional | `chapter-index` / `split-hub` / `split-child` |
| `related.{config_db,cli,yang}` | optional | 空配列でも合格。推測で埋めてはならない |

新規ページを書く際は `meta/templates/page.md` をコピーして雛形にする。`frontmatter_lint.py` を走らせ、必須フィールドが揃っていることを確認してから commit する。

## title 規約

- 40 字を目安に収める。長い注釈は本文 H1 直下の段落で扱う
- 「機能名 + 短い注釈」を基本形にする。例: `BGP unnumbered（IPv6 LLA を用いた BGP セッション）`
- nav に出る文字列はこの `title` がそのまま使われるため、ナビ崩れに注意する
- 章扉 (`page_kind: chapter-index`) は番号付きで章のスコープを示す。例: `08 VXLAN / EVPN / VNET`

## 本文構造

通常解説ページは以下の見出し順を標準とする。

```text
# <title と同じ>      <- H1 は 1 つだけ
## 概要               <- 何のためのページか、対象機能の一行サマリ
## 動作仕様           <- フロー / コンポーネント / DB スキーマ
## 設定               <- CLI / CONFIG_DB の最小設定例
## 制限事項           <- 既知の制約・未実装・platform 依存
## 関連               <- 隣接機能・関連ページへのリンク
## 引用               <- 一次情報 / 脚注定義
```

- 章扉 (`chapter-index`) は `## 概要` のあと、配下ページへのリンク集を中心にする
- `split-hub` は冒頭で `split-child` への導線（concepts / operations / internals / limitations）を提示する
- `discrepancy-found` ページは `## 動作仕様` の代わりに `## 実装との乖離` を立てる。`SCHEMA.md` の軸 6 評価基準 (a)〜(d) を満たす構造で書く

## mermaid 使い方

画像は原則 mermaid のみ許可する（後述）。記法の使い分けは次の通り。

- `flowchart LR` — パケット経路・データプレーンの流れ・状態の左→右遷移
- `flowchart TD` — レイヤ構造・コンポーネント階層・「上位 → 下位」関係
- `sequenceDiagram` — [orchagent](../reference/glossary.md#term-orchagent) / [syncd](../reference/glossary.md#term-syncd) / [SAI](../reference/glossary.md#term-sai) / kernel をまたぐ呼び出し順序
- `stateDiagram-v2` — [BGP](../reference/glossary.md#term-bgp) / [LACP](../reference/glossary.md#term-lacp) / [BFD](../reference/glossary.md#term-bfd) などのプロトコル状態機械

ノードラベル内では絵文字を使わない（PDF / 一部レンダラで文字化けする）。代わりに `[警告: ...]` のような括弧表記を使う。色指定 (`classDef`) は最小限にとどめる。

## admonition 使い方

MkDocs Material の admonition は次の用途に絞って使う。

- `!!! note` — 補足情報。読み飛ばしても主旨に影響しない
- `!!! tip` — 運用 Tips / コツ
- `!!! warning` — 既知の落とし穴・設定ミスしやすい点
- `!!! danger` — データ損失・ループ・サービス停止に直結する操作
- `!!! diff` — [HLD](../reference/glossary.md#term-hld) と実装の乖離を示す専用ブロック (`discrepancy-found` ページのみ)

`!!! diff` は必ず HLD 側の主張・現行 master の状態・読み手への影響を 3 段で書く。

## glossary 用語

技術用語は `docs/reference/glossary.md` に定義する。本文中での扱いは次の通り。

- 初出時のみ glossary anchor へのリンクを張る
- リンクの自動付与は CI の `inject_glossary_links.py` が行うため、Writer は手書きしない
- glossary に未登録の重要用語に遭遇したら、同 PR か別 PR で `glossary.md` に追加する

## 脚注 / evidence

主張の裏取りは脚注と HTML コメントの二段構えで行う。

- 込み入った主張・数値・実装挙動には脚注 `[^1]` を付け、ページ末で commit パーマリンクを定義する
- 脚注の直前または該当段落の直下に `<!-- evidence: source: <repo>/<path>#L<start>-L<end> ... -->` の HTML コメントでコード抜粋と判定理由を埋める
- evidence の行範囲は「該当行を含む」程度の精度で良い。完全一致は要求しない
- Reviewer / Verifier はこの evidence コメントを根拠に `code-verified` / `discrepancy-found` を判定する

## コードブロック

- 言語タグを必ず付ける (` ```bash`, ` ```yaml`, ` ```c++`, ` ```json` など)
- CLI 出力は ` ```text` を使う
- 長すぎる出力は `# ... (省略) ...` のコメントで途中を省略し、要点だけ残す
- フル設定例を載せたい場合は、別ファイルではなく折りたたみ admonition (`??? example`) を使う

## 画像

- 原則 mermaid のみとする。PNG / SVG は base platform 図 / hardware 図のように構造が固定で mermaid で表現できない場合にのみ許可する
- スクリーンショットは禁止 (`meta` 仕様外)
- 図中の文字は日本語可。ただし固有名詞（プロトコル名・コマンド名）は原綴で書く

## 日本語スタイル

- 文体は「である調」で統一する。「ですます調」は本ガイドおよび README 等の対人向けページに限定する
- 技術用語は原則カタカナ表記とする。例: ルータ / スイッチ / オーケストレータ / オーバーレイ
- 固有名詞・プロダクト名・コマンド名は原綴のままにする。例: SONiC / orchagent / syncd / [FRR](../reference/glossary.md#term-frr) / Mellanox
- 助詞「は / が / を / に」の重複を避ける。長い修飾句は読点で区切る
- 半角英数字と日本語の間にスペースは入れない（MkDocs の表示で間延びするため）
- 箇条書きは「、」「。」を統一する。文の集まりは句点で終え、語句の列挙は句読点なしで揃える

## page_kind の使い分け

| 値 | 用途 |
|----|------|
| `chapter-index` | 22 章扉 (`docs/topics/NN-slug/index.md`)。配下ページへの導線が本体 |
| `split-hub` | 大型 HLD を分割した際の元概要ハブ。`<base>.md` に付与し、`split-child` 群への導線を持つ |
| `split-child` | 上記から派生した `<base>-concepts.md` / `-operations.md` / `-internals.md` / `-limitations.md` 等 |
| 未指定 | 通常の単一解説ページ |

`split-hub` と `split-child` は同じ HLD ソースを共有するため、`verification` / `sources` を一致させる。`split-child` は本文ボリューム単独では評価されず、ハブとの導線・主張の網羅性で評価される。

## 関連

- [SCHEMA.md (frontmatter スキーマ一次情報源)](https://github.com/aoki-taquan/sonic-unofficial-docs/blob/main/meta/templates/SCHEMA.md)
- [page.md (ページテンプレート)](https://github.com/aoki-taquan/sonic-unofficial-docs/blob/main/meta/templates/page.md)
- [glossary.md](glossary.md)
- [品質監査ガイド](https://github.com/aoki-taquan/sonic-unofficial-docs/blob/main/meta/quality-audit-guide.md)

## 引用

本ページはプロジェクト内ルールを集約した `meta` ページであり、SONiC 一次情報源を持たない。スキーマ・テンプレートの正本は `meta/templates/` 配下のファイルである。

## 関連 reference

- [Reference index](index.md)
- [Glossary](glossary.md)
- [Topics: Reference index](../topics/22-reference-index/index.md)

<!-- glossary-links-injected: 8ba32e5aa69d -->
