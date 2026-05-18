---
title: DSCP_TO_PG_MAP テーブル（非実在）
description: "DSCP_TO_PG_MAP — このテーブルは SONiC CONFIG_DB に存在しない。DSCP から Priority Group へのマッピングは DSCP_TO_TC_MAP と TC_TO_PRIORITY_GROUP_MAP の 2 段構成で実現される。"
area: reference
hard: 0
verification: discrepancy-found
last_verified: 2026-05-15
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/qosorch.cpp
    ref: master
  - repo: sonic-net/sonic-swss
    path: orchagent/qosorch.h
    ref: master
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-dscp-tc-map.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-tc-priority-group-map.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - DSCP_TO_TC_MAP
    - TC_TO_PRIORITY_GROUP_MAP
    - PORT_QOS_MAP
  cli:
    - config qos
---

# DSCP_TO_PG_MAP テーブル

!!! warning "このテーブルは SONiC に存在しない"
    `DSCP_TO_PG_MAP` という CONFIG_DB テーブルは SONiC master ブランチに存在しない。DSCP 値から Priority Group (PG) へのマッピングは **2 段構成** で実現される。

## 概要

SONiC の QoS アーキテクチャでは DSCP 値を PG に直接マッピングするテーブルを持たない。実際の経路は以下のとおり:

```
DSCP (0-63)
  ──→ Traffic Class  (DSCP_TO_TC_MAP テーブル)
  ──→ Priority Group (TC_TO_PRIORITY_GROUP_MAP テーブル)
```

`PORT_QOS_MAP` テーブルの `dscp_to_tc_map` leaf と `tc_to_pg_map` leaf を組み合わせることで、入口ポートの DSCP 値が最終的に ingress buffer priority group へ到達する。

## 実際のアーキテクチャ

<!-- cdb-mermaid -->
### データフロー

```mermaid
flowchart LR
  PKT["受信パケット<br/>DSCP 0-63"]
  D2T[("CONFIG_DB<br/>DSCP_TO_TC_MAP")]
  T2P[("CONFIG_DB<br/>TC_TO_PRIORITY_GROUP_MAP")]
  PORT[("CONFIG_DB<br/>PORT_QOS_MAP")]
  ORC["QosOrch"]
  SAI["SAI<br/>sai_qos_map_api"]

  PORT -->|dscp_to_tc_map| D2T
  PORT -->|tc_to_pg_map| T2P
  D2T --> ORC
  T2P --> ORC
  ORC --> SAI
  PKT -->|ingress| SAI
```
<!-- /cdb-mermaid -->

### 段階 1 — DSCP → Traffic Class

`DSCP_TO_TC_MAP|<name>` テーブルに DSCP 値（0-63）→ Traffic Class 値（0-7）のエントリを定義する。`PORT_QOS_MAP.<port>.dscp_to_tc_map` から参照される。`qosorch` が `SAI_QOS_MAP_TYPE_DSCP_TO_TC` オブジェクトを生成する。

詳細: [DSCP_TO_TC_MAP](dscp-to-tc-map.md)

### 段階 2 — Traffic Class → Priority Group

`TC_TO_PRIORITY_GROUP_MAP|<name>` テーブルに TC 値（0-7）→ PG 値（0-7）のエントリを定義する。`PORT_QOS_MAP.<port>.tc_to_pg_map` から参照される。`qosorch` が `SAI_QOS_MAP_TYPE_TC_TO_PRIORITY_GROUP` オブジェクトを生成する。

詳細: [TC_TO_PRIORITY_GROUP_MAP](tc-to-priority-group-map.md)

## コード証拠

`qosorch.cpp:80-96` の `m_qos_maps` 初期化リストには以下のテーブルが登録されているが、`DSCP_TO_PG_MAP` は含まれない[^1]:

```cpp
type_map QosOrch::m_qos_maps = {
    {CFG_DSCP_TO_TC_MAP_TABLE_NAME, ...},              // "DSCP_TO_TC_MAP"
    {CFG_TC_TO_PRIORITY_GROUP_MAP_TABLE_NAME, ...},    // "TC_TO_PRIORITY_GROUP_MAP"
    // DSCP_TO_PG_MAP に対応するエントリはない
    ...
};
```

`qosorch.cpp:1329,1342` の handler 登録でも対応なし:

```cpp
m_qos_handler_map.insert(qos_handler_pair(CFG_DSCP_TO_TC_MAP_TABLE_NAME, &QosOrch::handleDscpToTcTable));
m_qos_handler_map.insert(qos_handler_pair(CFG_TC_TO_PRIORITY_GROUP_MAP_TABLE_NAME, &QosOrch::handleTcToPgTable));
// DSCP_TO_PG_MAP ハンドラは存在しない
```

`sonic-buildimage/src/sonic-yang-models/yang-models/` には `sonic-dscp-pg-map.yang` も存在しない[^2]。

<!-- defaults -->
## 暗黙デフォルト・コード由来挙動

`DSCP_TO_PG_MAP` テーブル自体が存在しないため、フィールドデフォルトは定義されない。2 段マッピングを構成する各テーブルのデフォルトは以下のとおり:

### DSCP_TO_TC_MAP のデフォルト（段階 1）

| フィールド | デフォルト有無 | 内容 |
|-----------|--------------|------|
| `name` | プラットフォーム依存 | ストレージバックエンドプラットフォームのみ `qos_config.j2` が `AZURE` / `AZURE_UPLINK` という名前のマップを自動注入する |
| `dscp` (key) | なし | 0-63 の値を明示的に設定する必要あり |
| `tc` | なし | 0-7 の Traffic Class 値を明示的に設定する必要あり |

`qos_config.j2` フォールバック AZURE マップのデフォルト値（抜粋）:

| DSCP | TC | 備考 |
|------|----|------|
| 3, 4 | 3, 4 | lossless クラス |
| 8 | 0 | CS1: best-effort |
| 46 | 5 | EF: expedited forwarding |
| 48 | 6 | CS6: network control |
| その他 | 1 | 低優先度デフォルト |

### TC_TO_PRIORITY_GROUP_MAP のデフォルト（段階 2）

| フィールド | デフォルト有無 | 内容 |
|-----------|--------------|------|
| `name` | プラットフォーム依存 | `qos_config.j2` の `generate_tc_to_pg_map()` マクロが platform 別に生成 |
| `tc` (key) | なし | 0-7 の Traffic Class 値を明示的に設定する必要あり |
| `pg` | なし | `pattern "[0-7]?"` — 0-7 または空文字を許可する YANG 制約 |

`qosorch.cpp:895` では `(uint8_t)stoi(fvValue(*i))` で pg 値を変換しており、例外処理なし。非整数文字列が CONFIG_DB に書き込まれると `std::invalid_argument` が伝播する。

> **Evidence**: `qosorch.cpp:80-96` (m_qos_maps 初期化), `qosorch.cpp:1329,1342` (handler 登録), `qosorch.cpp:880-910` (TcToPgMapHandler), `sonic-port-qos-map.yang:85-91,129-134` (leafref)

<!-- /defaults -->

<!-- ordering -->
## 書込み順依存 (Phase B)

`DSCP_TO_PG_MAP` テーブルは存在しないため、実際の 2 段マッピングチェーン全体の書き込み順依存を記述する。

### allPortsReady() ブロック

`QosOrch::doTask()` (`qosorch.cpp:2258`) は `gPortsOrch->allPortsReady()` が false の間は即 return する。`DSCP_TO_TC_MAP`・`TC_TO_PRIORITY_GROUP_MAP`・`PORT_QOS_MAP` すべての処理が**完全にブロック**される。orchdaemon が PortsOrch の初期化完了を保証するため通常は意識不要だが、起動シーケンス中の早期書き込みは処理待ちになる。

### SET 順序（マップ先行）

```
SET DSCP_TO_TC_MAP|<map_name>           # 段階 1 マップを先に作成
SET TC_TO_PRIORITY_GROUP_MAP|<pg_name>  # 段階 2 マップを先に作成
SET PORT_QOS_MAP|<port>  dscp_to_tc_map=<map_name> tc_to_pg_map=<pg_name>
```

`handlePortQosMapTable()` (`qosorch.cpp:2124`) は `resolveFieldRefValue()` を呼び、参照先マップが未作成の場合は `task_need_retry` を返す。orchagent のメインループで自動リトライされるが、マップが存在するまで PORT_QOS_MAP の SAI 反映はブロックされる。

### DEL 順序（参照元先行）

```
DEL PORT_QOS_MAP|<port>                 # 参照を先に解除
DEL DSCP_TO_TC_MAP|<map_name>           # 参照がなくなってから削除
DEL TC_TO_PRIORITY_GROUP_MAP|<pg_name>  # 参照がなくなってから削除
```

汎用マップハンドラ (`qosorch.cpp:181`) は `isObjectBeingReferenced()` が true の間は DEL 要求に対して `m_pendingRemove=true` をセットして `task_need_retry` を返す。`PORT_QOS_MAP` の参照が解除されるまで SAI 削除は実行されない。

### 依存関係サマリ

| 依存関係 | 方向 | 緩和策 |
|---------|------|-------|
| allPortsReady() 完了 → 全 QosOrch 処理 | 強制先行 | orchdaemon が自動管理 |
| DSCP_TO_TC_MAP SET → PORT_QOS_MAP SET (dscp_to_tc_map) | 必須先行 | task_need_retry で自動リトライ |
| TC_TO_PRIORITY_GROUP_MAP SET → PORT_QOS_MAP SET (tc_to_pg_map) | 必須先行 | task_need_retry で自動リトライ |
| PORT_QOS_MAP DEL → DSCP_TO_TC_MAP DEL | 必須先行 | m_pendingRemove + task_need_retry |
| PORT_QOS_MAP DEL → TC_TO_PRIORITY_GROUP_MAP DEL | 必須先行 | m_pendingRemove + task_need_retry |

> **スキャン証跡**: `QosOrch::doTask()` L2254-2299、`handlePortQosMapTable()` L2046-2134、汎用マップハンドラ L130-196 参照。
<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`DSCP_TO_PG_MAP` テーブルは存在しないため、2 段マッピングを構成する実在テーブルへの参照関係を示す。

> 証跡: `meta/_intermediate/cdb-flow/dscp-to-pg-map-cross-refs.md`

### DSCP_TO_TC_MAP を参照する側（段階 1 マップの消費元）

| 参照元テーブル | YANG leafref | 参照フィールド | 未解決時の挙動 | 参照元 evidence |
|---------------|:------------:|--------------|--------------|----------------|
| `PORT_QOS_MAP` (CONFIG_DB) | ✅ | `dscp_to_tc_map` | `resolveFieldRefValue()` 失敗 → `task_need_retry`、マップ作成後に自動再試行 | `qosorch.cpp:100,2021-2026,2124-2129` |
| `TUNNEL_DECAP_TABLE` (APPL_DB) | ✗ | `decap_dscp_to_tc_map` | `resolveTunnelQosMap()` 失敗 → `task_need_retry` | `tunneldecaporch.cpp:213-220` |

### TC_TO_PRIORITY_GROUP_MAP を参照する側（段階 2 マップの消費元）

| 参照元テーブル | YANG leafref | 参照フィールド | 未解決時の挙動 | 参照元 evidence |
|---------------|:------------:|--------------|--------------|----------------|
| `PORT_QOS_MAP` (CONFIG_DB) | ✅ | `tc_to_pg_map` | `resolveFieldRefValue()` 失敗 → `task_need_retry`、マップ作成後に自動再試行 | `qosorch.cpp:106,2124-2129` |
| `TUNNEL_DECAP_TABLE` (APPL_DB) | ✗ | `decap_tc_to_pg_map` | `resolveTunnelQosMap()` 失敗 → `task_need_retry` | `tunneldecaporch.cpp:230-235` |

!!! note "DSCP_TO_PG_MAP は存在しないため参照元は持たない"
    `DSCP_TO_PG_MAP` というキーで CONFIG_DB に書いても `qosorch` はハンドラを持たず完全に無視する。上記の参照関係はすべて 2 段パイプラインの構成要素（`DSCP_TO_TC_MAP` および `TC_TO_PRIORITY_GROUP_MAP`）に対するものである。
<!-- /cross-refs -->

## 制約

- `DSCP_TO_PG_MAP` テーブルは存在しないため、このキー名で CONFIG_DB に書き込んでも `qosorch` は無視する
- 実際の DSCP → PG 経路を設定するには `DSCP_TO_TC_MAP`、`TC_TO_PRIORITY_GROUP_MAP`、`PORT_QOS_MAP` の 3 テーブルを適切に設定する必要がある

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `DSCP_TO_TC_MAP`、`TC_TO_PRIORITY_GROUP_MAP`、`PORT_QOS_MAP`
- 関連 CLI: `config qos`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-dscp-tc-map`、`sonic-tc-priority-group-map`

## 引用元

[^1]: QosOrch m_qos_maps 初期化: `sonic-swss/orchagent/qosorch.cpp:80-96`. <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/qosorch.cpp>
[^2]: YANG モデル一覧: `sonic-buildimage/src/sonic-yang-models/yang-models/`. <https://github.com/sonic-net/sonic-buildimage/tree/master/src/sonic-yang-models/yang-models>

## 関連ページ

- [CONFIG_DB: DSCP_TO_TC_MAP](dscp-to-tc-map.md)
- [CONFIG_DB: TC_TO_PRIORITY_GROUP_MAP](tc-to-priority-group-map.md)
- [CONFIG_DB: PORT_QOS_MAP](port-qos-map.md)
