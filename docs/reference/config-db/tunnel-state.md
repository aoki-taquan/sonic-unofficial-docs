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

## 引用元

[^1]: schema.h 定数定義: <https://github.com/sonic-net/sonic-swss-common/blob/158de8d3463ff4b841653f6d57190bb142b80d9c/common/schema.h#L488-L489>

[^2]: `setDecapTunnelStatus()` 実装: <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/tunneldecaporch.cpp#L1521-L1531>

[^3]: `setDecapTunnelTermStatus()` 実装: <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/tunneldecaporch.cpp#L1539-L1560>

[^4]: `addRemoveStateTableEntry()` 実装: <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/vxlanorch.cpp#L1913-L1953>

[^5]: `createVxlan()` 実装: <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/cfgmgr/vxlanmgr.cpp#L890-L892>
