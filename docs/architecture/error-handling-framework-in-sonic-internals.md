---
title: Error Handling Framework 内部実装（OrchAgent producer / ErrorListener / ASIC_DB
  notification）
description: Error Handling Framework HLD の内部実装。OrchAgent が SAI 失敗を ASIC_DB notification
  channel 経由で受け取り ERROR_DB へ producer として書き込む経路、ErrorListener の register API と pub/sub
  受信、SAI 失敗から SWSS_RC への翻訳点を解説する。
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

# Error Handling Framework 内部実装

このページは [Error Handling Framework（概要ハブ）](error-handling-framework-in-sonic.md) の派生で、**producer / consumer 内部実装** に絞る。概念は [error-handling-framework-in-sonic-concepts.md](error-handling-framework-in-sonic-concepts.md)、CLI / スキーマは [error-handling-framework-in-sonic-operations.md](error-handling-framework-in-sonic-operations.md)、制限事項と乖離は [error-handling-framework-in-sonic-limitations.md](error-handling-framework-in-sonic-limitations.md) を参照。

## 1. Producer（OrchAgent）

OrchAgent が **唯一の ERROR_DB producer** として位置づけられる[^1]:

1. [SAI](../reference/glossary.md#term-sai) 呼び出し失敗を **[ASIC_DB](../reference/glossary.md#term-asic_db) の notification channel** 経由で [syncd](../reference/glossary.md#term-syncd) から受領
2. SAI status → SWSS_RC のマッピングテーブルで翻訳
3. 対象 table 名（`ROUTE_TABLE` / `NEIGH_TABLE` 等）と key を引いて ERROR_ROUTE_TABLE / ERROR_NEIGH_TABLE のキーを生成
4. ERROR_DB に SET し、pub/sub channel に publish

これにより syncd 内では fatal にせず継続し、エラー詳細を上位（OrchAgent → app）に伝える経路を確保する。

## 2. Consumer（ErrorListener）

App は `ErrorListener` を作って `Select` ループに addSelectable する[^1]:

```cpp
ErrorListener fpmErrorListener(APP_ROUTE_TABLE_NAME,
    (ERR_NOTIFY_FAIL | ERR_NOTIFY_POSITIVE_ACK));
Select s;
s.addSelectable(&fpmErrorListener);
```

register の引数:

- **table 名** — `APP_ROUTE_TABLE_NAME` など監視対象
- **通知種別** — `ERR_NOTIFY_FAIL` / `ERR_NOTIFY_POSITIVE_ACK` のビット OR
- **opcode フィルタ**（任意）— CREATE / DELETE / UPDATE

複数 table を監視する場合は `ErrorListener` を複数 instance 生成。

## 3. SAI 失敗 → SWSS_RC 翻訳

OrchAgent 内部に SAI status → SWSS_RC のマップを持つ[^1]:

```text
SAI_STATUS_TABLE_FULL          → SWSS_RC_FULL
SAI_STATUS_OBJECT_IN_USE       → SWSS_RC_IN_USE
SAI_STATUS_INVALID_PARAMETER   → SWSS_RC_INVALID_PARAM
SAI_STATUS_NOT_SUPPORTED       → SWSS_RC_UNAVAIL
SAI_STATUS_ITEM_NOT_FOUND      → SWSS_RC_NOT_FOUND
SAI_STATUS_NO_MEMORY           → SWSS_RC_NO_MEMORY
SAI_STATUS_ITEM_ALREADY_EXISTS → SWSS_RC_EXISTS
```

app は `rc` フィールドだけ見ればよく、SAI ヘッダ依存が消える。

## 4. Order 保証

通知は **single notification channel** を経由するため、同一 entry の create→delete→create のような連続イベントが順序通りに app に届く設計[^1]。複数 channel を使ってしまうと race が起きるため、設計上 1 つに集約される。

## 5. 現行 master 実装ファイル位置

| コンポーネント | 状態 | ファイル |
|---------------|------|---------|
| `SWSS_RC_*` enum | ✓ 取り込み済み | `sonic-swss-common/common/status_code_util.h:11-25` |
| `ERROR_DB` table 名 define | ⚠️ 未実装 | `sonic-swss-common/common/schema.h` に `ERROR_DB` / `ERROR_ROUTE_TABLE` / `ERROR_NEIGH_TABLE` のシンボル無し |
| `ErrorListener` / `ErrorReporter` | ⚠️ 未実装 | `sonic-swss/orchagent/` 配下に該当クラス無し |
| `show error-database` CLI | ⚠️ 未実装 | `sonic-utilities/` に該当無し |
| 代替: [CRM](../reference/glossary.md#term-crm) | ✓ production 稼働中 | `sonic-swss/orchagent/crmorch.cpp`、`show crm resources` |

行番号付きの確認結果と grep 結果は [error-handling-framework-in-sonic-limitations.md](error-handling-framework-in-sonic-limitations.md) を参照。

## 関連ページ

- [Error Handling Framework（概要ハブ）](error-handling-framework-in-sonic.md)
- [error-handling-framework-in-sonic-concepts.md](error-handling-framework-in-sonic-concepts.md)
- [error-handling-framework-in-sonic-operations.md](error-handling-framework-in-sonic-operations.md)
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
    | Phase 1 — 基本機能 | HLD §概要 / §設計の中核ユースケース | 部分取り込み済 — `SWSS_RC_*` enum のみ取り込み済み。`ErrorListener` / `ErrorReporter` クラス・ERROR_DB への producer 実装・CLI は未実装（本ページ「現行 master 実装ファイル位置」表参照） | ErrorListener / ErrorReporter / ERROR_DB テーブル define — 未実装 |
    | Phase 2 — 拡張機能 | HLD §拡張 / §追加要件 / §周辺統合 | — | 未実装 / 未マージ — HLD §未対応箇所、[制限事項](error-handling-framework-in-sonic-limitations.md) を参照 |
    | Phase 3 — 将来拡張 | HLD §Future Work / §将来課題 | — | 未実装 — HLD 提案段階。対応 PR は確認されていない (last_verified 時点) |

    凡例: 「実装済」=現行 master で動作確認できる範囲 / 「未実装」=HLD には記載があるが対応 PR が未マージまたは設計のみで code が存在しない範囲。
<!-- /phase-boundary -->

## 実装との乖離

`monitor: partially_implemented` — 部分実装 — [HLD](../reference/glossary.md#term-hld) の中核は実装済みだが、フィールド / API / 制約のいくつかが上流に未取り込み、または挙動が緩和されている。 本ページは split-child のため、差分の主要根拠 / 影響 / 回避策は親ページ [Error Handling Framework 内部実装 親ページ](error-handling-framework-in-sonic.md) の同セクション（`## 実装との乖離` または `!!! diff` ブロック）を参照のこと。

## 引用元

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

<!-- glossary-links-injected: 167700005048 -->
