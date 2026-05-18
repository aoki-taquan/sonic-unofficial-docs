# VNET / VNET_ROUTE — 副次 DB 書込 (Phase F) 調査メモ

調査対象: `sonic-swss/orchagent/vnetorch.cpp`
調査日: 2026-05-18

## スキャン手順

対象ファイルをGrep対象として以下を検索:
- `state_db_` `.set(` `.del(` `->set(` `->del(`
- `APP_VNET_MONITOR` `bfd_session_producer_` `monitor_session_producer_`
- `STATE_VNET_RT_TUNNEL` `STATE_ADVERTISE_NETWORK`

## 発見された副次 DB 書込

### 1. STATE_DB — `VNET_ROUTE_TUNNEL_TABLE`

`VNetRouteOrch` がトンネルルートの状態を `state_vnet_rt_tunnel_table_` (= `STATE_VNET_RT_TUNNEL_TABLE`) に書き込む。

```
state_vnet_rt_tunnel_table_->set(state_db_key, fvVector);   // vnetorch.cpp:2572
state_vnet_rt_tunnel_table_->del(state_db_key);             // vnetorch.cpp:2614
```

フィールド: `active_endpoints` (アクティブ VTEP アドレス), `state` ("active"/"inactive")

### 2. STATE_DB — `ADVERTISE_NETWORK_TABLE`

`advertise_prefix: true` を設定した VNET の tunnel ルートが active 化した時点で `state_vnet_rt_adv_table_` に書き込まれ、BGP コンテナ (fpmsyncd/sonic-bgpcfgd) が広告経路として参照する。

```
state_vnet_rt_adv_table_->set(key, fvs);   // vnetorch.cpp:2645  addRouteAdvertisement()
state_vnet_rt_adv_table_->del(key);         // vnetorch.cpp:2651  removeRouteAdvertisement()
```

### 3. APP_DB — `VNET_MONITOR_TABLE`

monitoring フィールド付き VNET_ROUTE_TUNNEL のエントリ追加時に、`monitor_session_producer_` (= `APP_VNET_MONITOR_TABLE`) にモニタリングセッションを書き込む。

```
monitor_session_producer_->del(key);  // vnetorch.cpp:2247
setEndpointMonitor() → monitor_session_producer_ 書込  // vnetorch.cpp:2258ff
```

### 4. APP_DB — `BFD_SESSION_TABLE`

monitoring フィールドに `ping` / `bfd` が指定された VNET_ROUTE_TUNNEL 追加時、`createBfdSession()` が `bfd_session_producer_` (= `BFD_SESSION_TABLE`) に書き込み BfdOrch に BFD セッションを生成させる。

```
createBfdSession() → bfd_session_producer_ .set()  // vnetorch.cpp:2046-2115
removeBfdSession() → bfd_session_producer_.del()   // vnetorch.cpp:2117
```

### 5. SAI — VRF / VxLAN Tunnel Map (ASIC_DB 経由)

`VNetVrfObject::createObj()` で `sai_virtual_router_api->create_virtual_router()` を呼ぶため、ASIC_DB への SAI エントリが副次的に生成される。VNET 削除時のデストラクタでは `remove_virtual_router()` + `gFlowCounterRouteOrch->onRemoveVR()` が呼ばれる (vnetorch.cpp:345-362)。

### 6. COUNTERS_DB — 書込なし

`vnetorch.cpp` 内に COUNTERS_DB への書込コードなし。フロー統計は `gFlowCounterRouteOrch` 経由で orchagent が管理するが、VNetOrch 自体はカウンタを書かない。

## 結論

| 副次 DB | 書込有無 | 対象テーブル / 根拠 |
|---|---|---|
| STATE_DB | **あり** | `VNET_ROUTE_TUNNEL_TABLE` (active_endpoints/state), `ADVERTISE_NETWORK_TABLE` (prefix広告) |
| APP_DB (MONITOR) | **あり** | `VNET_MONITOR_TABLE` (monitoring セッション) |
| APP_DB (BFD) | **あり** | `BFD_SESSION_TABLE` (monitoring=bfd/ping 時) |
| ASIC_DB (SAI経由) | **あり** | VRF オブジェクト / VxLAN Tunnel Map (間接) |
| COUNTERS_DB | なし | `vnetorch.cpp` 全体で書込 0 件 |
| FLEX_COUNTER_DB / LOGLEVEL_DB | なし | 参照 0 件 |
