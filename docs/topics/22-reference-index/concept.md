---
title: リファレンス設計の考え方
description: "リファレンス設計の考え方 — このページでは、docs/reference/ 配下の辞書ページ群が機能章 (docs/topics/) およびカテゴリページ (docs/categories/) とどう棲み分けているかを整理する。"
area: topics
verification: meta
last_verified: 2026-05-10
keywords:
  - Reference
  - 概念
  - 横断索引
  - CLI / CONFIG_DB / YANG
  - 情報設計
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

<!-- xref-prereq -->
## この章の前提知識

この章を読み進める前に、次の章を押さえておくと迷子になりにくい。

- [SONiC 全体像と設定基盤](../01-overview/index.md)

<!-- glossary-links-injected: 2e72833604bb -->
