# VNET_ROUTE / VNET_ROUTE_TUNNEL — Phase F 副次 DB 書込 中間ファイル

生成日: 2026-05-19
ソース: `sonic-swss/orchagent/vnetorch.cpp` (`VNetRouteOrch::handleRoutes`, `VNetRouteOrch::handleTunnel`, `VNetRouteOrch::updateVnetRouteEntry`, `VNetRouteOrch::deleteTunnelRoute`)

---

## 概要

`VNET_ROUTE` / `VNET_ROUTE_TUNNEL` の CONFIG_DB 書込は `VNetCfgRouteOrch` が即座に APPL_DB へ passthrough する。副次 DB 書込は APPL_DB 消費側の `VNetRouteOrch` が SAI 反映後に行う。

| DB | テーブル / キー | トリガ | 方向 |
|----|----------------|--------|------|
| APPL_DB | `VNET_ROUTE_TABLE:<vnet>:<prefix>` | CONFIG_DB SET → passthrough | 書込（VNetCfgRouteOrch） |
| APPL_DB | `VNET_ROUTE_TUNNEL_TABLE:<vnet>:<prefix>` | CONFIG_DB SET → passthrough | 書込（VNetCfgRouteOrch） |
| APPL_DB | `BFD_SESSION_TABLE:<type>:<vrf>:<interface>:<peer>` | `endpoint_monitor` 指定時 | 書込（createBfdSession） |
| STATE_DB | `VNET_ROUTE_TUNNEL_TABLE:<vnet>:<prefix>` | tunnel 経路の SAI 反映後 | 書込（updateVnetRouteEntry） |
| STATE_DB | `ADVERTISE_NETWORK_TABLE:<vnet>:<prefix>` | `VNET.advertise_prefix=true` のとき | 書込（setBgpNetwork） |

---

## 1. APPL_DB / `VNET_ROUTE_TABLE` および `VNET_ROUTE_TUNNEL_TABLE`

`VNetCfgRouteOrch::doVnetRouteTask()` / `doVnetTunnelRouteTask()` が即時に書き込む。

```cpp
// vnetorch.cpp:3638–3661 (doVnetRouteTask / doVnetTunnelRouteTask)
app_route_table_.set(key, fvVector);   // VNET_ROUTE_TABLE
app_tunnel_table_.set(key, fvVector);  // VNET_ROUTE_TUNNEL_TABLE
```

- **SET**: CONFIG_DB のフィールドをそのまま fvVector に詰め、APPL_DB に set する。KEY 区切り文字のみ `|` → `:` 変換。
- **DEL**: `app_route_table_.del(key)` / `app_tunnel_table_.del(key)` で APPL_DB エントリを削除。
- **タイミング**: CONFIG_DB 書込と同一 orchagent イテレーション内で即座に発生する。

---

## 2. APPL_DB / `BFD_SESSION_TABLE`

`VNetRouteOrch::createBfdSession()` が `endpoint_monitor` フィールドに IP が設定されているとき、
APPL_DB の `BFD_SESSION_TABLE` に BFD セッションエントリを書き込む（vnetorch.cpp:2046, 2078-2086）。

```cpp
// vnetorch.cpp:2078-2086
BfdUpdate update;
update.peer = monitor;
update.state = SAI_BFD_SESSION_STATE_DOWN;
gBfdOrch->createBfdSession(...);
// → app_bfd_table_.set("default:default:" + monitor, fvs);
```

- **キー形式**: `<type>:<vrf>:<interface>:<peer>` 例: `default:default:default:10.0.0.1`
- **フィールド**: `local_addr`, `multihop`, `type`, （rx/tx_interval は -1 のとき付加なし）
- **DEL**: `deleteBfdSession()` で `app_bfd_table_.del(key)` を発行。`VNET_ROUTE_TUNNEL` 削除またはモニタリング無効時にセッションが解放される。
- **条件**: `endpoint_monitor` フィールドが設定されている VNET_ROUTE_TUNNEL エントリのみ発生。

---

## 3. STATE_DB / `VNET_ROUTE_TUNNEL_TABLE`

`VNetRouteOrch::updateVnetRouteEntry()` が tunnel 経路の active/inactive 状態を書き込む（vnetorch.cpp:745, 2572, 2614）。

```cpp
// vnetorch.cpp:2572-2578
state_db_route_table_.hset(key, "active_endpoints", ep_str);
state_db_route_table_.hset(key, "state", "active");

// vnetorch.cpp:2610-2616
state_db_route_table_.hset(key, "active_endpoints", "");
state_db_route_table_.hset(key, "state", "inactive");
```

- **キー**: `VNET_ROUTE_TUNNEL_TABLE|<vnet>|<prefix>`
- **フィールド**:
  - `state`: `"active"` / `"inactive"`
  - `active_endpoints`: 現在 active な endpoint の IP をカンマ区切りで列挙（inactive 時は空文字列）
- **タイミング**: BFD セッション状態変化コールバック（`gBfdOrch->attach(this)`）から呼ばれる。CONFIG_DB 書込直後ではなく BFD セッションが UP/DOWN になるタイミングで発生する。
- **条件**: `endpoint_monitor` が設定されている VNET_ROUTE_TUNNEL エントリのみ。

定数: `STATE_VNET_RT_TUNNEL_TABLE_NAME = "VNET_ROUTE_TUNNEL_TABLE"` (`schema.h:495`)

---

## 4. STATE_DB / `ADVERTISE_NETWORK_TABLE`

`VNetRouteOrch::setBgpNetwork()` が `VNET.advertise_prefix=true` のとき prefix 広告を BGP プロセスへ通知するために書き込む（vnetorch.cpp:746, 2645, 2651）。

```cpp
// vnetorch.cpp:2645-2651
if (advertise) {
    state_db_advertise_table_.set(key, fvs);   // "state" = "active"
} else {
    state_db_advertise_table_.del(key);
}
```

- **キー**: `ADVERTISE_NETWORK_TABLE|<prefix>`
- **フィールド**: `state=active`（advertise=true のとき）/ エントリ削除（advertise=false のとき）
- **読み手**: `fpmsyncd` / `bgpcfgd` が STATE_DB を購読して BGP へ経路広告を通知する。
- **条件**: 親 `VNET` エントリに `advertise_prefix=true` が設定されている場合のみ発生する。

定数: `STATE_ADVERTISE_NETWORK_TABLE_NAME = "ADVERTISE_NETWORK_TABLE"` (`schema.h:496`)

---

## 副次書込なし（スコープ外）

- **COUNTERS_DB / FLEX_COUNTER_DB**: VNET_ROUTE 処理では flex counter 登録を行わない。
- **ASIC_DB**: SAI 経由で syncd が書き込む（orchagent の直接書込なし）。

---

## 書込フロー図

```
VNET_ROUTE SET (CONFIG_DB)
  └─ VNetCfgRouteOrch::doVnetRouteTask()
       └─ app_route_table_.set()                          → APPL_DB/VNET_ROUTE_TABLE (即時)

VNET_ROUTE_TUNNEL SET (CONFIG_DB)
  └─ VNetCfgRouteOrch::doVnetTunnelRouteTask()
       └─ app_tunnel_table_.set()                         → APPL_DB/VNET_ROUTE_TUNNEL_TABLE (即時)

APPL_DB/VNET_ROUTE_TUNNEL_TABLE (消費)
  └─ VNetRouteOrch::handleTunnel()
       ├─ SAI: sai_route_api->create_route_entry()        → ASIC_DB (syncd 経由)
       ├─ SAI: sai_next_hop_group_api->create_...()       → ASIC_DB (syncd 経由)
       ├─ createBfdSession() [endpoint_monitor あり]      → APPL_DB/BFD_SESSION_TABLE
       └─ BFD 状態変化コールバック後:
            ├─ updateVnetRouteEntry() active              → STATE_DB/VNET_ROUTE_TUNNEL_TABLE
            └─ setBgpNetwork() [advertise_prefix あり]    → STATE_DB/ADVERTISE_NETWORK_TABLE

VNET_ROUTE_TUNNEL DEL (CONFIG_DB)
  └─ VNetCfgRouteOrch::doVnetTunnelRouteTask()
       └─ app_tunnel_table_.del()                         → APPL_DB/VNET_ROUTE_TUNNEL_TABLE (即時)

APPL_DB/VNET_ROUTE_TUNNEL_TABLE DEL (消費)
  └─ VNetRouteOrch::handleTunnel() DEL
       ├─ SAI: sai_route_api->remove_route_entry()        → ASIC_DB (syncd 経由)
       ├─ deleteBfdSession() [endpoint_monitor あり]      → APPL_DB/BFD_SESSION_TABLE (del)
       ├─ updateVnetRouteEntry() inactive                 → STATE_DB/VNET_ROUTE_TUNNEL_TABLE
       └─ setBgpNetwork(false) [advertise_prefix あり]    → STATE_DB/ADVERTISE_NETWORK_TABLE (del)
```
