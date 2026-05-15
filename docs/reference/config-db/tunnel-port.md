---
title: VXLAN トンネルポート (Port::TUNNEL)
description: "VXLAN トンネルポート — orchagent が VXLAN_TUNNEL_MAP / EVPN_REMOTE_VNI 処理時に動的生成する Port::TUNNEL 型ポートオブジェクトのコード由来デフォルトと暗黙挙動を解説する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-15
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/vxlanorch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/vxlanorch.h
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/portsorch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/port.h
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
related:
  config_db:
    - VXLAN_TUNNEL
    - VXLAN_TUNNEL_MAP
    - VXLAN_EVPN_NVO
  cli:
    - config vxlan
  yang:
    - sonic-vxlan
---

# VXLAN トンネルポート (Port::TUNNEL)

!!! warning "CONFIG_DB テーブルではない"
    VXLAN トンネルポートは [CONFIG_DB](../../reference/glossary.md#term-config_db) のテーブルではなく、`orchagent` 内の `PortsOrch` が `m_portList` に保持するランタイムオブジェクト。`sonic-yang-models` に対応 [YANG](../../reference/glossary.md#term-yang) モジュールは存在しない。本ページは `PortsOrch::addTunnel()` / `addBridgePort()` のコード由来デフォルトを解説する。

## 概要

[VXLAN](../../reference/glossary.md#term-vxlan) トンネルポートは `Port::TUNNEL` 型の `Port` 構造体として `orchagent` 内部に保持される。[CONFIG_DB](../../reference/glossary.md#term-config_db) の `VXLAN_TUNNEL_MAP` または `EVPN_REMOTE_VNI_TABLE` の処理結果として動的生成されるものであり、オペレータが直接設定する対象ではない[^1]。

トンネルポートには 2 種類ある。

| 種別 | 名前形式 | 生成トリガー |
|------|---------|------------|
| Local SRC VTEP ポート | `Port_SRC_VTEP_<src_ip>` | `VXLAN_TUNNEL_MAP` 処理 (DIP トンネル非サポート時) |
| EVPN DIP トンネルポート | `Port_EVPN_<remote_vtep_ip>` | `addTunnelUser()` (EVPN リモート VTEP 学習時) |

<!-- cdb-mermaid -->
### データフロー

```mermaid
flowchart LR
  CDB[("CONFIG_DB\nVXLAN_TUNNEL\nVXLAN_TUNNEL_MAP")]
  ORCH["VxlanTunnelOrch\n(orchagent)"]
  PORTS["PortsOrch\nm_portList\n[Port::TUNNEL]"]
  SAI["SAI\nsai_bridge_api\ncreate_bridge_port()"]
  CDB --> ORCH
  ORCH --> PORTS
  PORTS --> SAI
```

<!-- /cdb-mermaid -->

## 命名規則

| プレフィックス定数 | 値 | 場所 |
|-----------------|-----|------|
| `LOCAL_TUNNEL_PORT_PREFIX` | `"Port_SRC_VTEP_"` | `vxlanorch.h:41` |
| `EVPN_TUNNEL_PORT_PREFIX` | `"Port_EVPN_"` | `vxlanorch.h:42` |

命名は `getTunnelPortName(vtep, local)` が `local=true` の場合に `LOCAL_TUNNEL_PORT_PREFIX`、`false` の場合に `EVPN_TUNNEL_PORT_PREFIX` を vtep IP に連結して生成する[^1]。

## 生成フロー

### EVPN DIP トンネルポート (DIP トンネルサポート有り)

```
addTunnelUser(remote_vtep, vni_id, ...) [vxlanorch.cpp:1674]
  → createDynamicDIPTunnel(remote_vtep) [vxlanorch.cpp:1707]
  → getTunnelPort(remote_vtep) が false の場合のみ新規生成
  → gPortsOrch->addTunnel("Port_EVPN_<vtep>", tunnel_id, hwlearning=false)
  → gPortsOrch->addBridgePort(tunnelPort)
```

### Local SRC VTEP ポート (DIP トンネル非サポート時)

```
VxlanTunnelMapOrch::addOperation [vxlanorch.cpp:2079]
  → getTunnelPort(src_vtep, local=true) が false の場合のみ新規生成
  → gPortsOrch->addTunnel("Port_SRC_VTEP_<src_ip>", tunnel_id, hwlearning=false)
  → gPortsOrch->addBridgePort(tunPort)
```

## 購読者

- `VxlanTunnelOrch::addTunnelUser()`: EVPN DIP トンネルポートを生成
- `VxlanTunnelMapOrch::addOperation()`: Local SRC VTEP ポートを生成 (DIP 非サポート時)
- `VxlanTunnelOrch::deleteTunnelPort()`: FDB カウントが 0 の場合にポートを削除
- `VxlanTunnelOrch::updateDbTunnelOperStatus()`: STATE_DB の oper status を更新

<!-- defaults -->
## コード由来の暗黙デフォルト (Phase A)

以下のデフォルト値は DB フィールドとして公開されず、`portsorch.cpp` / `vxlanorch.cpp` 内でハードコードまたは暗黙的に設定される[^1]。

| フィールド / SAI 属性 | デフォルト / 実挙動 | 分類 | 根拠 |
|----------------------|--------------------|------|------|
| `m_type` | 常に `Port::TUNNEL` ハードコード | ハードコード | `portsorch.cpp:8362` |
| `m_learn_mode` (FDB 学習) | 常に `SAI_BRIDGE_PORT_FDB_LEARNING_MODE_DISABLE` — `hwlearning=false` が固定で渡される | ハードコード | `vxlanorch.cpp:1719`, `vxlanorch.cpp:2082`, `portsorch.cpp:8370` |
| `m_oper_status` 初期値 | `SAI_PORT_OPER_STATUS_DOWN` — トンネルポート作成直後は常に DOWN | ハードコード初期値 | `portsorch.cpp:8372` |
| SAI bridge type | `SAI_BRIDGE_PORT_TYPE_TUNNEL` ハードコード | ハードコード | `portsorch.cpp:7230` |
| SAI bridge | `m_default1QBridge` (デフォルト 1Q ブリッジ固定) | ハードコード | `portsorch.cpp:7238` |
| SAI admin state | `true` (UP) — ブリッジポート作成時に常に UP | ハードコード | `portsorch.cpp:7250` |
| `m_fdb_count` 初期値 | `0` | ハードコード初期値 | `port.h:234` |
| CONFIG_DB フィールド | なし — 全属性がコード内で固定 | CONFIG_DB 非連動 | YANG 定義なし |

### 詳細: FDB 学習の無効化

`VxlanTunnelOrch::addTunnelUser()` (vxlanorch.cpp:1719) および
`VxlanTunnelMapOrch::addOperation()` (vxlanorch.cpp:2082) はどちらも
`gPortsOrch->addTunnel(name, id, false)` を呼ぶ。`hwlearning=false` により
`PortsOrch::addTunnel()` 内で `m_learn_mode = SAI_BRIDGE_PORT_FDB_LEARNING_MODE_DISABLE` が設定され、
後続の `addBridgePort()` で SAI ブリッジポートの `FDB_LEARNING_MODE` 属性として渡される。
結果として、すべての VXLAN トンネルポートで HW FDB 学習は **常に無効**。CONFIG_DB から
この挙動を変更する手段はない[^1]。

### 詳細: 削除ガード

`deleteTunnelPort()` (vxlanorch.cpp:1792) および `delTunnelUser()` は
`tunnelPort.m_fdb_count != 0` を確認し、FDB エントリが残存する間は
`removeBridgePort()` を呼ばない。削除は FDB エージング後まで遅延する。

<!-- /defaults -->

## 例外条件・特殊挙動

- **二重生成の防止**: `getTunnelPort()` が既存エントリを発見した場合 `addTunnel()` を呼ばない。ポートは 1 remote VTEP につき 1 つのみ存在する (`vxlanorch.cpp:1715`)。
- **DIP トンネル非サポート時の縮退**: `isDipTunnelsSupported()` が `false` の場合、EVPN DIP トンネルポートは生成されず、Local SRC VTEP ポート 1 つがすべてのリモート VTEP を共用する (`vxlanorch.cpp:1701-1704`)。
- **FDB カウント残留による削除ブロック**: `m_fdb_count != 0` の間はブリッジポート削除がスキップされ `SWSS_LOG_ERROR` が記録される。FDB エントリのエージングが必要 (`vxlanorch.cpp:1770-1776`)。
- **STATE_DB oper status**: `updateDbTunnelOperStatus()` (vxlanorch.cpp:1893) が `SAI_PORT_OPER_STATUS_UP` / `DOWN` を STATE_DB の `VXLAN_TUNNEL_TABLE` に書き込む。初期は `DOWN` で始まり、アンダーレイルートが確立されると `UP` に遷移。

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): [`VXLAN_TUNNEL`](vxlan-tunnel.md)、[`VXLAN_TUNNEL_MAP`](vxlan-tunnel-map.md)、[`VXLAN_EVPN_NVO`](vxlan-evpn-nvo.md)
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-vxlan` (tunnel port エントリなし)
- 関連 CLI: [`config vxlan`](../cli/config-vxlan.md)

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`VXLAN_TUNNEL`](vxlan-tunnel.md)
- CONFIG_DB: [`VXLAN_TUNNEL_MAP`](vxlan-tunnel-map.md)
- CONFIG_DB: [EVPN DIP トンネル](vxlan-evpn-tunnel.md)
- CONFIG_DB: [VxlanTunnelOrch encap 処理詳細](tunnel-encap-orch.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: VxlanTunnelOrch / PortsOrch 実装: `orchagent/vxlanorch.cpp`, `orchagent/portsorch.cpp`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/vxlanorch.cpp>

## 関連ページ

- [HLD: VXLAN / VNet 全体設計](../../overlay/vxlan-sonic.md)
- [CONFIG_DB: VXLAN_TUNNEL](vxlan-tunnel.md)
- [CONFIG_DB: VXLAN_TUNNEL_MAP](vxlan-tunnel-map.md)
- [CONFIG_DB: EVPN DIP トンネル](vxlan-evpn-tunnel.md)
- [CONFIG_DB: VxlanTunnelOrch encap 処理詳細](tunnel-encap-orch.md)

<!-- ops-hint -->
## 運用ヒント

### トンネルポートの確認

```bash
# EVPN DIP トンネルポートは STATE_DB で確認
sonic-db-cli STATE_DB keys 'VXLAN_TUNNEL_TABLE|*'

# 個別トンネルの oper status
sonic-db-cli STATE_DB hgetall 'VXLAN_TUNNEL_TABLE|EVPN_<remote_vtep_ip>'

# show コマンド
show vxlan tunnel
show vxlan remotevtep
```

### よくある問題

- **FDB 残留でトンネルポート削除されない**: `m_fdb_count != 0` の間はブリッジポートが削除されない。`show vxlan remotevtep` でリモート VTEP が消えない場合は FDB エージングを待つ。
- **DIP トンネル非サポートプラットフォーム**: `isDipTunnelsSupported() = false` の場合は Local SRC VTEP ポートが 1 つだけ生成される。`Port_EVPN_*` は存在しない。
- **トンネルポート oper DOWN 継続**: アンダーレイルートが未到達の場合は oper status が `DOWN` のまま。BGP/IGP のアンダーレイ経路を確認する。
<!-- /ops-hint -->
