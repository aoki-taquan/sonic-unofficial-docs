---
title: ACL_TABLE テーブル
description: "ACL_TABLE テーブル — ACL コンテナ（適用ポイント / 種別 / 段 (ingress/egress)）を定義する CONFIG_DB テーブル。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/aclorch.h
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/aclorch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
related:
  config_db:
    - ACL_TABLE
    - ACL_TABLE_TYPE
    - ACL_RULE
    - PORT
    - PORTCHANNEL
  cli:
    - config acl
  yang: []
---

# ACL_TABLE テーブル

## 概要

[ACL](../../reference/glossary.md#term-acl) コンテナ（適用ポイント / 種別 / 段 (ingress/egress)）を定義する [CONFIG_DB](../../reference/glossary.md#term-config_db) テーブル[^1]。`orchagent` の `AclOrch` がこのテーブルを購読し、[SAI](../../reference/glossary.md#term-sai) [ACL](../../reference/glossary.md#term-acl) table を生成、`ACL_RULE` に登録された各エントリを [SAI](../../reference/glossary.md#term-sai) [ACL](../../reference/glossary.md#term-acl) entry として展開する。

!!! warning "YANG 未定義"
    `ACL_TABLE` テーブルは現時点で `sonic-yang-models` に該当する YANG モジュールが存在しない。スキーマの正本は `sonic-swss/orchagent/aclorch.{h,cpp}` の定数と `sonic-swss-common/common/schema.h`。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>ACL_TABLE")]
  DM["AclOrch"]
  CDB --> DM
  APPDB[("APP_DB<br/>APP_ACL_TABLE_TABLE")]
  DM --> APPDB
  SYNCD["syncd"]
  APPDB --> SYNCD
  SAI["SAI<br/>sai_acl_api"]
  SYNCD --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
ACL_TABLE|<table_name>
```

`<table_name>` はユーザ任意の文字列。

## フィールド一覧

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `policy_desc` | string | - | テーブルの説明文 |
| `type` | string | ✅ | テーブルタイプ。事前定義型または `ACL_TABLE_TYPE` で定義したユーザ定義型 |
| `stage` | enum `ingress`/`egress` | - | ACL 適用段（既定 `ingress`） |
| `ports` | カンマ区切り leafref `PORT.name` / `PORTCHANNEL.name` / `Vlan<id>` | - | バインドポート |
| `services` | カンマ区切り string | - | (Control plane ACL) サービス名 |

## 事前定義 type

`AclOrch` が静的に許可している type:

- `L3` / `L3V6` / `L3V4V6` ... 通常の L3 ACL
- `MIRROR` / `MIRRORV6` / `MIRROR_DSCP` ... mirror セッションへ振分け
- `PFCWD` ... [PFC](../../reference/glossary.md#term-pfc) watchdog 用
- `MCLAG` ... [MCLAG](../../reference/glossary.md#term-mclag) 制御
- `MUX` ... dual-ToR mux 用
- `DROP` ... drop 専用最適化
- `MARK_META` / `MARK_META_V6` ... メタデータマーキング
- `EGR_SET_DSCP` ... egress [DSCP](../../reference/glossary.md#term-dscp) 上書き
- `CTRLPLANE` ... コントロールプレーン (`copp` 制御)

ユーザ定義型は `ACL_TABLE_TYPE|<name>` でフィールド `MATCHES` / `ACTIONS` / `BPOINT_TYPES` を指定する。

## 関連サブテーブル

- `ACL_TABLE_TYPE|<name>`
    - `MATCHES` (string list): 許可する match キー（`SRC_IP`, `DST_IP`, `L4_SRC_PORT` 等）
    - `ACTIONS` (string list): 許可する action（`PACKET_ACTION`, `REDIRECT_ACTION` 等）
    - `BPOINT_TYPES` (string list): バインド可能なポイント種別（`PORT`, `LAG`, `SWITCH`, `VLAN` 等）

## 購読者

- `orchagent` の `AclOrch`: [SAI](../../reference/glossary.md#term-sai) ACL table 生成、ポートへのバインド
- `copporch`: `CTRLPLANE` 系の登録時に連動

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `ACL_RULE`、`ACL_TABLE_TYPE`、`PORT`、`PORTCHANNEL`、`MIRROR_SESSION`
- 関連 CLI: [`config acl`](../cli/config-acl.md)
- 関連 [YANG](../../reference/glossary.md#term-yang): なし（[YANG](../../reference/glossary.md#term-yang) 未定義）

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

| 条件 | 挙動 |
|------|------|
| 未知の属性名 | ERROR ログ後 erase、skip |
| `type` 不正 | `processAclTableType()` 失敗、erase、skip |
| `ports` に存在しないポート名 | `processAclTablePorts()` 失敗、erase、skip |
| `ports` に物理 IF 以外（IN_PORTS/OUT_PORTS） | `return false`、erase |
| `stage` が INGRESS/EGRESS 以外 | `processAclTableStage()` 失敗、erase |
| `services` フィールド | `continue` で実質無視（コントロールプレーン ACL 専用） |
| `TABLE_TYPE_UNDERLAY_SET_DSCP`/`V6` | 内部で `TABLE_TYPE_MARK_META`/`V6` に変換して SAI に投入 |
| 既存 table_id への SET | `updateAclTable()` を呼んで再バインド |

<!-- evidence: sonic-net/sonic-swss/orchagent/aclorch.cpp:5346L -->
<!-- /cdb-exceptions -->

<!-- failure -->
## 失敗挙動 (Phase D)

ACL_TABLE の処理失敗は `doAclTableTask()` 内の `bAllAttributesOk` フラグと `validate()` の結果で分岐し、STATE_DB の `ACL_TABLE|<table_name>` テーブルに `status` フィールドで記録される。

### SET 時の失敗パターン

| 失敗ケース | 発生箇所 | 挙動 | STATE_DB status | retry |
|---|---|---|---|---|
| `type` 空文字 | `processAclTableType()` L5823-5826 | `bAllAttributesOk=false` → erase | `"Inactive"` | なし |
| 不明な属性名 | `doAclTableTask()` L5415-5419 | `bAllAttributesOk=false` → break → erase | `"Inactive"` | なし |
| `stage` が INGRESS/EGRESS 以外 | `processAclTableStage()` L5842-5848 | `ACL_STAGE_UNKNOWN` → `validate()` false → erase | `"Inactive"` | なし |
| `ports` に bind 不可ポート（IN_PORTS/OUT_PORTS 等） | `getAclBindPortId()` L5795-5799 | `return false` → `bAllAttributesOk=false` → erase | `"Inactive"` | なし |
| `ports` に未登録ポート | `processAclTablePorts()` L5786-5791 | `pendingPortSet.emplace()` でスキップ継続（erase しない） | 変化なし | `onPortReady()` で自動解消 |
| ユーザ定義 type 未登録 | `getAclTableType()` L5432-5437 | `it++`（保留） | 変化なし | ACL_TABLE_TYPE 登録まで無制限 |
| `type=L3V4V6` + ASIC 非サポート | `AclTable::validate()` L2737-2745 | `validate()` false → erase | `"Inactive"` | なし |
| action 非サポート | `AclTable::validate()` L2759-2766 | `validate()` false → erase | `"Inactive"` | なし |
| `addAclTable()` SAI 失敗（MIRROR capability 欠如等） | `doAclTableTask()` L5480-5485 | `it++`（retry） | `"Pending creation"` | 無制限 |
| `updateAclTable()` 失敗（ports 更新失敗） | `doAclTableTask()` L5467-5469 | `it++`（retry） | 変化なし | 無制限 |

### DEL 時の失敗パターン

| 失敗ケース | 発生箇所 | 挙動 | STATE_DB status | retry |
|---|---|---|---|---|
| 配下 ACL_RULE の SAI 削除失敗 | `removeAclTable()` L4850-4855 | `return false` → `it++` | `"Pending removal"` | 無制限 |
| `unbindAclTableFromSwitch()` 失敗 | `removeAclTable()` L4862-4867 | `return false` → `it++` | `"Pending removal"` | 無制限 |
| SAI `deleteUnbindAclTable()` 失敗 | `removeAclTable()` L4869-4908 | `return false` → `it++` | `"Pending removal"` | 無制限 |
| `removeEgrSetDscpTable()` 失敗（UNDERLAY 系） | `removeAclTable()` L4835-4840 | `return false` → `it++` | `"Pending removal"` | 無制限 |

### STATE_DB status 遷移

```
SET 受信
  ├─ bAllAttributesOk=false or validate()=false → "Inactive"  (erase, no retry)
  ├─ addAclTable() 失敗                          → "Pending creation"  (it++, retry)
  └─ addAclTable() 成功                          → "Active"   (erase)

DEL 受信
  ├─ removeAclTable() 失敗                       → "Pending removal"  (it++, retry)
  └─ removeAclTable() 成功                       → STATUS_DB エントリ削除
```

確認コマンド: `sonic-db-cli STATE_DB hgetall 'ACL_TABLE|<table_name>'`

エラーはすべて `SWSS_LOG_ERROR` でサイログ出力される。`ERROR_TABLE` への書き込みはなし。CONFIG_DB のエントリは失敗後も残る（orchagent は書き戻さない）。

> **証跡**: `doAclTableTask()` L5361-5518 全行精読、`AclTable::validate()` L2725-2769、`processAclTableType()` L5819-5831、`processAclTableStage()` L5838-5853、`processAclTablePorts()` L5776-5807、`removeAclTable()` L4829-4910、`setAclTableStatus()` L6088-6093。
<!-- /failure -->

<!-- value-behavior -->
## 値依存挙動マトリクス

### `type` 値別挙動

YANG 定義 4 値 (sonic-acl.yang:59-65): `MIRROR/MIRRORV6/L3/L3V6`。
実装定義マクロ (acltable.h:26-42): `TABLE_TYPE_L3` / `TABLE_TYPE_L3V6` / `TABLE_TYPE_L3V4V6` / `TABLE_TYPE_MIRROR` / `TABLE_TYPE_MIRRORV6` / `TABLE_TYPE_MIRROR_DSCP` / `TABLE_TYPE_PFCWD` / `TABLE_TYPE_CTRLPLANE` / `TABLE_TYPE_MCLAG` / `TABLE_TYPE_MUX` / `TABLE_TYPE_DROP` / `TABLE_TYPE_MARK_META` / `TABLE_TYPE_MARK_META_V6` / `TABLE_TYPE_EGR_SET_DSCP` / `TABLE_TYPE_UNDERLAY_SET_DSCP` / `TABLE_TYPE_UNDERLAY_SET_DSCPV6`。`processAclTableType()` は type 空文字のみ reject、それ以外はそのまま通す (aclorch.cpp:5821-5833)。

| 値 | 動作 | ASIC 確認 | evidence |
|---|---|---|---|
| `L3` | IPv4 L3 [ACL](../../reference/glossary.md#term-acl)。INGRESS/EGRESS 両対応 (`TABLE_TYPE_L3`) | なし | `acltable.h:26`, `aclorch.cpp:200,454` |
| `L3V6` | IPv6 L3 [ACL](../../reference/glossary.md#term-acl)。`IP_PROTOCOL` 使用は非推奨 (WARN ログ) (`TABLE_TYPE_L3V6`) | なし | `acltable.h:27`, `aclorch.cpp:220,1231` |
| `L3V4V6` | IPv4/IPv6 デュアルスタック ACL (`TABLE_TYPE_L3V4V6`) | `isAclL3V4V6TableSupported()` 必須 (`aclorch.cpp:2737`) | `acltable.h:28`, `aclorch.cpp:240,3541-3543` |
| `MIRROR` | INGRESS mirror セッション転送専用 (`TABLE_TYPE_MIRROR`) | `m_mirrorTableCapabilities[MIRROR]` 必須 | `acltable.h:29`, `aclorch.cpp:260,3502,3671` |
| `MIRRORV6` | IPv6 INGRESS mirror 専用。ASIC によっては MIRROR テーブルに統合 (`TABLE_TYPE_MIRRORV6`) | `m_mirrorTableCapabilities[MIRRORV6]` 必須 | `acltable.h:30`, `aclorch.cpp:279,3503,3510-3511,5811` |
| `MIRROR_DSCP` | [DSCP](../../reference/glossary.md#term-dscp) 値でミラー先決定 (`TABLE_TYPE_MIRROR_DSCP`) | なし | `acltable.h:31`, `aclorch.cpp:298` |
| `PFCWD` | [PFC Watchdog](../../reference/glossary.md#term-pfc-watchdog) 専用 (`TABLE_TYPE_PFCWD`)。BRCM DNX では `SAI_ACL_BIND_POINT_TYPE_SWITCH` | なし | `acltable.h:32`, `aclorch.cpp:316,3811-3825` |
| `CTRLPLANE` | SAI テーブル作成なし。`copporch` 経由で制御 (`TABLE_TYPE_CTRLPLANE`) | なし (stage 無視) | `acltable.h:33`, `aclorch.cpp:2727` |
| `MCLAG` | [MCLAG](../../reference/glossary.md#term-mclag) 制御専用テーブル (`TABLE_TYPE_MCLAG`) | なし | `acltable.h:35`, `aclorch.cpp:334,3791` |
| `MUX` | dual-ToR mux 専用テーブル (`TABLE_TYPE_MUX`) | なし | `acltable.h:36`, `aclorch.cpp:352` |
| `DROP` | drop 最適化テーブル (`TABLE_TYPE_DROP`; 内部クラス `IngressTableDrop` / `EgressTableDrop`) | なし | `acltable.h:37`, `aclorch.cpp:370` |
| `MARK_META` | メタデータマーキング (IPv4) (`TABLE_TYPE_MARK_META`) | なし | `acltable.h:38`, `aclorch.cpp:388` |
| `MARK_METAV6` | メタデータマーキング (IPv6) (`TABLE_TYPE_MARK_META_V6`) | なし | `acltable.h:39`, `aclorch.cpp:400` |
| `EGR_SET_DSCP` | egress [DSCP](../../reference/glossary.md#term-dscp) 書き換え専用 (`TABLE_TYPE_EGR_SET_DSCP`)。EGRESS stage 固定 | なし | `acltable.h:40`, `aclorch.cpp:412,489` |
| `UNDERLAY_SET_DSCP` | 内部で `TABLE_TYPE_MARK_META` (`MARK_META`) に変換して SAI 投入 (`TABLE_TYPE_UNDERLAY_SET_DSCP`) | なし | `acltable.h:41`, `aclorch.cpp:121 相当` |
| `UNDERLAY_SET_DSCPV6` | 内部で `TABLE_TYPE_MARK_META_V6` (`MARK_METAV6`) に変換して SAI 投入 (`TABLE_TYPE_UNDERLAY_SET_DSCPV6`) | なし | `acltable.h:42` |

### `stage` 値別挙動

lookup map: `aclStageLookUp` (aclorch.cpp:164-167)。マクロ: `STAGE_INGRESS` / `STAGE_EGRESS` (acltable.h:23-24)。不正値は `processAclTableStage()` が false を返し erase。

| 値 | SAI stage | 有効 MIRROR action | evidence |
|---|---|---|---|
| `INGRESS` (既定) | `SAI_ACL_STAGE_INGRESS` | `MIRROR_INGRESS_ACTION` 有効 (`STAGE_INGRESS` マクロ) | `aclorch.cpp:166,173,263-266` |
| `EGRESS` | `SAI_ACL_STAGE_EGRESS` | `MIRROR_EGRESS_ACTION` のみ有効 (`STAGE_EGRESS` マクロ) | `aclorch.cpp:167,185,270-272` |

### `ETHER_TYPE` / `IP_TYPE` / `PACKET_ACTION` — ACL_TABLE への直接影響なし

これら 3 フィールドは ACL_TABLE テーブル自体には存在しない (hit 数 0)。`ACL_TABLE_TYPE` サブテーブルの `MATCHES` / `ACTIONS` フィールドで許可する match / action キー名として文字列で列挙することで間接的に参照される。

### 値別 grep カバレッジ

| フィールド | 値数 | 0 hit | 証跡ファイル |
|---|---|---|---|
| `type` | 4 (YANG) / 14+ (実装) | 0 | acltable.h, aclorch.cpp |
| `stage` | 2 | 0 | aclorch.cpp |
| `ETHER_TYPE` | N/A (非フィールド) | — | — |
| `IP_TYPE` | N/A (非フィールド) | — | — |
| `PACKET_ACTION` | N/A (非フィールド) | — | — |

### 複合条件

1. `type=CTRLPLANE` → `stage` フィールドを無視し SAI テーブルを作成しない (`aclorch.cpp:2727`)
2. `type=L3V4V6` + ASIC capability なし → `isAclL3V4V6TableSupported()` が false でテーブル作成失敗 (`aclorch.cpp:2737`)
3. `type=MIRROR` / `MIRRORV6` → 起動時 ASIC capability query、capability なければ reject (`aclorch.cpp:3502-3541`)
4. `type=EGR_SET_DSCP` → EGRESS stage 固定。`stage=INGRESS` を指定しても egress 動作になる (`aclorch.cpp:489`)
<!-- /value-behavior -->

<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 自動派生

| 派生先フィールド | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| `type` | minigraph.py: AttachTo に `erspan` prefix | `MIRROR` | `minigraph.py:1218` |
| `type` | minigraph.py: AttachTo に `erspanv6` prefix | `MIRRORV6` | `minigraph.py:1220` |
| `type` | minigraph.py: AttachTo に `erspan_dscp` prefix | `MIRROR_DSCP` | `minigraph.py:1222` |
| `type` | minigraph.py: ports なし | `CTRLPLANE` | `minigraph.py:1233-1247` |
| `type` | minigraph.py: 名前に `v6` | `L3V6`、それ以外 → `L3` | `minigraph.py:1228` |
| `stage` | minigraph.py: XML `InAcl` タグ | `ingress` | `minigraph.py:1103-1104` |
| `stage` | minigraph.py: XML `OutAcl` タグ | `egress` | `minigraph.py:1106-1107` |
| `stage` (強制上書き) | `type=EGR_SET_DSCP` 設定時 | `EGRESS` 固定 (ユーザ指定無視) | `aclorch.cpp:489` |
| 内部 type 変換 | `type=UNDERLAY_SET_DSCP` | 内部で `MARK_META` に変換して SAI 投入 | `acltable.h:41`, `aclorch.cpp` |
| 内部 type 変換 | `type=UNDERLAY_SET_DSCPV6` | 内部で `MARK_METAV6` に変換して SAI 投入 | `acltable.h:42` |

### Phase 7: 条件付き登録

| 条件 | 影響 | ソース |
|---|---|---|
| `AclOrch` は常時登録 (platform 非依存) | ACL_TABLE 購読は無条件 | `orchdaemon.cpp:533,569` |
| `type=MIRROR`/`MIRRORV6` + ASIC capability なし | 起動時 SAI capability query 失敗 → テーブル作成 reject | `aclorch.cpp:3500-3541,5198-5199` |
| `type=L3V4V6` + ASIC 未サポート | `isAclL3V4V6TableSupported(stage)` → false → reject | `aclorch.cpp:2737-2739` |
| `type=CTRLPLANE` | SAI テーブル非生成。`stage` フィールド無視 | `aclorch.cpp:2727` |
| `META_DATA` 系 capability | `sai_query_attribute_capability()` 確認後に有効化 | `aclorch.cpp:3590-3659` |
| `DTelOrch` は `platform==BFN\|VS` のみ生成 | DTEL 関連 action が有効になる前提条件 | `orchdaemon.cpp:502-530` |

### グレップカバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `type` 派生 (minigraph.py) | 6 | `minigraph.py:1218-1228` |
| `stage` 派生 (minigraph.py) | 2 | `minigraph.py:1103-1107` |
| `EGR_SET_DSCP` EGRESS 強制 | 1 | `aclorch.cpp:489` |
| UNDERLAY 内部変換 | 2 | `acltable.h:41-42` |
| MIRROR capability check | 4 | `aclorch.cpp:3500-3541` |
| L3V4V6 サポート確認 | 2 | `aclorch.cpp:2737-2739` |

<!-- /derivation -->

<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

ACL_TABLE は `AclOrch::doAclTableTask()` が処理する。`type` / `stage` フィールド値によって SAI テーブルの作成方法や bind point が変わる。

| Handler | メソッド | 分岐条件 | 効果 | evidence |
|---|---|---|---|---|
| `AclOrch` | `doAclTableTask()` | `attr_name == ACL_TABLE_TYPE` | `processAclTableType()` 呼び出し — 空文字は reject、それ以外はカスタム / 組み込み type として通す | `sonic-swss/orchagent/aclorch.cpp:5380-5388` |
| `AclOrch` | `doAclTableTask()` | `attr_name == ACL_TABLE_STAGE` | `processAclTableStage()` 呼び出し — INGRESS/EGRESS 以外は `bAllAttributesOk=false` → erase | `sonic-swss/orchagent/aclorch.cpp:5400-5408` |
| `AclOrch` | `doAclTableTask()` | `attr_name == ACL_TABLE_SERVICES` | `continue`（完全無視 — コントロールプレーン ACL 専用フィールドのため）| `sonic-swss/orchagent/aclorch.cpp:5410-5413` |
| `AclOrch` | `addAclTable()` | `type == TABLE_TYPE_CTRLPLANE` | SAI テーブルを作成せず `copporch` に委譲 | `sonic-swss/orchagent/aclorch.cpp:2727` |
| `AclOrch` | `addAclTable()` | `type == TABLE_TYPE_L3V4V6` | `isAclL3V4V6TableSupported(stage)` で ASIC capability を確認、非サポート時はテーブル作成失敗 | `sonic-swss/orchagent/aclorch.cpp:2739` |
| `AclOrch` | `addAclTable()` | `type IN [MIRROR, MIRRORV6]` | `m_mirrorTableCapabilities[type]` で ASIC capability 確認、非サポート時 reject | `sonic-swss/orchagent/aclorch.cpp:3502-3541` |
| `AclOrch` | `addEgrSetDscpTable()` | `type == TABLE_TYPE_EGR_SET_DSCP` | 内部で `TABLE_TYPE_MARK_META` / `TABLE_TYPE_MARK_METAV6` へ変換して SAI 投入、stage を EGRESS 固定 | `sonic-swss/orchagent/aclorch.cpp:4444-4539` |

> **スキャン証跡**: `doAclTableTask()` L5346-5520 全行読了 + `addAclTable()` / `addEgrSetDscpTable()` 参照。7 件分岐抽出。Phase 6/7 derivation ブロック再確認: minigraph.py type/stage 派生・UNDERLAY 変換・MIRROR capability check — 実ソースと整合、誤読なし。

<!-- /handler-branching -->

<!-- defaults -->
## コード由来の暗黙デフォルト (Phase A)

YANG スキーマに `default` 宣言がない (`ACL_TABLE` は YANG 未定義) 状態で、C++ struct 初期化・Python CLI fallback・実装読み捨てによって実質的に適用されるデフォルト値を列挙する。

| フィールド | YANG default | コード由来デフォルト | 発生源 |
|---|---|---|---|
| `stage` | なし | **`INGRESS`** | C++ struct 初期値 `acl_stage_type_t stage = ACL_STAGE_INGRESS` (`aclorch.h:543`) + CLI `default="ingress"` (`config/main.py:8081`) |
| `policy_desc` | なし | **`<table_name>`** (CLI 経由) / `""` (直接書き込み) | `parse_acl_table_info()` の `else` 分岐 `table_info["policy_desc"] = table_name` (`main.py:8047`) |
| `type` | なし | **なし** (必須フィールド) | `processAclTableType()` — 空文字のみ reject、省略時は `bAllAttributesOk=false` → erase (`aclorch.cpp:5823`) |
| `ports` | なし | **全有効 ACL ポート** (CLI 経由) / `[]` (直接書き込み) | `get_acl_bound_ports()` fallback (`main.py:8059`) |
| `services` | なし | **なし** (読み捨て) | `doAclTableTask()` 内で `continue` — 内部状態に影響しない (`aclorch.cpp:5413`) |

### `stage` の詳細

C++ の `AclTable` クラスは `stage = ACL_STAGE_INGRESS` でメンバを初期化する (`aclorch.h:543`)。CONFIG_DB エントリに `stage` フィールドがなければ `processAclTableStage()` が呼ばれず INGRESS がそのまま `validate()` に渡る。CLI でも `-s` 省略時に `"ingress"` をセット済みで書き込むため、2 重に担保されている。

### `policy_desc` の詳細

`config acl add table` 実行時に `-d` を省略すると `policy_desc` に `table_name` 文字列が設定される。REST/minigraph/直接書き込みでは `policy_desc` は任意で、省略時は orchagent の `AclTable::description` が空文字列デフォルト。orchagent は `description` を SAI 属性として渡さないため SAI ハードウェアに影響なし（ログ・`show` 表示のみ）。

### 内部自動付与 action/match (YANG 外)

`addMandatoryActions()` (`aclorch.cpp:2563`) — ASIC が action list mandatory と報告する場合、ユーザ指定 action が空なら `SAI_ACL_ACTION_TYPE_COUNTER` を自動追加し、さらに `defaultAclActionList` テーブルから type/stage 組み合わせで追加する。これは CONFIG_DB フィールドではなく SAI 属性 (`SAI_ACL_TABLE_ATTR_ACL_ACTION_TYPE_LIST`) として展開される。主要な自動付与:

| type | INGRESS 自動付与 | EGRESS 自動付与 |
|---|---|---|
| `L3` / `L3V6` / `L3V4V6` | `PACKET_ACTION`, `REDIRECT` | `PACKET_ACTION`, `REDIRECT` |
| `MIRROR` | `MIRROR_INGRESS`, `MIRROR_EGRESS` | `MIRROR_EGRESS` |

`addStageMandatoryMatchFields()` (`aclorch.cpp:2632`) — type/stage 組み合わせに応じて SAI match 属性を自動付与する。`SAI_ACL_TABLE_ATTR_FIELD_ACL_RANGE_TYPE` (L4 ポート範囲) は BRCM プラットフォームの EGRESS stage では省略される (`addStageMandatoryRangeFields()` が `false` を返す)。これらも CONFIG_DB フィールドではなく SAI 属性として展開される。

<!-- /defaults -->

<!-- ref-triangle:start -->

## 関連リファレンス

- CLI: [`config acl`](../cli/config-acl.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: フィールド名・type 値は `sonic-swss/orchagent/aclorch.{h,cpp}` (sha `43055961`) のマクロ定義と type バリデーションロジックから抽出。<https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/aclorch.cpp>

## 関連ページ
- [HLD: ACL の基本設計](../../acl-qos/acl-support-in-sonic.md)
- [CLI: config acl](../cli/config-acl.md)
- [CLI: show acl](../cli/show-acl.md)
- [CONFIG_DB: ACL_RULE](acl-rule.md)

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: ACL / CoPP / Mirror / Packet Action](../../topics/07-acl-copp-mirror/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `ACL_TABLE|<table-name>`。
- `type`: `L3` / `L3V6` / `MIRROR` / `MIRRORV6` / `CTRLPLANE` / `MCLAG` 等。
- `stage`: `INGRESS` / `EGRESS`。
- `ports`: `["Ethernet0", "PortChannel0001"]` のように紐付け対象を列挙。
- `policy_desc`: 運用識別用。

### よくある誤設定

- `type` と紐付けポートの能力（V4/V6/MIRROR）が不一致だと aclorch が SAI でテーブルを作らない。
- `stage: EGRESS` を ASIC が未サポートなのに指定すると syslog にエラー、何も適用されない。
- `ports` を空にすると ACL_RULE は [CONFIG_DB](../../reference/glossary.md#term-config_db) に入っても hardware に降りない。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'ACL_TABLE|EVERFLOW'
show acl table
aclshow -a
```
<!-- /ops-hint -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

CONFIG_DB の `ACL_TABLE` テーブルを書き込むコードパスを網羅する。

### CLI

`sonic-utilities/config/main.py:8084-8123` — `config acl add table` / `config acl remove table`

```python
config_db.set_entry("ACL_TABLE", table_name, table_info)   # 追加
config_db.set_entry("ACL_TABLE", table_name, None)          # 削除
```

- 入力プロトコル: CLI 引数 (`table_name`, `table_type`, `-d desc`, `-p ports`, `-s stage`)
- `stage` 未指定時デフォルト: `"ingress"` (`parse_acl_table_info()` L8041)
- ports: カンマ区切り文字列 → リストに変換

### minigraph

`sonic-buildimage/src/sonic-config-engine/minigraph.py:1102-1249, 2671`

XML `<AclInterface>` 要素から `ACL_TABLE` エントリを生成し CONFIG_DB に書き込む。

| XML 要素 / 属性 | 生成フィールド | 生成値 |
|---|---|---|
| `<InAcl>` タグ | `stage` | `ingress` |
| `<OutAcl>` タグ | `stage` | `egress` |
| `<AttachTo>` に `erspan` prefix | `type` | `MIRROR` |
| `<AttachTo>` に `erspanv6` prefix | `type` | `MIRRORV6` |
| `<AttachTo>` に `erspan_dscp` prefix | `type` | `MIRROR_DSCP` |
| interface list が空 | `type` | `CTRLPLANE` |
| ACL 名に `v6` を含む、それ以外 | `type` | `L3V6` / `L3` |

入力プロトコル: minigraph XML (`<AclInterface>`, `<InAcl>`, `<OutAcl>`, `<AttachTo>` XPath)

### REST / gNMI

`sonic-mgmt-common/translib/acl_app.go:95-300`

- REST path: `PATCH /openconfig-acl:acl/acl-sets/acl-set/{name}/{type}`
- gNMI path: `/openconfig-acl:acl/acl-sets/acl-set[name=...][type=...]`
- `AclApp.processCreate()` → `processCommon()` → `d.SetEntry(app.aclTs, ...)` で CONFIG_DB の ACL_TABLE に書き込み
- OpenConfig type → SONiC type マッピング: `ACL_IPV4` → `L3`、`ACL_IPV6` → `L3V6` など

### db_migrator

なし。ACL_TABLE の migration ステップは `db_migrator.py` に存在しない。

### build-time デフォルト

なし。`init_cfg.json.j2` および `qos_config.j2` に ACL_TABLE エントリは存在しない。

### hard-coded デフォルト

なし。

### 死活 (runtime injection)

`orchagent` の `AclOrch` は ACL_TABLE を購読するのみ（書き込みなし）。

<!-- /entry-points -->

<!-- ordering -->
## 書込み順依存 (Phase B)

### 前提: allPortsReady() ガード

`AclOrch::doTask()` (`aclorch.cpp:4276`) は `gPortsOrch->allPortsReady()` が false の間は即 return する。`ACL_TABLE` / `ACL_TABLE_TYPE` / `ACL_RULE` すべての処理が**完全にブロック**される。orchdaemon が PortsOrch の初期化完了を保証するため、通常は意識不要だが起動シーケンス中の早期書き込みは処理待ちになる。

### ACL_TABLE_TYPE (ユーザ定義型) が先行必須

`doAclTableTask()` L5432-5437: `getAclTableType()` が nullptr を返すと `it++; continue` で ACL_TABLE エントリを**保留キューに残す**。組み込み型（`L3`/`MIRROR`/`CTRLPLANE` 等）はコンストラクタ時点で登録済みのため不要。ユーザ定義型を使う場合のみ、`ACL_TABLE_TYPE|<name>` を ACL_TABLE SET より先に書き込むこと。

```
SET ACL_TABLE_TYPE|<type_name>  MATCHES=...,ACTIONS=...,BPOINT_TYPES=...
SET ACL_TABLE|<table_name>      type=<type_name> stage=ingress ports=...
SET ACL_RULE|<table_name>|<rule_name>  PRIORITY=...
```

### ports フィールドのポート未登録（自動遅延）

未登録ポートは `pendingPortSet` に追加されるが ACL_TABLE 自体は作成される。`onPortReady()` コールバックで PORT 登録完了時に自動バインドされる (`aclorch.cpp:2884`)。erase はされないため設定は保持される。

### ACL_RULE は ACL_TABLE 作成後に書き込む

`doAclRuleTask()` L5552-5565: `table_oid == SAI_NULL_OBJECT_ID` の間は `it++; continue` で待機（自動 wait loop）。`ACL_TABLE` の SAI 作成完了後、次の orchagent ループで自動処理される。**先行して書き込んでも失われない**が、ACL_TABLE が作成されるまで SAI には反映されない。

### type / stage 変更には DEL → SET が必要

`doAclTableTask()` L5450-5454: 既存 table の `type` または `stage` が変更された場合、orchagent は内部で既存テーブルを削除してから再作成する（配下の ACL_RULE も消える）。変更前に `DEL ACL_RULE|<table>|*` を明示削除することを推奨。`ports` のみ変更する場合は `updateAclTable()` で差分適用されるため DEL 不要。

### 安全な DEL 順序

```
DEL ACL_RULE|<table_name>|<rule_name>    # 配下ルールを先に削除（推奨）
DEL ACL_TABLE|<table_name>               # テーブル削除（orchagent 内部でも clear() を呼ぶ）
DEL ACL_TABLE_TYPE|<type_name>           # ユーザ定義 type を削除する場合は最後
```

`removeAclTable()` (`aclorch.cpp:4850`) は内部で `clear()` を呼び配下 ACL_RULE を自動削除するが、CONFIG_DB 上の `ACL_RULE` エントリは残る。orchagent 再起動後に孤立エントリが "Wait for ACL table" ループに入るため、CLI/REST 経由では ACL_RULE を先に明示削除する。

| 依存関係 | 方向 | 緩和策 |
|----------|------|--------|
| allPortsReady() 完了 → ACL_TABLE 処理 | 強制先行 | orchdaemon が自動管理 |
| ACL_TABLE_TYPE SET → ACL_TABLE SET（ユーザ定義型） | 論理的先行 | 保留キューで自動調停 |
| PORT/PORTCHANNEL SET → ports バインド | 部分先行 | pendingPortSet + onPortReady() |
| ACL_TABLE SET → ACL_RULE SET（SAI 反映） | 必須 | 自動 wait loop |
| type/stage 変更: DEL → SET | 必須 | SET のみでも動作するが配下 ACL_RULE 消失 |
| ACL_TABLE DEL → ACL_TABLE_TYPE DEL | 推奨 | 強制ではないが論理的に必要 |

> **スキャン証跡**: `doAclTableTask()` L5346-5518 全行精読、`doAclTableTypeTask()` L5738-5774、`removeAclTable()` L4829-4910、`processAclTablePorts()` L5776-5807、`doAclRuleTask()` L5520-5566 参照。
<!-- /ordering -->

<!-- runtime-trace -->
## 起動経路 (Direction B: CFG → APPL → SAI)

### 段階 1: Consumer 登録

`orchdaemon.cpp:408-419` で `CONFIG_DB / ACL_TABLE` (`"ACL_TABLE"`)、`CONFIG_DB / ACL_TABLE_TYPE`、`CONFIG_DB / ACL_RULE` および対応する `APP_DB` 版の計 6 本の `TableConnector` を作成し `AclOrch` コンストラクタに渡す。`AclOrch` は `gOrchDaemon->orchList` に登録され、メインループで `doTask()` (`aclorch.cpp:4272`) が呼ばれる。`table_name` が `CFG_ACL_TABLE_TABLE_NAME` または `APP_ACL_TABLE_TABLE_NAME` に一致すると `doAclTableTask()` に委譲される。追加コンシューマ: `NatMgr` (`cfgmgr/natmgrd.cpp:119`) が `ACL_TABLE` を購読して NAT 設定に連動。

### 段階 2: CFG → APPL 翻訳

`ACL_TABLE` は `cfgmgr` 中間層を**持たない**。`AclOrch` が `CONFIG_DB` を直接購読し `doAclTableTask()` でフィールドを解釈する。`APP_DB` への中間書き込みなし。主な変換:

| CFG フィールド | 変換 | 備考 |
|---|---|---|
| `type` | `processAclTableType()` → `AclTableType` オブジェクト | 空文字は reject、`UNDERLAY_SET_DSCP` → 内部で `MARK_META` に変換 |
| `stage` | `processAclTableStage()` → `STAGE_INGRESS` / `STAGE_EGRESS` | 不正値は erase |
| `ports` | `processAclTablePorts()` → PORT OID 解決 | SAI bind point (port/LAG/VLAN) に変換 |
| `services` | `continue` で無視 | CTRLPLANE ACL 専用フィールド |

### 段階 3: APPL → SAI

`AclTable::create()` → `sai_acl_api->create_acl_table(&m_oid, gSwitchId, attrs, ...)` (`aclorch.cpp:2847`) を呼び出す。設定 SAI 属性: `SAI_ACL_TABLE_ATTR_ACL_BIND_POINT_TYPE_LIST`、`SAI_ACL_TABLE_ATTR_ACL_ACTION_TYPE_LIST`、`SAI_ACL_TABLE_ATTR_ACL_STAGE`、`SAI_ACL_TABLE_ATTR_FIELD_*` (match フィールド群)。ポートバインドは別途 `sai_port_api->set_port_attribute(SAI_PORT_ATTR_INGRESS_ACL / EGRESS_ACL)` 等を呼ぶ。`type=MIRROR/MIRRORV6` は ASIC capability 確認 (`aclorch.cpp:3502-3541`)、`type=L3V4V6` は `isAclL3V4V6TableSupported()` 確認 (`aclorch.cpp:2737`)、`type=CTRLPLANE` は SAI テーブル非作成 (`aclorch.cpp:2727`)。

### 段階 4: タイミング・副作用

- **config reload**: warm start 非対応。reload 時は全エントリを再処理し `create_acl_table` を再投入。
- **runtime 変更 (SET)**: 既存 table 検出時は `updateAclTable()` → ポート bind/unbind を差分適用 (`aclorch.cpp:5446-5520`)。`type` / `stage` は作成後変更不可 (create-only 属性)。
- **warm-restart**: `AclOrch` は `onWarmBootEnd()` を実装しない。orchagent 全体の `warmRestoreAndSyncUp()` (`orchdaemon.cpp:872`) でリカバリ。
- **DEL**: バインドを外した後 `sai_acl_api->remove_acl_table()` を呼ぶ。配下に ACL_RULE が残ると SAI エラー。
- **CRM 連携**: 作成/削除時に `gCrmOrch->incCrmAclUsedCounter()` / `decCrmAclUsedCounter()` (`aclorch.cpp:2855`)。

<!-- /runtime-trace -->
<!-- glossary-links-injected: 9f69b0796e2c -->
