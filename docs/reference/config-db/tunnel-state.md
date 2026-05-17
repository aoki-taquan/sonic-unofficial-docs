---
title: TUNNEL STATE_DB テーブル群
description: "STATE_DB TUNNEL 関連テーブル — tunneldecaporch / VxlanTunnelOrch / VxlanMgr が書き込む TUNNEL_DECAP_TABLE・TUNNEL_DECAP_TERM_TABLE・VXLAN_TUNNEL_TABLE のフィールド・デフォルト・書き込み条件の参照。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-15
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/tunneldecaporch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/vxlanorch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: cfgmgr/vxlanmgr.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
related:
  config_db:
    - TUNNEL
    - TUNNEL_DECAP_TABLE
    - TUNNEL_DECAP_TERM
    - VXLAN_TUNNEL
  cli: []
  yang:
    - sonic-tunnel
    - sonic-vxlan
---

# TUNNEL STATE_DB テーブル群

## 概要

[STATE_DB](../../reference/glossary.md#term-state_db) には [TUNNEL](./tunnel.md) の処理結果を反映する複数のテーブルが存在する。書き込み元はオーケストレーター（[orchagent](../../reference/glossary.md#term-orchagent)）と cfgmgr（vxlanmgrd）の両方。

| STATE_DB テーブル名 | 書き込み元 | 役割 |
|--------------------|-----------|------|
| `TUNNEL_DECAP_TABLE` | `tunneldecaporch` | APPL_DB `TUNNEL_DECAP_TABLE` の SAI 反映状態ミラー |
| `TUNNEL_DECAP_TERM_TABLE` | `tunneldecaporch` | Decap term エントリの SAI 反映状態ミラー |
| `VXLAN_TUNNEL_TABLE` | `VxlanTunnelOrch` | VxLAN トンネルの作成状態 + operstatus |
| `VXLAN_TABLE` | `VxlanMgr` | VxLAN netdevice 作成成功フラグ |

## TUNNEL_DECAP_TABLE

### key 構造

```text
TUNNEL_DECAP_TABLE|<tunnel_name>
```

### フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `tunnel_type` | string | `IPINIP` 固定。省略された場合はこのフィールドなし |
| `dscp_mode` | string | `uniform` または `pipe` |
| `ecn_mode` | string | `copy_from_outer` または `standard` |
| `encap_ecn_mode` | string | `standard` のみ有効 |
| `ttl_mode` | string | `uniform` または `pipe` |

書き込みは `setDecapTunnelStatus()` が `APPEND_IF_NOT_EMPTY` マクロを使用するため、**内部キャッシュで空のフィールドは STATE_DB に書かれない**。

### 書き込みタイミング

1. 新規トンネル作成: `addDecapTunnel()` 完了後
2. 既存トンネル更新（`dscp_mode` / `ttl_mode` / QoS マップ変更）: SET_COMMAND 処理後
3. 削除: `removeDecapTunnel()` で `del()` — ただし ref count > 0 の間は消去されない

## TUNNEL_DECAP_TERM_TABLE

### key 構造

```text
TUNNEL_DECAP_TERM_TABLE|<tunnel_name>|<dst_ip_prefix>
```

### フィールド

| フィールド | 型 | 省略時 | 説明 |
|-----------|----|--------|------|
| `term_type` | string | 常に存在 (`P2MP` がデフォルト) | `P2P` / `P2MP` / `MP2MP` |
| `src_ip` | string | フィールドなし | P2P/MP2MP 時は必須。省略で P2MP |
| `subnet_type` | string | フィールドなし | `vlan` または `vip`。MP2MP subnet decap 専用 |

`term_type` のデフォルト `P2MP` は `doDecapTunnelTermTask()` 内の変数初期値 (`TUNNEL_TERM_TYPE_P2MP`) に由来する。

### 書き込みタイミング

- `addDecapTunnelTermEntry()` 成功後に `setDecapTunnelTermStatus()` が呼ばれる
- 削除: `removeDecapTunnelTermStatus()` で `del()`

## VXLAN_TUNNEL_TABLE

### key 構造

```text
VXLAN_TUNNEL_TABLE|<tunnel_name>
```

### フィールド

| フィールド | 型 | 初期値 | 説明 |
|-----------|----|--------|------|
| `src_ip` | string | — | VxLAN トンネル送信元 IP |
| `dst_ip` | string | — | VxLAN トンネル宛先 IP (P2P の場合) |
| `tnl_src` | string | — | `CLI` (config経由) または `EVPN` (BGP EVPN経由) |
| `operstatus` | string | `down` | 作成直後は常に `down`。ポート UP で `up` に遷移 |

`operstatus` の初期値 `"down"` は `addRemoveStateTableEntry()` でハードコードされている（vxlanorch.cpp L1942）。

### 書き込みタイミング

- トンネル作成: `addRemoveStateTableEntry(add=true)` — `operstatus=down` で書き込み
- ポート状態変化: `operstatus` を `up`/`down` に更新
- 削除: `addRemoveStateTableEntry(add=false)` で `del()`
- Warm reboot: 既存エントリが存在する場合は上書きしない（重複防止）

## VXLAN_TABLE

### key 構造

```text
VXLAN_TABLE|<vxlan_name>
```

### フィールド

| フィールド | 型 | 値 | 説明 |
|-----------|----|-----|------|
| `state` | string | `ok` (固定) | VxLAN netdevice 作成成功を示す。失敗時は書かれない |

`createVxlan()` (vxlanmgr.cpp) 成功時のみ `"state"="ok"` を書き込む。値はハードコード固定。

## 関連 CONFIG_DB / CLI

- 元データ: [CONFIG_DB TUNNEL](./tunnel.md)、[VXLAN_TUNNEL](./vxlan-tunnel.md)
- 関連 APPL_DB: `TUNNEL_DECAP_TABLE`、`TUNNEL_DECAP_TERM_TABLE`、`VXLAN_TUNNEL_TABLE`

<!-- defaults -->
## 暗黙デフォルト・コード由来挙動 (Phase A)

以下は設定省略時にコード実装から導出される暗黙の挙動。

### TUNNEL_DECAP_TABLE — フィールド省略時の挙動

| フィールド | 省略/未設定時の STATE_DB 挙動 | ソース証跡 |
|-----------|------------------------------|-----------|
| `tunnel_type` | `APPEND_IF_NOT_EMPTY` マクロにより STATE_DB に書かれない | `tunneldecaporch.cpp` L1526 |
| `dscp_mode` | 空の場合は STATE_DB に書かれない | `tunneldecaporch.cpp` L1527 |
| `ecn_mode` | 空の場合は STATE_DB に書かれない | `tunneldecaporch.cpp` L1528 |
| `encap_ecn_mode` | 空の場合は STATE_DB に書かれない | `tunneldecaporch.cpp` L1529 |
| `ttl_mode` | 空の場合は STATE_DB に書かれない | `tunneldecaporch.cpp` L1530 |

### TUNNEL_DECAP_TERM_TABLE — フィールド省略時の挙動

| フィールド | 省略/未設定時の STATE_DB 挙動 | ソース証跡 |
|-----------|------------------------------|-----------|
| `term_type` | 常に書かれる。省略時デフォルト `P2MP` | `tunneldecaporch.cpp` L361, L1550 |
| `src_ip` | `src_ip_str.empty()` なら STATE_DB に書かれない | `tunneldecaporch.cpp` L1551-1554 |
| `subnet_type` | `subnet_type.empty()` なら STATE_DB に書かれない | `tunneldecaporch.cpp` L1555-1558 |

### VXLAN_TUNNEL_TABLE — ハードコードデフォルト

| フィールド | ハードコード値 | 説明 |
|-----------|--------------|------|
| `operstatus` | `"down"` | トンネル作成直後の初期値。ポート link-up イベントまで `down` のまま |
| `tnl_src` | `"EVPN"` | BGP EVPN 経由で作成された場合の固定ラベル |

### VXLAN_TABLE — ハードコードデフォルト

| フィールド | ハードコード値 | 説明 |
|-----------|--------------|------|
| `state` | `"ok"` | `createVxlan()` 成功時のみ書き込まれる。値は常に `"ok"` でユーザー変更不可 |

### 削除・ref count 依存の残存

- `TUNNEL_DECAP_TABLE` は `tunneldecaporch` が参照カウント (`ref_count`) を管理しており、MUX や他エンティティからの参照が残る間は `del()` されない。削除要求後も STATE_DB エントリが残存する場合がある。

### Warm Reboot 時のスキップ

- `VXLAN_TUNNEL_TABLE`: warm reboot 中 (`WarmStartState == INITIALIZED`) かつ既存エントリが STATE_DB に存在する場合、`addRemoveStateTableEntry()` は書き込みをスキップする（vxlanorch.cpp L1927-1945）。

### YANG-実装 discrepancy

- `TUNNEL_DECAP_TABLE` / `TUNNEL_DECAP_TERM_TABLE` / `VXLAN_TUNNEL_TABLE` は STATE_DB テーブルであり、`sonic-yang-models` に対応する YANG モジュールは存在しない。フィールド定義はすべてコード (`tunneldecaporch.cpp` / `vxlanorch.cpp`) から導出。
- `TUNNEL_DECAP_TERM_TABLE` の `term_type` デフォルト `P2MP` は YANG にも明示されておらず、コードの変数初期値のみが規定している。

<!-- /defaults -->

<!-- ordering -->
## 書込み順依存 (Phase B)

STATE_DB への書き込みは CONFIG_DB → APPL_DB → SAI の処理完了を受けて行われる。以下は各テーブルの書き込みが確定するために必要な前提条件と、DEL 操作の安全順序。

### TUNNEL_DECAP_TABLE / TUNNEL_DECAP_TERM_TABLE

| 順序 | 操作 | 理由 |
|------|------|------|
| 1 | `CONFIG_DB TUNNEL` SET | `tunnelmgrd` が APPL_DB `TUNNEL_DECAP_TABLE` を自動生成 |
| 2 | SAI `create_tunnel()` 成功 | `addDecapTunnel()` 完了後に `setDecapTunnelStatus()` が STATE_DB へ書き込む |
| 3 | SAI `create_tunnel_term_table_entry()` 成功 | `addDecapTunnelTermEntry()` 完了後に `setDecapTunnelTermStatus()` が STATE_DB へ書き込む |

- **TERM エントリの先行到着**: APPL_DB の TUNNEL_DECAP_TERM_TABLE がトンネル本体より先に届いた場合、orchagent は `unhandledDecapTerms` に蓄積する。STATE_DB への TERM 書き込みは必ずトンネル本体 SAI 作成の後になる[^2][^3]。
- **ref_count による DEL 抑止**: `removeDecapTunnel()` を呼んでも参照カウントが残る間は `stateTunnelDecapTable->del()` が呼ばれない。MUX_CABLE 等の参照元を先に DEL すること。

### VXLAN_TUNNEL_TABLE

- **書き込みタイミング**: `addRemoveStateTableEntry(add=true)` は `addTunnelUser()` / `createDynamicDIPTunnel()` から呼ばれる。`VXLAN_TUNNEL` エントリの SET 直後ではなく、`VXLAN_TUNNEL_MAP` / EVPN 処理が完了して SAI tunnel が作成されてから書き込まれる[^4]。
- **Warm boot スキップ**: `WarmStart::INITIALIZED` かつ既存エントリが STATE_DB に存在する場合は書き込みをスキップする（重複防止）。

### VXLAN_TABLE

- **書き込み条件**: `createVxlan()` (vxlanmgr.cpp) の Linux VXLAN netdevice 作成が成功した場合のみ `state=ok` を書き込む。失敗時は STATE_DB エントリが存在しない[^5]。

### DEL 操作の安全順序

```
# TUNNEL_DECAP_* 系
DEL APPL_DB TUNNEL_DECAP_TERM_TABLE|<name>|<dst_ip>   # term を先に DEL
DEL APPL_DB TUNNEL_DECAP_TABLE|<name>                  # ref_count=0 確認後に DEL
# STATE_DB エントリは orchagent が自動削除

# VXLAN 系
DEL CONFIG_DB VXLAN_TUNNEL_MAP|*                        # map を先に DEL
DEL CONFIG_DB VXLAN_TUNNEL|<name>                       # vxlanmgrd が STATE_DB を自動削除
```

> 詳細スキャンノート: `meta/_intermediate/cdb-flow/tunnel-state-ordering.md`

<!-- /ordering -->

<!-- cross-refs -->
## 他テーブル・Orch とのクロスリファレンス (Phase C)

STATE_DB の TUNNEL 系テーブルは他 Orch からの**直接読み取り対象ではない**。他 Orch はインメモリキャッシュを通じて参照し、STATE_DB はモニタリング向けの読み取り専用ミラーとして機能する。ただし、STATE_DB 書き込みの**契機**となるイベントは複数の Orch にまたがる。

### TUNNEL_DECAP_TABLE — 参照元 Orch

| 参照元 | 呼び出し箇所 | 参照内容 |
|-------|------------|---------|
| `MuxOrch` (muxorch.cpp:2348-2374) | `MuxCable::updateTunnelRoute()` | `getDstIpAddresses()` / `getDscpMode()` / `getQosMapId()` で MUX_TUNNEL の設定値を取得 |
| `RouteOrch` (routeorch.cpp:2714, 3222, 3245) | SubnetDecap ルート処理 | `getSubnetDecapConfig()` で decap src_ip・有効フラグを取得 |
| `VnetOrch` (vnetorch.cpp:1565, 1583) | VNET ルートフィルタ | `getSubnetDecapConfig()` で decap 有効フラグを取得 |

MuxOrch は `TunnelDecapOrch*` を直接保持しており、`TUNNEL_DECAP_TABLE` の STATE_DB エントリが存在しない（トンネル SAI 未作成）状態での `MUX_CABLE` SET は不整合を引き起こす[^6]。

### VXLAN_TUNNEL_TABLE — 書き込み契機 Orch

`VxlanTunnelOrch::addRemoveStateTableEntry()` は以下の経路から呼ばれる:

| 経路 | 書き込み種別 |
|-----|------------|
| `EvpnNvoOrch` → `addTunnelUser()` (vxlanorch.cpp:1678) | EVPN IMR/IP 経由の DIP トンネル作成 |
| `EvpnNvoOrch` → `createDynamicDIPTunnel()` (vxlanorch.cpp:1733) | 動的 DIP トンネル作成 |
| `PortsOrch::addTunnel()` 完了直後 (vxlanorch.cpp:1719-1720) | `gPortsOrch` へのトンネル登録後に STATE_DB 書き込み |
| `PortsOrch::removeTunnel()` 完了直後 (vxlanorch.cpp:1761, 1843) | `gPortsOrch` からのトンネル削除後に STATE_DB 削除 |

### VXLAN_TABLE — 独立した書き込みフロー

`VxlanMgr` (cfgmgr) が Linux VXLAN netdevice を作成した際に独立して書き込む。`VxlanTunnelOrch` や他 Orch との直接的な依存はない。

> 詳細スキャンノート: `meta/_intermediate/cdb-flow/tunnel-state-crossrefs.md`

<!-- /cross-refs -->

<!-- failure -->
## 失敗挙動マトリクス (Phase D)

`tunneldecaporch` / `VxlanTunnelOrch` / `VxlanMgr` における STATE_DB 書き込みの失敗経路を網羅する。

### TUNNEL_DECAP_TABLE — SET 失敗経路

| 失敗条件 | 検出箇所 | STATE_DB への影響 | ログ | evidence |
|---|---|---|---|---|
| `tunnel_type` が `IPINIP` 以外 | `doDecapTunnelTask()` | `valid=false` → 書き込みなし | SWSS_LOG_ERROR | `tunneldecaporch.cpp:127-131` |
| `src_ip` が無効な IP アドレス文字列 | `doDecapTunnelTask()` | `valid=false` → 書き込みなし | SWSS_LOG_ERROR | `tunneldecaporch.cpp:142-145` |
| `src_ip` を既存トンネルに変更しようとした場合 | `doDecapTunnelTask()` | エラーログのみ・既存 STATE_DB は変化なし | SWSS_LOG_ERROR | `tunneldecaporch.cpp:148-150` |
| `dscp_mode` / `ecn_mode` / `ttl_mode` が無効値 | `doDecapTunnelTask()` | `valid=false` → 書き込みなし | SWSS_LOG_ERROR | `tunneldecaporch.cpp:155-207` |
| `ecn_mode` を既存トンネルに SET（create-only SAI 属性） | `doDecapTunnelTask()` | WARN ログのみ・SAI 変更なし・STATE_DB は更新される（SAI と不一致） | SWSS_LOG_WARN | `tunneldecaporch.cpp:178-182` |
| QoS マップ (`decap_dscp_to_tc_map` 等) が未解決 | `doDecapTunnelTask()` | `task_need_retry` → m_toSync 保留・書き込みなし（後で再試行） | SWSS_LOG_NOTICE | `tunneldecaporch.cpp:218-266` |
| 不明フィールドを SET に含む | `doDecapTunnelTask()` | `valid=false` → 書き込みなし | SWSS_LOG_ERROR | `tunneldecaporch.cpp:275-279` |
| SAI `create_router_interface` 失敗 | `addDecapTunnel()` | トンネル作成中断 → STATE_DB に書かれない | SWSS_LOG_ERROR | `tunneldecaporch.cpp:754-761` |
| SAI `create_tunnel` 失敗 | `addDecapTunnel()` | トンネル作成中断 → STATE_DB に書かれない | SWSS_LOG_ERROR | `tunneldecaporch.cpp:850-857` |

### TUNNEL_DECAP_TABLE — DEL 失敗経路

| 失敗条件 | 検出箇所 | STATE_DB への影響 | ログ | evidence |
|---|---|---|---|---|
| DEL 対象トンネルが未登録 | `doDecapTunnelTask()` | エラーログのみ・STATE_DB 変化なし | SWSS_LOG_ERROR | `tunneldecaporch.cpp:325-327` |
| `tunnel_term_info` が残存している状態で DEL | `removeDecapTunnel()` | `removeDecapTunnelStatus()` 未呼び出し → STATE_DB エントリ残存 | SWSS_LOG_ERROR | `tunneldecaporch.cpp:1182-1186` |
| `ref_count > 0` の状態での DEL 要求 | `RemoveTunnelIfNotReferenced()` | `removeDecapTunnel()` スキップ → STATE_DB エントリ残存（ref_count が 0 になるまで保留） | （ログなし） | `tunneldecaporch.cpp:1569-1575` |
| SAI `remove_tunnel` 失敗 | `removeDecapTunnel()` | `removeDecapTunnelStatus()` 未呼び出し → STATE_DB エントリ残存 | SWSS_LOG_ERROR | `tunneldecaporch.cpp:1188-1196` |

### TUNNEL_DECAP_TERM_TABLE — 失敗経路

| 失敗条件 | 検出箇所 | STATE_DB への影響 | ログ | evidence |
|---|---|---|---|---|
| SAI `create_tunnel_term_table_entry` 失敗 | `addDecapTunnelTermEntry()` | `setDecapTunnelTermStatus()` 未呼び出し → STATE_DB に書かれない | SWSS_LOG_ERROR | `tunneldecaporch.cpp:980-987` |
| Subnet decap が無効 (`subnetDecapConfig.enabled=false`) の状態で MP2MP term を SET | `doDecapTunnelTermTask()` | エントリ erase・STATE_DB 書き込みなし | SWSS_LOG_ERROR | `tunneldecaporch.cpp:504-509` |
| 親トンネルが未作成の状態で term を SET | `doDecapTunnelTermTask()` | `unhandledDecapTerms` に保留・STATE_DB 書き込みなし（親トンネル作成後に `processUnhandledDecapTunnelTerms()` で自動処理） | SWSS_LOG_NOTICE | `tunneldecaporch.cpp:519-522` |

### VXLAN_TUNNEL_TABLE — 失敗経路

| 失敗条件 | 検出箇所 | STATE_DB への影響 | ログ | evidence |
|---|---|---|---|---|
| `gPortsOrch->allPortsReady()` が false（全ポート未 ready） | `TunnelDecapOrch::doTask()` | 全タスクスキップ → STATE_DB 書き込みなし（次サイクルで再試行） | （ログなし） | `tunneldecaporch.cpp:55-58` |
| SAI `create_tunnel` 失敗（vxlanorch） | `VxlanTunnel::createTunnel()` | 例外キャッチ → `addRemoveStateTableEntry()` 未呼び出し → STATE_DB 書き込みなし | SWSS_LOG_ERROR | `vxlanorch.cpp:848` |
| P2P トンネルで `dst_ip` が 0 (VTEP 用) の場合 | `VxlanTunnel` コンストラクタ | `addRemoveStateTableEntry()` 未呼び出し → `VXLAN_TUNNEL_TABLE` に書き込まれない | （ログなし） | `vxlanorch.cpp:529-532` |
| SAI `remove_tunnel` 失敗（vxlanorch） | `VxlanTunnel::deleteTunnel()` | `~VxlanTunnel()` が途中で例外キャッチ → `del()` が呼ばれずエントリ残存 | SWSS_LOG_ERROR | `vxlanorch.cpp:874` |

### VXLAN_TABLE — 失敗経路

| 失敗条件 | 検出箇所 | STATE_DB への影響 | ログ | evidence |
|---|---|---|---|---|
| `vxlanTunnelCache` にトンネル未登録 | `doVxlanCreateTask()` | m_toSync 保留・`state=ok` 書き込みなし（トンネル作成後に自動再試行） | SWSS_LOG_DEBUG | `vxlanmgr.cpp:319-325` |
| VRF が未 ready (`isVrfStateOk()` false) | `doVxlanCreateTask()` | 保留・STATE_DB 書き込みなし | SWSS_LOG_DEBUG | `vxlanmgr.cpp:328-333` |
| MAC アドレス未設定 | `doVxlanCreateTask()` | 保留・STATE_DB 書き込みなし | SWSS_LOG_DEBUG | `vxlanmgr.cpp:336-342` |
| `createVxlan()` 失敗（Linux netdevice 作成エラー） | `doVxlanCreateTask()` | `m_stateVxlanTable.set()` 未呼び出し → `state=ok` が書き込まれない | SWSS_LOG_ERROR | `vxlanmgr.cpp:366-370` |

> 詳細スキャンノート: `meta/_intermediate/cdb-flow/tunnel-state-failure.md`

<!-- /failure -->

<!-- constants -->
## ハードコード定数 (Phase E)

コードに直書きされており、`config_db.json` での変更が効かない定数。変更にはコードのリコンパイルが必要。

### schema.h テーブル名マクロ

| マクロ | 値 | 定義場所 |
|--------|----|---------|
| `STATE_TUNNEL_DECAP_TABLE_NAME` | `"TUNNEL_DECAP_TABLE"` | `sonic-swss-common/common/schema.h:488` |
| `STATE_TUNNEL_DECAP_TERM_TABLE_NAME` | `"TUNNEL_DECAP_TERM_TABLE"` | `sonic-swss-common/common/schema.h:489` |
| `STATE_VXLAN_TUNNEL_TABLE_NAME` | `"VXLAN_TUNNEL_TABLE"` | `sonic-swss-common/common/schema.h:435` |
| `STATE_VXLAN_TABLE_NAME` | `"VXLAN_TABLE"` | `sonic-swss-common/common/schema.h:434` |

### キー区切り文字

| 定数 | 値 | 定義場所 | 用途 |
|------|----|---------|------|
| `state_db_key_delimiter` | `'|'` | `orchagent/orch.h:38` | `TUNNEL_DECAP_TERM_TABLE` のキーを `<tunnel_name>\|<dst_ip>` に組み立てる |

### TUNNEL_DECAP_TABLE フィールド有効値

| フィールド | 有効値 | 備考 |
|-----------|--------|------|
| `tunnel_type` | `"IPINIP"` | 唯一の有効値。不一致は `valid=false` でエラー（`tunneldecaporch.cpp:127`） |
| `dscp_mode` | `"uniform"` / `"pipe"` | いずれか以外はエラー（`tunneldecaporch.cpp:155`） |
| `ecn_mode` | `"copy_from_outer"` / `"standard"` | いずれか以外はエラー（`tunneldecaporch.cpp:171`） |
| `encap_ecn_mode` | `"standard"` | 唯一の有効値（`tunneldecaporch.cpp:187-189`） |
| `ttl_mode` | `"uniform"` / `"pipe"` | いずれか以外はエラー（`tunneldecaporch.cpp:203`） |

### TUNNEL_DECAP_TERM_TABLE — term_type 有効値

| 値 | 内部 enum | デフォルト |
|----|-----------|-----------|
| `"P2P"` | `TUNNEL_TERM_TYPE_P2P` | — |
| `"P2MP"` | `TUNNEL_TERM_TYPE_P2MP` | ○（省略時の変数初期値、`tunneldecaporch.cpp:361`） |
| `"MP2MP"` | `TUNNEL_TERM_TYPE_MP2MP` | — |

enum 定義: `tunneldecaporch.h:15-17`

### VXLAN_TUNNEL_TABLE — フィールド値定数

| フィールド | 値 | 条件 | 定義場所 |
|-----------|-----|------|---------|
| `operstatus` | `"down"` | トンネル初回作成時（`addRemoveStateTableEntry`） | `vxlanorch.cpp:1942` |
| `operstatus` | `"up"` | ポート link-up イベント発生時（`updateDbTunnelOperStatus`） | `vxlanorch.cpp:1901` |
| `operstatus` | `"down"` | ポート link-down イベント発生時 | `vxlanorch.cpp:1905` |
| `tnl_src` | `"CLI"` | CONFIG_DB `VXLAN_TUNNEL` から手動設定されたトンネル | `vxlanorch.cpp:1935` |
| `tnl_src` | `"EVPN"` | BGP EVPN 経由で動的に作成されたトンネル | `vxlanorch.cpp:1939` |

`TNL_CREATION_SRC_CLI` / `TNL_CREATION_SRC_EVPN` enum 定義: `vxlanorch.h:53-55`

### VXLAN_TABLE — フィールド値定数

| フィールド | 値 | 条件 | 定義場所 |
|-----------|-----|------|---------|
| `state` | `"ok"` | `createVxlan()` 成功時のみ。失敗時は書き込まれない | `vxlanmgr.cpp:891` |

### EVPN トンネル名プレフィックス定数

EVPN 由来の動的トンネルは `EVPN_<vtep_ip>` 形式で VXLAN_TUNNEL_TABLE に登録される。

| マクロ | 値 | 定義場所 |
|--------|----|---------|
| `LOCAL_TUNNEL_PORT_PREFIX` | `"Port_SRC_VTEP_"` | `vxlanorch.h:41` |
| `EVPN_TUNNEL_PORT_PREFIX` | `"Port_EVPN_"` | `vxlanorch.h:42` |
| `EVPN_TUNNEL_NAME_PREFIX` | `"EVPN_"` | `vxlanorch.h:43` |

> 詳細スキャンノート: `meta/_intermediate/cdb-flow/tunnel-state-constants.md`

<!-- /constants -->

<!-- side-effects -->
## STATE_DB 書き込みの副作用 (Phase F)

STATE_DB への書き込みは単なる状態ミラーにとどまらず、以下の連鎖処理を引き起こす。

### TUNNEL_DECAP_TABLE 書き込み後の副作用

#### 保留 TERM エントリのフラッシュ

`addDecapTunnel()` が成功してトンネル本体の `setDecapTunnelStatus()` が STATE_DB に書き込まれた直後、`processUnhandledDecapTunnelTerms()` が呼ばれ、`unhandledDecapTerms` に蓄積されていた TERM エントリが一括処理される[^7]。

```
addDecapTunnel() 成功
  └─ setDecapTunnelStatus()         # STATE_DB TUNNEL_DECAP_TABLE 書き込み
  └─ processUnhandledDecapTunnelTerms(key)
       └─ addDecapTunnelTermEntry() × n
            └─ increaseTunnelRefCount()
            └─ setDecapTunnelTermStatus()   # STATE_DB TUNNEL_DECAP_TERM_TABLE 書き込み
```

#### ref_count 管理との連動

TUNNEL_DECAP_TABLE の STATE_DB 削除は `ref_count` の管理と連動している。`removeDecapTunnel()` を呼んでも `ref_count > 0` の間は STATE_DB エントリが削除されない。ref_count は TERM エントリの追加・削除によって増減するため、**TERM が存在する限りトンネル本体の STATE_DB エントリも残存する**[^8]。

### TUNNEL_DECAP_TERM_TABLE 書き込み後の副作用

#### TERM 削除時のトンネル本体 DEL 連鎖

TERM エントリを削除すると `decreaseTunnelRefCount()` が呼ばれ、`ref_count` が 0 になった場合に `RemoveTunnelIfNotReferenced()` がトンネル本体を削除し、STATE_DB の `TUNNEL_DECAP_TABLE` エントリも連鎖的に `del()` される[^9]。

```
removeDecapTunnelTermEntry()
  └─ decreaseTunnelRefCount()
  └─ RemoveTunnelIfNotReferenced()
       └─ ref_count==0 のとき: removeDecapTunnel()
                └─ removeDecapTunnelStatus()   # STATE_DB TUNNEL_DECAP_TABLE 削除
```

### VXLAN_TUNNEL_TABLE 書き込み後の副作用

#### FlexCounter 登録との非同期関係

SAI トンネル作成成功時に `addTunnelToFlexCounter()` が呼ばれ、`m_pendingAddToFlexCntr` に追加される。1 秒インターバルのタイマー (`FLEX_COUNTER_UPD_INTERVAL`) が発火すると `COUNTERS_DB COUNTERS_TUNNEL_NAME_MAP` / `COUNTERS_TUNNEL_TYPE_MAP` に書き込まれてトンネル統計収集が開始される。**STATE_DB への書き込みと FlexCounter 登録の完了順序は保証されない**[^10]。

#### PortsOrch への登録順序

`addTunnelUser()` 内では `gPortsOrch->addTunnel()` → `addBridgePort()` の後に `addRemoveStateTableEntry(add=true)` が呼ばれる。STATE_DB への書き込みは PortsOrch 登録が完了した後に確定する[^11]。

#### link ステータス変化による上書き

link-up / link-down イベントが発生すると `PortsOrch::updateDbPortOperStatus()` → `VxlanTunnelOrch::updateDbTunnelOperStatus()` の経路で `operstatus` フィールドが上書きされる。この更新はトンネル作成時の初期書き込みとは独立して発生し、タイミングは SAI 通知に依存する[^12]。

### VXLAN_TABLE 書き込み後の副作用

#### Linux netdevice 作成完了の唯一の公開シグナル

`VXLAN_TABLE|<name>` の `state=ok` は `createVxlan()` が以下 6 ステップの Linux コマンドを全て成功させた場合にのみ書かれる。外部監視ツールはこのエントリを polling して VXLAN netdevice 作成完了を検出できる。途中で失敗した場合は `state=ok` が書かれず、先行コマンドのロールバックが試みられる[^13]。

| ステップ | コマンド相当 |
|---------|------------|
| 1 | `ip link add ... type vxlan` |
| 2 | `ip link set ... up` (VXLAN) |
| 3 | VxLAN インターフェース作成 |
| 4 | `ip link set ... master` (VXLAN → IF) |
| 5 | VxLAN IF を VNET にアタッチ |
| 6 | `ip link set ... up` (VxLAN IF) |

> 詳細スキャンノート: `meta/_intermediate/cdb-flow/tunnel-state-side-effects.md`

<!-- /side-effects -->

<!-- pubsub -->
## 通信メカニズム・pub/sub (Phase G)

STATE_DB のトンネル関連テーブルへの書き込みはすべて `swsscommon::Table::set()` / `del()` による直接操作であり、`NotificationProducer` / `ConsumerStateTable` ベースのチャネル通知は使用しない。

### 書き込みメカニズム

| STATE_DB テーブル | 書き込み API | 書き込み元 |
|-----------------|-------------|----------|
| `TUNNEL_DECAP_TABLE` | `stateTunnelDecapTable->set()` / `->del()` | `setDecapTunnelStatus()` / `removeDecapTunnelStatus()` (tunneldecaporch.cpp L1531, L1536) |
| `TUNNEL_DECAP_TERM_TABLE` | `stateTunnelDecapTermTable->set()` / `->del()` | `setDecapTunnelTermStatus()` / `removeDecapTunnelTermStatus()` (tunneldecaporch.cpp L1560, L1566) |
| `VXLAN_TUNNEL_TABLE` | `m_stateVxlanTable.set()` / `.del()` | `addRemoveStateTableEntry()` (vxlanorch.cpp L1943, L1953) |
| `VXLAN_TUNNEL_TABLE` (`operstatus` のみ) | `m_stateVxlanTable.set()` | `updateDbTunnelOperStatus()` (vxlanorch.cpp L1910) |
| `VXLAN_TABLE` | `m_stateVxlanTable.set()` | `VxlanMgr::createVxlan()` (vxlanmgr.cpp L890-892) |

### 購読者 — sonic-utilities CLI

`show vxlan remotevtep` コマンド (sonic-utilities/show/vxlan.py L253-268) が STATE_DB の `VXLAN_TUNNEL_TABLE|*` を **polling** で読む唯一の CLI 購読者。keyspace 通知ではなく `SonicV2Connector.keys()` + `get_all()` を使用する[^14]。

`TUNNEL_DECAP_TABLE` / `TUNNEL_DECAP_TERM_TABLE` / `VXLAN_TABLE` に特化した show コマンドは存在しない（テスト用アサーションは除く）。

### operstatus 更新の通知フロー

`VXLAN_TUNNEL_TABLE.operstatus` は SAI の port oper-status イベントを起点に更新される[^15]:

```
SAI ポートリンク変化通知
  └─ PortsOrch::updateDbPortOperStatus()        (portsorch.cpp L3920-3924)
       └─ port.m_type == Port::TUNNEL のとき
            └─ VxlanTunnelOrch::updateDbTunnelOperStatus()   (vxlanorch.cpp L1893-1910)
                 └─ m_stateVxlanTable.set(tunnel_name, {operstatus: "up"/"down"})
```

外部監視ツールが `operstatus` 変化を検出するには STATE_DB の polling が必要。

### NotificationProducer / SubscriberStateTable 非使用の確認

- `tunneldecaporch.cpp` L39 の `SubscriberStateTable` は CONFIG_DB の `CFG_SUBNET_DECAP_TABLE_NAME` 購読専用であり、STATE_DB 書き込み通知とは無関係
- STATE_DB のいずれのトンネルテーブルも、`NotificationProducer` / `NotificationConsumer` による channel 通知パスを持たない

> 詳細スキャンノート: `meta/_intermediate/cdb-flow/tunnel-state-pubsub.md`

<!-- /pubsub -->

## 引用元

[^1]: schema.h 定数定義: <https://github.com/sonic-net/sonic-swss-common/blob/158de8d3463ff4b841653f6d57190bb142b80d9c/common/schema.h#L488-L489>

[^2]: `setDecapTunnelStatus()` 実装: <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/tunneldecaporch.cpp#L1521-L1531>

[^3]: `setDecapTunnelTermStatus()` 実装: <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/tunneldecaporch.cpp#L1539-L1560>

[^4]: `addRemoveStateTableEntry()` 実装: <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/vxlanorch.cpp#L1913-L1953>

[^5]: `createVxlan()` 実装: <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/cfgmgr/vxlanmgr.cpp#L890-L892>

[^6]: `MuxCable` コンストラクタで `TunnelDecapOrch*` を保持: <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/muxorch.cpp#L2183-L2185>

[^7]: `processUnhandledDecapTunnelTerms` 呼び出し: <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/tunneldecaporch.cpp#L300-L310>

[^8]: `RemoveTunnelIfNotReferenced` による DEL 抑止: <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/tunneldecaporch.cpp#L1569-L1575>

[^9]: `decreaseTunnelRefCount` → `RemoveTunnelIfNotReferenced` 連鎖: <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/tunneldecaporch.cpp#L1258-L1265>

[^10]: `addTunnelToFlexCounter` 実装: <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/vxlanorch.cpp#L1342-L1344>

[^11]: `addTunnelUser` → `addRemoveStateTableEntry` 順序: <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/vxlanorch.cpp#L1719-L1721>

[^12]: `updateDbTunnelOperStatus` を `PortsOrch` が呼び出す: <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/portsorch.cpp#L3916-L3923>

[^13]: `createVxlan` → `m_stateVxlanTable.set`: <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/cfgmgr/vxlanmgr.cpp#L807-L892>

[^14]: `show vxlan remotevtep` が STATE_DB `VXLAN_TUNNEL_TABLE` を polling: <https://github.com/sonic-net/sonic-utilities/blob/master/show/vxlan.py#L253-L268>

[^15]: `PortsOrch::updateDbPortOperStatus()` → `updateDbTunnelOperStatus()` 委譲: <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/portsorch.cpp#L3916-L3923>
