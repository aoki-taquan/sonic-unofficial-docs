---
title: Error Handling Framework 制限事項と HLD との乖離（コア機構未実装 / CRM 代替）
description: Error Handling Framework HLD の制限事項。SWSS_RC enum だけが先行採用され ERROR_DB /
  ErrorListener / CLI は丸ごと未実装な部分採用状況、サイレント RIB-FIB 乖離リスク、CRM (Critical Resource Monitor)
  ベースの代替運用設計を詳述する。
area: architecture
verification: discrepancy-found
last_verified: 2026-05-11
page_kind: split-child
monitor: partially_implemented
sources:
- repo: sonic-net/SONiC
  path: doc/error-handling/error_handling_design_spec.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
_no_related_cdb: true
related:
  _no_yang: true
---

# Error Handling Framework 制限事項と HLD との乖離

このページは [Error Handling Framework（概要ハブ）](error-handling-framework-in-sonic.md) の派生で、**制限事項と実装乖離** に絞る。概念は [error-handling-framework-in-sonic-concepts.md](error-handling-framework-in-sonic-concepts.md)、CLI / スキーマは [error-handling-framework-in-sonic-operations.md](error-handling-framework-in-sonic-operations.md)、内部実装は [error-handling-framework-in-sonic-internals.md](error-handling-framework-in-sonic-internals.md) を参照。

## 1. HLD レベルの制限事項

- 初版は `ROUTE_TABLE` / `NEIGH_TABLE` のみ。他 table は後付け拡張前提
- GET 失敗は対象外
- retry / rollback は app の責務（framework は report のみ）
- v0.1 (2019-05) のまま改訂が無く、現行 master への取り込み未確認

## 2. 実装との乖離（2026-05 verifier-batch-18）

エラーコード enum だけが先行採用され、ERROR_DB / ErrorListener / CLI は丸ごと未実装な **部分採用状態**。

### 取り込み済み

- `sonic-swss-common/common/status_code_util.h:11-` で `SWSS_RC_SUCCESS / INVALID_PARAM / DEADLINE_EXCEEDED / UNAVAIL / NOT_FOUND / NO_MEMORY / EXISTS / PERMISSION_DENIED` 等の enum 群が定義されている。[HLD](../reference/glossary.md#term-hld) の `SWSS_RC_*` 体系の最低限は libswsscommon 側に入った。

### 未取り込み

- `ERROR_DB` / `ERROR_ROUTE_TABLE` / `ERROR_NEIGH_TABLE` のテーブル名 define は `sonic-swss-common/common/schema.h` に **存在しない**（`grep -n "ERROR_DB\|ERROR_ROUTE_TABLE" schema.h` 0 件。`lagid.h:16` の `LAG_ID_ALLOCATOR_ERROR_DB_ERROR` は別物の戻り値定数）。
- `sonic-swss/orchagent/` 配下に `ErrorListener` / `ErrorReporter` クラスは未定義。RouteOrch / NeighOrch の [SAI](../reference/glossary.md#term-sai) 失敗は内部ロギングだけで、専用 ERROR_DB 通知経路は無い。
- `sonic-utilities/` に `show error-database` / `sonic-clear error-database` CLI が無い。

## 3. 行番号付きエビデンス

`sonic-swss-common/common/status_code_util.h` L11-L25:

```cpp
enum StatusCode {
    SWSS_RC_SUCCESS,
    SWSS_RC_INVALID_PARAM,
    SWSS_RC_DEADLINE_EXCEEDED,
    SWSS_RC_UNAVAIL,
    SWSS_RC_NOT_FOUND,
    SWSS_RC_NO_MEMORY,
    SWSS_RC_EXISTS,
    SWSS_RC_PERMISSION_DENIED,
    SWSS_RC_FULL,
    SWSS_RC_IN_USE,
    SWSS_RC_INTERNAL,
    SWSS_RC_UNIMPLEMENTED,
    SWSS_RC_NOT_EXECUTED,
    SWSS_RC_FAILED_PRECONDITION,
    SWSS_RC_UNKNOWN,
```

→ enum **だけ** 取り込み済み。HLD のコア機構は欠落:

```bash
$ grep -rln "ERROR_DB\|ERROR_ROUTE_TABLE\|ERROR_NEIGH_TABLE\|ErrorListener\|ErrorReporter" \
    .cache/sonic-sources/sonic-swss-common/ .cache/sonic-sources/sonic-swss/
# 0 件（LAG_ID_ALLOCATOR_ERROR_DB_ERROR は別物の戻り値定数）

$ grep -rn "error-database\|error_database" .cache/sonic-sources/sonic-utilities/
# 0 件
```

## 4. 読者への影響

- [BGP](../reference/glossary.md#term-bgp) が経路追加を要求し、[ASIC](../reference/glossary.md#term-asic) FIB がそれを `SAI_STATUS_TABLE_FULL` で reject した場合、[fpmsyncd](../reference/glossary.md#term-fpmsyncd) / bgpd は **失敗を知らない**ため、`show ip route` には経路が見えるが `show ip fib` には無い、というサイレントな乖離が発生する。
- HLD 通りに `show error-database` を期待する自動化スクリプトは即座に失敗する。
- retry / rollback ロジックが実装されないため、ASIC リソース不足（[TCAM](../reference/glossary.md#term-tcam) full 等）の状態は手動介入が必要。
- 一時的回避として OrchAgent のログを syslog で grep する以外に体系的な検知手段が無い。

## 5. 回避策の実コマンド

```bash
# 1) SAI 失敗の発見
sudo grep -E "SAI_STATUS_(TABLE_FULL|INSUFFICIENT_RESOURCES|FAILURE|NOT_SUPPORTED|OBJECT_IN_USE)" \
  /var/log/syslog | tail -50

# 2) OrchAgent ログ詳細化（必要時のみ、ノイズ多い）
sudo swssloglevel -l NOTICE -c orchagent
sudo swssloglevel -l NOTICE -c routeorch
sudo swssloglevel -l NOTICE -c neighorch

# 3) RIB ↔ FIB 突合の手動チェック
diff <(show ip route json | jq -r 'keys[]' | sort) \
     <(show ip fib | awk '{print $1}' | sort) | head

# 4) CRM（Critical Resource Monitor）で SAI リソース上限を監視
show crm resources all
sonic-db-cli COUNTERS_DB hgetall 'CRM:STATS'

# 5) ASIC_DB 内のエラー状態（限定的）
redis-cli -n 1 keys 'ASIC_STATE:SAI_OBJECT_TYPE_ROUTE_ENTRY:*' | wc -l   # RIB と突合
```

## 6. 代替設計: CRM ベース運用

本 HLD の実装着手 PR は **見つからない**。`SWSS_RC_*` enum を導入した PR (`sonic-swss-common` 経由) のみが部分採用の痕跡。

代替の retry/recovery 機構は [CRM](../reference/glossary.md#term-crm) (Critical Resource Monitor: `sonic-swss/orchagent/crmorch.cpp`) で部分的にカバーされており、こちらは production で稼働中。`show crm resources` / `CRM_TABLE` 経由でリソース閾値監視が可能。HLD ベースではなく **CRM ベースで運用設計する方が現実的**。

## 関連ページ

- [Error Handling Framework（概要ハブ）](error-handling-framework-in-sonic.md)
- [error-handling-framework-in-sonic-concepts.md](error-handling-framework-in-sonic-concepts.md)
- [error-handling-framework-in-sonic-operations.md](error-handling-framework-in-sonic-operations.md)
- [error-handling-framework-in-sonic-internals.md](error-handling-framework-in-sonic-internals.md)

<!-- phase-boundary -->
## 実装フェーズ境界

!!! info "Phase 別の実装済 / 未実装 サマリ"
    本ページは `monitor: partially_implemented` で、HLD で示された一連の機能
    が **段階的に取り込まれている** 状態を扱う。フェーズ毎の実装境界を
    1 枚の表に集約する (詳細は本ページ上部の `diff` admonition および
    [discrepancy-index](../reference/verification/discrepancy-index.md) を参照)。

    | Phase | 範囲 (機能 / 段階) | 実装済 (master 取り込み済) | 未実装 (HLD 提案のみ) |
    |---|---|---|---|
    | Phase 1 — 基本機能 | HLD §概要 / §設計の中核ユースケース | 部分取り込み済 — `SWSS_RC_*` enum (`status_code_util.h:11-25`) のみ取り込み済み | ERROR_DB / ErrorListener / ErrorReporter / CLI — 未実装（本ページ「実装との乖離」節参照） |
    | Phase 2 — 拡張機能 | HLD §拡張 / §追加要件 / §周辺統合 | — | 未実装 / 未マージ — HLD §未対応箇所は本ページ「HLD レベルの制限事項」節を参照 |
    | Phase 3 — 将来拡張 | HLD §Future Work / §将来課題 | — | 未実装 — HLD 提案段階。対応 PR は確認されていない (last_verified 時点) |

    凡例: 「実装済」=現行 master で動作確認できる範囲 / 「未実装」=HLD には記載があるが対応 PR が未マージまたは設計のみで code が存在しない範囲。
<!-- /phase-boundary -->

## 実装との乖離

`monitor: partially_implemented` — 部分実装 — HLD の中核は実装済みだが、フィールド / API / 制約のいくつかが上流に未取り込み、または挙動が緩和されている。 本ページは split-child のため、差分の主要根拠 / 影響 / 回避策は親ページ [Error Handling Framework 制限事項と HLD との乖離 親ページ](error-handling-framework-in-sonic.md) の同セクション（`## 実装との乖離` または `!!! diff` ブロック）を参照のこと。

## 引用元

本ページの根拠は引用元 [^1] を参照。

[^1]: `sonic-net/SONiC` `doc/error-handling/error_handling_design_spec.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- next-action -->
## このページを読んだ後の次アクション

!!! tip "読み手向け"
    - **本機能を実運用で使う場合**: 取り込み済の部分のみ運用可能。欠落部分の利用は不可なので本文「実装との乖離」を確認した上で適用範囲を限定する
    - **upstream 動向を追う場合**: 関連 issue / PR を [sonic-net/SONiC](https://github.com/sonic-net/SONiC) で検索（HLD タイトル / CONFIG_DB テーブル名 / Orch クラス名で grep するのが速い）
    - **代替手段 / 関連 reference**: frontmatter `related` に列挙された関連テーブル / CLI / YANG、および [Reference 索引](../reference/index.md) を参照

!!! note "本ドキュメントの追跡"
    - monitor: `partially_implemented` / last_verified: `2026-05-11`
    - 次回再裏取りトリガ: quarterly。一覧は [discrepancy-index](../reference/verification/discrepancy-index.md) を参照（運用詳細は repo の `meta/discrepancy-operations.md`）

<!-- /next-action -->

<!-- glossary-links-injected: c006405759d8 -->
