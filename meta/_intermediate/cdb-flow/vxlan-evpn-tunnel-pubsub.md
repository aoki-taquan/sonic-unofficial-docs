# EVPN DIP トンネル (動的生成) — Phase G 通信メカニズムスキャンノート

対象ページ: `docs/reference/config-db/vxlan-evpn-tunnel.md`
対象フロー: BGP EVPN IMET (Type-3) ルート → fdbsyncd → APP_DB VXLAN_REMOTE_VNI_TABLE → EvpnRemoteVnip2pOrch → SAI
スキャン範囲: `sonic-swss/fdbsyncd/fdbsync.cpp`、`sonic-swss/fdbsyncd/fdbsyncd.cpp`、`sonic-swss/orchagent/vxlanorch.cpp`、`sonic-swss/orchagent/orchdaemon.cpp`

---

## 検出した通信メカニズム

### 1. fdbsyncd — Netlink (RTM_NEWNEIGH/RTM_DELNEIGH) → IMET ルート検出

`fdbsyncd/fdbsyncd.cpp:26-28` で `NetDispatcher` に `RTM_NEWNEIGH` / `RTM_DELNEIGH` / `RTM_NEWLINK` を登録。FRR bgpd が EVPN Type-3 (IMET) ルートを学習するとカーネルネイバーテーブルが更新され、libnl の RTNLGRP_NEIGH グループ購読経由でイベントが `FdbSync::onMsgNbr()` に到達する (`fdbsync.cpp:692`)。

IMET ルートの判定条件: MAC アドレスが `00:00:00:00:00:00` かつ `vtep.s_addr != 0` (`fdbsync.cpp:805-813`)。この条件を満たす RTM_NEWNEIGH イベントが `imetAddRoute()`、RTM_DELNEIGH イベントが `imetDelRoute()` を呼ぶ。

### 2. fdbsyncd → APP_DB (ProducerStateTable via RedisPipeline)

`FdbSync::m_imetTable` は `RedisPipeline` + `ProducerStateTable` として `APP_VXLAN_REMOTE_VNI_TABLE_NAME` (`"VXLAN_REMOTE_VNI_TABLE"`) を書き込む (`fdbsync.cpp:26`)。

```
imetAddRoute(): m_imetTable.set("<Vlan{id}>:<vtep_ip>", [("vni", "<vni>")])
imetDelRoute(): m_imetTable.del("<Vlan{id}>:<vtep_ip>")
```

キー形式: `Vlan<id>:<vtep_ip>` (例: `Vlan100:192.0.2.1`)。フィールドは `vni` のみ (`fdbsync.cpp:578-586`)。

WarmStart 中は `AppRestartAssist::insertToMap()` にキャッシュし、reconciliation 完了後に一括適用する。

### 3. fdbsyncd 主ループ — blocking select、タイムアウトなし

`fdbsyncd.cpp:91` で `s.select(&temps)` をタイムアウトなし (UINT_MAX) で呼ぶ永続ブロックループ。イベントは netlink または STATE_DB/CONFIG_DB の `SubscriberStateTable` から到達する:

| selectable | 購読先 | 処理関数 |
|-----------|--------|---------|
| `netlink` (RTNLGRP_NEIGH/RTNLGRP_LINK) | カーネル netlink | `onMsgNbr()` / `onMsgLink()` |
| `sync.getFdbStateTable()` | STATE_DB `FDB_TABLE` | `processStateFdb()` |
| `sync.getMclagRemoteFdbStateTable()` | STATE_DB `MCLAG_REMOTE_FDB_TABLE` | `processStateMclagRemoteFdb()` |
| `sync.getCfgEvpnNvoTable()` | CONFIG_DB `EVPN_NVO_TABLE` | `processEvpnNvo()` |

明示的な retry interval / sleep は存在しない。netlink イベント駆動。

### 4. orchagent — ConsumerStateTable + select ループ (SELECT_TIMEOUT = 1000 ms)

`orchdaemon.cpp:579-586` で `isDipTunnelsSupported()` が true の場合は `EvpnRemoteVnip2pOrch`、false の場合は `EvpnRemoteVnip2mpOrch` を APP_DB `VXLAN_REMOTE_VNI_TABLE_NAME` に対して生成し `m_orchList` に追加する。

orchagent 共通の `Select::select()` ループ (SELECT_TIMEOUT = 1000 ms、`orchdaemon.cpp:23,959`) が APP_DB への書き込みを検知し、`EvpnRemoteVnip2pOrch::addOperation()` / `delOperation()` を呼び出す。

`EvpnRemoteVnip2pOrch` は `Orch2` を基底クラスとして持ち、`ConsumerStateTable` 経由で APP_DB を購読する (`vxlanorch.h:499-502`)。

### 5. orchagent → SAI — 同期 API 呼び出し (bulk なし)

`addOperation()` が前提条件 (EVPN VTEP / VLAN / VNI-VLAN マップ) を確認後、`addTunnelUser()` → `createDynamicDIPTunnel()` → `sai_tunnel_api->create_tunnel()` を直接呼ぶ。SAI 呼び出しは同期で、bulk API は使用しない。前提条件が未満足の場合は `return false` でタスクキューに残留し、orchagent の次のイベントループで自動再処理される。

### 6. STATE_DB への書き戻し — orchagent が直接書き込み

DIP トンネル生成・oper status 変化・削除に連動して orchagent が `m_stateVxlanTable` (`SubscriberStateTable`/`Table`) に書き込む。STATE_DB の変化を読む外部 consumer は show コマンド (`show vxlan tunnel` など) であり、イベント駆動ではなくポーリングまたはコマンド実行時の snapshot 読み取り。

---

## 通信メカニズム サマリ

| 区間 | 方式 | チャンネル / テーブル |
|------|------|---------------------|
| カーネル netlink (EVPN IMET ルート) → `FdbSync` | `libnl` RTNLGRP_NEIGH | RTM_NEWNEIGH / RTM_DELNEIGH |
| `FdbSync` → APP_DB `VXLAN_REMOTE_VNI_TABLE` | `ProducerStateTable` (RedisPipeline) | `VXLAN_REMOTE_VNI_TABLE_CHANNEL@0` |
| APP_DB `VXLAN_REMOTE_VNI_TABLE` → `EvpnRemoteVnip2pOrch` | `ConsumerStateTable` (Orch2 基底) | keyspace notification |
| `EvpnRemoteVnip2pOrch` → SAI | 直接 API 呼び出し (同期) | `sai_tunnel_api`, `sai_vlan_api` |
| `orchagent` → STATE_DB `VXLAN_TUNNEL_TABLE` | `Table::set/del` | 直接書き込み |

---

## ページ反映方針

`<!-- /side-effects -->` の直後に `<!-- pubsub -->` ブロックを追加する。
