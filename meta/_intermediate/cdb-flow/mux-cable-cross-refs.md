# MUX_CABLE テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/mux-cable.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-swss/orchagent/muxorch.cpp`。`MUX_CABLE` エントリ処理時に `MuxOrch` が直接購読せずに間接参照する CONFIG_DB / APPL_DB テーブルを列挙する。

## スキャン手順

```bash
grep -n "NEIGHBOR_TABLE\|PORT_TABLE\|VLAN\|TUNNEL_TABLE\|gPortsOrch\|gNeighOrch\|decap_orch_\|getAllPorts\|getAllVlans\|getPort\|getNeighborEntry\|getMuxNeighbors" \
    .cache/sonic-sources/sonic-swss/orchagent/muxorch.cpp
```

`MuxOrch::addOperation()` (L2260-L2310) および `MuxCable::stateActive()` / `MuxCable::stateStandby()` (L467-L500) 等で `gPortsOrch->getPort()` / `gNeighOrch->getNeighborEntry()` / `decap_orch_->getDstIpAddresses()` の呼び出しを抽出。

## 検出された暗黙参照テーブル

### PORT テーブル (PortsOrch 経由)

`MuxOrch` は `MUX_CABLE` キーを受け取ると、まず `gPortsOrch->getPort(mux_name_, port)` でポートオブジェクトを取得する。ポートが未登録であればスキップ。`MuxAclHandler::bindAllPorts()` (L1490) では `gPortsOrch->getAllPorts()` で全物理ポート・LAG を走査して ACL テーブルをバインドする。

| 参照方法 | 参照箇所 | 用途 |
|---|---|---|
| `gPortsOrch->getPort(mux_name_, port)` | muxorch.cpp:468, 493 | MUX ポートの SAI oid / m_port_id 取得。欠落時は即リターン |
| `gPortsOrch->getAllPorts()` | muxorch.cpp:1490 | ACL テーブルバインド時に全 PHY/LAG を列挙 |
| `gPortsOrch->getAllVlans()` | muxorch.cpp:1861 | FDB 学習後に VLAN neighbor を MUX neighbor へ変換する際 VLAN 一覧を取得 |

> **PORT テーブルは leafref 先でもある**。`MUX_CABLE|<ifname>` の `<ifname>` は `PORT.name` への leafref (YANG: sonic-mux-cable.yang)。MuxOrch は PORT が確定していない状態では処理を保留する。

### NEIGHBOR_TABLE (NeighOrch 経由)

`gNeighOrch` を通じて以下のネイバー情報を参照する。いずれも APPL_DB または NeighOrch キャッシュ (NEIGHBOR_TABLE) 経由。

| 参照方法 | 参照箇所 | 用途 |
|---|---|---|
| `gNeighOrch->getMuxNeighborsForPort(port_name, m_neighbors)` | muxorch.cpp:2290 | MUX ポート設定前に学習済みネイバーを一括取得し MUX ネイバーに変換 |
| `gNeighOrch->getNeighborEntry(nexthop, neighbor, mac)` | muxorch.cpp:1619, 2462 | ネクストホップ更新時・ルート設定時にネイバーの MAC / alias を照合 |
| `gNeighOrch->getLocalNextHopId(nh)` | muxorch.cpp:765, 823, 1179, 1256, 1279 | active 状態でローカル NH id を取得して SAI ルートに設定 |
| `gNeighOrch->enableNeighbor()` / `disableNeighbor()` | muxorch.cpp:766, 774 | active/standby 切替時にネイバーを有効化・無効化 |

> MuxOrch は NEIGHBOR_TABLE を直接 subscribe しない。NeighOrch が APPL_DB の `NEIGH_TABLE` を購読し、`MuxOrch::updateNeighbor()` / `MuxOrch::updateRoute()` へコールバックする構造。

### TUNNEL テーブル (TunnelDecapOrch 経由)

`MuxOrch::handlePeerSwitch()` (L2340-) が `PEER_SWITCH` エントリを受け取ると、`decap_orch_->getDstIpAddresses(MUX_TUNNEL)` を呼んで `TUNNEL` テーブルの `MuxTunnel0` エントリから宛先 IP を取得する。TUNNEL エントリが未作成であれば処理を延期する。

| 参照方法 | 参照箇所 | 用途 |
|---|---|---|
| `decap_orch_->getDstIpAddresses("MuxTunnel0")` | muxorch.cpp:2348 | PEER_SWITCH 処理時に TUNNEL.MuxTunnel0 の dst_ip を取得してP2P tunnel を生成 |
| `decap_orch_->getDscpMode("MuxTunnel0")` | muxorch.cpp:2359 | MuxTunnel0 の dscp_mode を TUNNEL テーブルから読み取り SAI encap 属性に反映 |
| `decap_orch_->getQosMapId("MuxTunnel0", ...)` | muxorch.cpp:2367, 2374 | TC→DSCP / TC→Queue QoS マップ OID を TUNNEL テーブルから取得 |

> `MuxTunnel0` は `TUNNEL` CONFIG_DB テーブルに定義される。MuxOrch は TUNNEL を直接 subscribe しないが、TunnelDecapOrch のキャッシュを介して参照する。TUNNEL エントリが存在しない場合、PEER_SWITCH 処理は `return false` でリトライされる。

### VLAN テーブル (PortsOrch 経由)

FDB 学習後に VLAN interface 上のネイバーを MUX ネイバーへ変換する処理で参照。

| 参照方法 | 参照箇所 | 用途 |
|---|---|---|
| `gPortsOrch->getAllVlans()` | muxorch.cpp:1861 | MUX ポート上で FDB 更新が発生した際、VLAN 上の既存ネイバーを探索して MUX ネイバーに変換 |

> VLAN テーブルは直接購読されない。PortsOrch が `VLAN_TABLE` (APPL_DB) を管理し、MuxOrch は PortsOrch キャッシュ経由で VLAN 情報にアクセスする。

## 依存関係サマリ

```
MUX_CABLE (CONFIG_DB)
  └── MuxOrch::addOperation()
        ├── gPortsOrch->getPort()         ← PORT テーブル (隣接チェック)
        ├── gNeighOrch->getMuxNeighbors() ← NEIGHBOR_TABLE (既存ネイバー取得)
        └── decap_orch_->getDstIpAddresses() ← TUNNEL テーブル (MuxTunnel0)

PEER_SWITCH (CONFIG_DB)
  └── MuxOrch::handlePeerSwitch()
        └── decap_orch_->getDstIpAddresses/getDscpMode/getQosMapId ← TUNNEL テーブル

FDB 更新 (NeighOrch コールバック)
  └── gPortsOrch->getAllVlans()           ← VLAN テーブル
```

## まとめ — `mux-cable.md` Phase C 記載対象

| カテゴリ | テーブル | 参照方法 |
|---|---|---|
| ポート存在確認 (処理前提) | `PORT` | `gPortsOrch->getPort()` — 欠落時は処理スキップ |
| ネイバー状態参照 (NeighOrch キャッシュ) | `NEIGHBOR_TABLE` (APPL_DB) | `getMuxNeighborsForPort()` / `getNeighborEntry()` |
| トンネル設定参照 (TunnelDecapOrch キャッシュ) | `TUNNEL` (CONFIG_DB) | `getDstIpAddresses("MuxTunnel0")` / `getDscpMode()` |
| VLAN ネイバー変換 | `VLAN` | `gPortsOrch->getAllVlans()` — FDB 更新時 |

## 検証コマンド

```bash
grep -n "gPortsOrch\|gNeighOrch\|decap_orch_" \
    .cache/sonic-sources/sonic-swss/orchagent/muxorch.cpp | grep -v "SWSS_LOG"

grep -n "getAllPorts\|getAllVlans\|getPort\|getNeighborEntry\|getMuxNeighbors\|getDstIpAddresses\|getDscpMode\|getQosMapId" \
    .cache/sonic-sources/sonic-swss/orchagent/muxorch.cpp
```

このスキャン結果から派生して `docs/reference/config-db/mux-cable.md` の `<!-- cross-refs -->` ブロックを生成する。
