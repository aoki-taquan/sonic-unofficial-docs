---
title: リファレンス設計の考え方
description: リファレンス設計の考え方 — このページでは、docs/reference/ 配下の辞書ページ群が機能章 (docs/topics/) およびカテゴリページ
  (docs/categories/) とどう棲み分けているかを整理する。
area: topics
verification: meta
last_verified: 2026-05-10
keywords:
- Reference
- 概念
- 横断索引
- CLI / CONFIG_DB / YANG
- 情報設計
related:
  cli:
  - config bgp
  - show bgp
  - show techsupport
  - show platform
  - show version
  - show acl
  - config acl
  config_db: []
  yang: []
  _no_related_config_db: true
  _no_related_yang: true
---

# リファレンス設計の考え方

このページでは、`docs/reference/` 配下の辞書ページ群が機能章 (`docs/topics/`) およびカテゴリページ (`docs/categories/`) とどう棲み分けているかを整理する。

## 3 層の役割

このドキュメント全体は、以下の 3 層で読み手の入口を多重化している。

| 層 | 場所 | 役割 | 1 ページの粒度 |
|---|---|---|---|
| 機能章 (topics) | `docs/topics/<NN>-<feature>/` | 読み物。設定 → 運用 → 内部実装の順に複数 [HLD](../../reference/glossary.md#term-hld) を再構成する | 章 = 4〜8 ページ |
| 辞書 (reference) | `docs/reference/{cli,config-db,yang}/` | 辞書。コマンド名 / table 名 / モジュール名から仕様を逆引き | 1 ページ = 1 コマンド群 or 1 テーブル or 1 モジュール |
| カテゴリ (categories) | `docs/categories/` | 軸別の集約 (例: [SAI](../../reference/glossary.md#term-sai) 拡張、CLI 章ごとの章まとめ)。area 横断のメタ整理 | 1 ページ = 1 軸 |

機能章は「読み手の問いから入る」設計、辞書は「名前から入る」設計、カテゴリは「軸 (実装階層、HLD 種別) から入る」設計である。3 層は同じ素材を別の入口から照射しているだけで、相互排他にはしない。

## 「機能章から参照、辞書章から逆引き」

辞書ページの本文は HLD と CLI 実装ベースで書かれているため、機能章本文側で再度長文の仕様を書くと内容が二重化する。Phase B 着手時のルールは次の通り。

- 機能章の「設定」ページからは、[CONFIG_DB](../../reference/glossary.md#term-config_db) table のスキーマ詳細を引きたい場合に reference ページへリンクする。本文では table 名と主キー、最小設定例の意味だけを書く。
- 機能章の「運用」ページからは、CLI コマンドの全オプションを引きたい場合に reference ページへリンクする。本文では「どの順番でどのコマンドを叩くか」だけを書く。
- 機能章の「内部実装」ページからは、[YANG](../../reference/glossary.md#term-yang) モデル名と native / OpenConfig の対応を引きたい場合に reference ページへリンクする。
- reference ページからは、関連機能章へ戻れるリンクが望ましい (本章は逆引き表をここでまとめるため、reference ページ自身の本文は触らない)。

## カテゴリページとの関係

`docs/categories/` には以下のような軸が既に存在する。

- [SAI 拡張属性追加系](../../categories/sai-extensions.md)
- カウンタ / デバッグ系
- platform / port lifecycle
- ほかドキュメント整理軸

カテゴリは「実装階層の縦軸 (SAI / SWSS / [syncd](../../reference/glossary.md#term-syncd)) に沿って HLD を束ねたい」「ある主題 (counter、test plan) を横断したい」など、機能章とは別の軸でページを集める用途で残す。機能章で読み終えた読者が、さらに「同じ階層で関連する HLD を一覧したい」ときに辿る位置付けである。

## discrepancy と reference gap の位置

Phase 6 で `verification: hld-only` のページを 0 件にし、すべて `code-verified` または `discrepancy-found` に振り分けた。discrepancy が見つかった箇所は `docs/_meta/discrepancies.md` に一覧化し、reference 側で未カバーのまま残っている項目は `meta/reference-gaps.md` に積み上げてある。これらは本章 [品質と gap](quality-gaps.md) で扱う。

## このページの位置付け

このページは「reference を読まずに機能章だけ読む」と「reference だけを辞書として使う」のどちらでも完結しないことを前提に、章と辞書を往復する読者を救う索引層の入口を定義する。具体的な対応表は次の 3 ページで提供する。

- [CLI 横断索引](cli-index.md)
- [CONFIG_DB 横断索引](config-db-index.md)
- [YANG 横断索引](yang-index.md)

## 索引の粒度を選ぶ

reference を引くときは、入口になる名前の種類で粒度が変わる。読者の問いから粒度を決めてから索引に入ると迷子にならない。

| 読者の問い | 引き始める索引 | 粒度 |
| --- | --- | --- |
| 「`config bgp neighbor add` の引数を確認したい」 | [CLI 横断索引](cli-index.md) → コマンド群ページ | 1 コマンド群 = 1 ページ |
| 「`BGP_NEIGHBOR_AF` のキー構造を確認したい」 | [CONFIG_DB 横断索引](config-db-index.md) | 1 テーブル = 1 ページ |
| 「`sonic-bgp-global` がどの leaf を持つか確認したい」 | [YANG 横断索引](yang-index.md) | 1 モジュール = 1 ページ |
| 「機能 X に関する CLI / table / YANG を一望したい」 | 機能章 (`docs/topics/<NN>-<feature>/index.md`) の `related` | 機能単位 |
| 「実装階層 (SAI / SWSS / syncd) で HLD を束ねたい」 | `docs/categories/` | 階層単位 |

reference ページ単体には機能章への戻りリンクが付いており、reference → 機能章 → reference の往復が成立するように配置している。

## 命名規約とそろえ方

reference ページの slug は **コマンド名 / table 名 / モジュール名そのもの** を使う。`docs/topics/` の slug は **機能ドメイン名 (kebab-case)** を使う。両者を混同しないよう、次のルールで一貫させている。

- CLI ページ: `docs/reference/cli/<root-command>-<subgroup>.md` (例: `config-bgp.md`、`show-ip.md`)。
- CONFIG_DB ページ: `docs/reference/config-db/<table-name-lower>.md` (例: `bgp-neighbor.md`)。
- YANG ページ: `docs/reference/yang/<module-name>.md` (例: `sonic-bgp-global.md`)。
- 機能章: `docs/topics/<NN>-<feature>/` で 2 桁の章番号を付け、章内ファイルは `concept.md` / `setup.md` / `operations.md` / `internals.md` / `advanced.md` に揃える。

この命名規約は frontmatter の `sources` から逆方向にも辿れる前提を作る。検索エンジンや IDE で「テーブル名」を grep すれば該当 reference ページに当たり、そこから related で機能章に戻れる。

## 3 層の往復例

実際に読み手が辿るパスを 1 つ追うと、3 層の役割分担が見える。

例: 「[BGP](../../reference/glossary.md#term-bgp) neighbor を 1 つ足したい」と思った読者の動きはこうなる。

1. 機能章 [BGP - 設定](../02-bgp/setup.md) で「何を CONFIG_DB に書くか」「どの CLI を打つか」の **手順** を読む。
2. 手順内のリンクから reference [config bgp](../../reference/cli/config-bgp.md) に飛び、CLI 全オプションを引く。
3. 同じく [BGP_NEIGHBOR](../../reference/config-db/bgp-neighbor.md) で table の全カラムを引く。
4. [gNMI](../../reference/glossary.md#term-gnmi) から入れたい場合だけ [sonic-bgp-neighbor](../../reference/yang/sonic-bgp-neighbor.md) を引く。
5. SAI 拡張観点で他機能と並べたい場合は categories の [SAI 拡張](../../categories/sai-extensions.md) を参照する。

機能章は (1) と (2)〜(5) への入口で、reference は **同じ操作対象を別の名前から引き直す** ための層になる。

## 索引が満たすべき不変条件

reference 索引は次の不変条件を満たす前提で運用している。CI / lint で部分的に検査される。

- すべての reference ページは少なくとも 1 つの機能章から `related` で参照されている (orphan reference は CI で警告)。
- 機能章の `related.cli` / `related.config_db` / `related.yang` に並ぶ名前は、対応する reference ページが存在する。
- `discrepancy-found` のページは `docs/_meta/discrepancies.md` から逆引きできる。
- reference 側の未カバー項目は `meta/reference-gaps.md` に積まれ、本章 [品質と gap](quality-gaps.md) に集約される。

不変条件が崩れたときは「reference を足す」「機能章の related を直す」「discrepancy を昇格させる」のいずれかで埋める。索引層の役割は、この埋め残しを可視化することにある。

<!-- xref-prereq -->
## この章の前提知識

この章を読み進める前に、次の章を押さえておくと迷子になりにくい。

- [SONiC 全体像と設定基盤](../01-overview/index.md)

<!-- glossary-links-injected: 3fe800163a71 -->
