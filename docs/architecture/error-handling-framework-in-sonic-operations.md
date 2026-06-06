---
title: Error Handling Framework 設定・運用（show / clear error-database / ERROR_DB スキーマ）
description: Error Handling Framework HLD の CLI / ERROR_DB スキーマ。`show error-database`
  / `sonic-clear error-database` の使い方（HLD 提案、現行 master 未実装）、ERROR_ROUTE_TABLE / ERROR_NEIGH_TABLE
  のフィールド、イベント遷移表をまとめる。
area: architecture
verification: discrepancy-found
last_verified: 2026-05-11
page_kind: split-child
monitor: partially_implemented
sources:
- repo: sonic-net/SONiC
  path: doc/error-handling/error_handling_design_spec.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db: []
  cli:
  - show error-database
  - sonic-clear error-database
  - clear
  yang: []
  _no_related_yang: true
  _no_related_cdb: true
---

# Error Handling Framework 設定・運用

このページは [Error Handling Framework（概要ハブ）](error-handling-framework-in-sonic.md) の派生で、**CLI / ERROR_DB スキーマ / イベント遷移** に絞る。概念は [error-handling-framework-in-sonic-concepts.md](error-handling-framework-in-sonic-concepts.md)、内部実装は [error-handling-framework-in-sonic-internals.md](error-handling-framework-in-sonic-internals.md)、制限事項と乖離は [error-handling-framework-in-sonic-limitations.md](error-handling-framework-in-sonic-limitations.md) を参照。

!!! warning "現行 master では未実装"
    本ページに記載した CLI / ERROR_DB は **HLD 提案** であり、現行 master では `show error-database` / `sonic-clear error-database` ともに未実装。代替手段は [error-handling-framework-in-sonic-limitations.md](error-handling-framework-in-sonic-limitations.md) を参照。

## 1. ERROR_DB スキーマ（HLD 提案）

### ERROR_ROUTE_TABLE

```text
ERROR_ROUTE_TABLE|<prefix>
  operation = CREATE | SET | DELETE
  nexthop   = <ip>[, <ip>...]
  intf      = <ifindex csv>
  rc        = <SWSS_RC_*>
```

### ERROR_NEIGH_TABLE

```text
ERROR_NEIGH_TABLE|(INTF_TABLE|VLAN_INTF_TABLE|LAG_INTF_TABLE).name|<prefix>
  operation = CREATE | SET | DELETE
  neigh     = <mac>
  family    = IPv4 | IPv6
  rc        = <SWSS_RC_*>
```

`rc` は SWSS_RC_FULL（TABLE_FULL）など SWSS code を文字列で持つ想定。

## 2. イベント遷移

下表は HLD §3.3.1（`error_handling_design_spec.md` L194–L202）で **明示列挙された遷移パターンの全件**[^1]。HLD はこの 5 パターンのみを「framework がエントリを既存状態と突き合わせて特別に扱うケース」として列挙しており、抜粋ではない。

| 直前 (Previous) | 今回 (Current) | framework 動作 |
|------|------|----------------|
| Create failure | Update failure | エントリ更新 + 通知 |
| Create failure | Delete failure | エントリ削除 + 通知 |
| Create failure | Update success | エントリ削除 + 通知 |
| Create success | Delete failure | エントリ追加 + 通知 |
| Delete failure | Create success | エントリ削除 + 通知 |

表に現れない組み合わせ（例: 直前 = Create success → 今回 = Update failure、直前 = Update success → 今回 = Update failure、または ERROR_DB に直前エントリが無い「初回失敗」）は、HLD §3.3 の一般則（L168–L188）に従う:

- **失敗イベント受信時** — ERROR_DB にエントリを追加（既存なら failure code を更新）し、登録 listener に通知[^1]
- **成功イベント受信時** — ERROR_DB に対応エントリがあれば削除、無ければ何もしない。listener へは `ERR_NOTIFY_POSITIVE_ACK` 登録者のみ通知[^1]

正常完了系はデフォルトで ERROR_DB に書かない。`ERR_NOTIFY_POSITIVE_ACK` 指定時のみ通知[^1]。

## 3. CLI

| Command | 用途 |
|---------|------|
| `show error-database [TableName]` | 現在の失敗エントリ表示 |
| `sonic-clear error-database [TableName]` | エントリ全削除（OrchAgent は同期削除のみ実施し app 通知はしない）|

```bash
Router# show error-database route
Route             Nexthop                Operation  Failure
2.2.2.0/24        10.10.10.2             Create     TABLE FULL
192.168.10.12/24  12.12.10.2,11.11.11.2  Update     PARAM
```

## 4. Warm boot / scalability

- ERROR_DB は **warm boot 越しに永続化されない**（HLD §6, L378–L379）[^1]
- scalability への直接影響は無いと HLD に記述

## 関連ページ

- [Error Handling Framework（概要ハブ）](error-handling-framework-in-sonic.md)
- [error-handling-framework-in-sonic-concepts.md](error-handling-framework-in-sonic-concepts.md)
- [error-handling-framework-in-sonic-internals.md](error-handling-framework-in-sonic-internals.md)
- [error-handling-framework-in-sonic-limitations.md](error-handling-framework-in-sonic-limitations.md)

<!-- phase-boundary -->
## 実装フェーズ境界

!!! info "Phase 別の実装済 / 未実装 サマリ"
    本ページは `monitor: partially_implemented` で、HLD で示された一連の機能
    が **段階的に取り込まれている** 状態を扱う。フェーズ毎の実装境界を
    1 枚の表に集約する (詳細は本ページ上部の `diff` admonition および
    [discrepancy-index](../reference/verification/discrepancy-index.md) を参照)。

    | Phase | 範囲 (機能 / 段階) | 実装済 (master 取り込み済) | 未実装 (HLD 提案のみ) |
    |---|---|---|---|
    | Phase 1 — 基本機能 | HLD §概要 / §設計の中核ユースケース | 部分取り込み済 — `SWSS_RC_*` enum のみ取り込み済み | ERROR_DB スキーマ / `show error-database` / `sonic-clear error-database` CLI — 未実装（本ページ冒頭 warning 参照） |
    | Phase 2 — 拡張機能 | HLD §拡張 / §追加要件 / §周辺統合 | — | 未実装 / 未マージ — [制限事項](error-handling-framework-in-sonic-limitations.md) を参照 |
    | Phase 3 — 将来拡張 | HLD §Future Work / §将来課題 | — | 未実装 — HLD 提案段階。対応 PR は確認されていない (last_verified 時点) |

    凡例: 「実装済」=現行 master で動作確認できる範囲 / 「未実装」=HLD には記載があるが対応 PR が未マージまたは設計のみで code が存在しない範囲。
<!-- /phase-boundary -->

## 実装との乖離

`monitor: partially_implemented` — 部分実装 — [HLD](../reference/glossary.md#term-hld) の中核は実装済みだが、フィールド / API / 制約のいくつかが上流に未取り込み、または挙動が緩和されている。 本ページは split-child のため、差分の主要根拠 / 影響 / 回避策は親ページ [Error Handling Framework 設定・運用 親ページ](error-handling-framework-in-sonic.md) の同セクション（`## 実装との乖離` または `!!! diff` ブロック）を参照のこと。

## 引用元

[^1]: `sonic-net/SONiC` `doc/error-handling/error_handling_design_spec.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- next-action -->
## このページを読んだ後の次アクション

!!! tip "読み手向け"
    - **本機能を実運用で使う場合**: 取り込み済の部分のみ運用可能。欠落部分の利用は不可なので本文「実装との乖離」を確認した上で適用範囲を限定する
    - **upstream 動向を追う場合**: 関連 issue / PR を [sonic-net/SONiC](https://github.com/sonic-net/SONiC) で検索（HLD タイトル / CONFIG_DB テーブル名 / Orch クラス名で grep するのが速い）
    - **代替手段 / 関連 reference**: 本ページの frontmatter `related` が空のため、[Reference 索引](../reference/index.md) から関連テーブル / CLI / YANG を辿る

!!! note "本ドキュメントの追跡"
    - monitor: `partially_implemented` / last_verified: `2026-05-11`
    - 次回再裏取りトリガ: quarterly。一覧は [discrepancy-index](../reference/verification/discrepancy-index.md) を参照（運用詳細は repo の `meta/discrepancy-operations.md`）

<!-- /next-action -->

<!-- glossary-links-injected: 167700005048 -->
