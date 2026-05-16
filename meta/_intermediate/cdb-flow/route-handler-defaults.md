# ROUTE_TABLE (APPL_DB) / fpmsyncd RouteSync handler — Phase A: コード由来の暗黙デフォルト詳細トレース

生成日: 2026-05-14  
対象ページ: `docs/reference/config-db/route-handler.md`

## 訪問ファイル・関数一覧

| ファイル | 関数/セクション | 目的 |
|---------|---------------|------|
| `sonic-swss/fpmsyncd/routesync.h` | `RouteTableFieldValueTupleWrapper` 宣言 L101-127 | field 宣言デフォルト値 |
| `sonic-swss/fpmsyncd/routesync.h` | `LabelRouteTableFieldValueTupleWrapper` 宣言 L129-150 | MPLS label route field デフォルト |
| `sonic-swss/fpmsyncd/routesync.cpp` | `getProtocolString()` L124-135 | proto 番号 → 文字列変換、失敗時数値文字列 |
| `sonic-swss/fpmsyncd/routesync.cpp` | `RouteTableFieldValueTupleWrapper::fieldValueTupleVector()` L1001-1055 | ZMQ/non-ZMQ 分岐・条件付き emit |
| `sonic-swss/fpmsyncd/routesync.cpp` | `RouteSync::onMsg()` L2053-2103 | メッセージ kind 分岐 (AF_MPLS/VNET/VRF/default) |
| `sonic-swss/fpmsyncd/routesync.cpp` | `RouteSync::onMsgRaw()` L1960-2051 | raw FPM メッセージ分岐 (NHG/SRv6/EVPN/SteerRoute) |
| `sonic-swss/fpmsyncd/routesync.cpp` | `RouteSync::onRouteMsg()` L2111-2303 | 通常経路 handler (RTN_BLACKHOLE/RTN_UNICAST 分岐) |
| `sonic-swss/fpmsyncd/routesync.cpp` | `RouteSync::getNextHopWt()` L3075-3098 | weight=0 → 1 フォールバック |
| `sonic-swss/orchagent/routeorch.cpp` | `RouteOrch::doRouteTask()` L725-815 | フィールド消費・nexthop_group+ips排他チェック |
| `sonic-swss/orchagent/routeorch.cpp` | `RouteOrch::addRoute()` L1994-2103 | blackhole判定・NHG分岐 |

## handler 分岐ツリー

```
RouteSync::onMsg() [AF 判定]
├── AF_MPLS → onLabelRouteMsg()  [LABEL_ROUTE_TABLE]
├── (AF_INET/AF_INET6) + master=VNET → onVnetRouteMsg()  [VNET_ROUTE_TABLE]
└── (AF_INET/AF_INET6) + master=VRF or NULL → onRouteMsg()  [ROUTE_TABLE]

RouteSync::onMsgRaw() [nlmsg_type 判定]
├── RTM_NEWNEXTHOP/RTM_DELNEXTHOP → onNextHopMsg()
├── RTM_NEWPICCONTEXT/RTM_DELPICCONTEXT → onPicContextMsg()
├── RTM_NEWSRV6VPNROUTE/RTM_DELSRV6VPNROUTE → onSrv6VpnRouteMsg()
├── RTM_NEWSRV6LOCALSID/RTM_DELSRV6LOCALSID → onSrv6MySidMsg()
└── getEncapType() switch
    ├── NH_ENCAP_SRV6_ROUTE → onSrv6SteerRouteMsg()
    └── default → onEvpnRouteMsg()

onRouteMsg() [rtnl_route_get_type() 判定]
├── RTN_BLACKHOLE → blackhole="true", 即 set
├── RTN_UNICAST → nexthop/ifname/weight 解決
├── RTN_MULTICAST/RTN_BROADCAST/RTN_LOCAL → スキップ (BUM未対応)
└── default → スキップ
```

## field 別 fallback 詳細

### `blackhole`

**宣言デフォルト**: `string blackhole = string("false");` (routesync.h L117)

**non-ZMQ emit 条件** (routesync.cpp L1022-1023):
```cpp
if (blackhole != string("false")) {
    fvVector.push_back(FieldValueTuple("blackhole", blackhole.c_str()));
}
```
→ 通常経路 (RTN_UNICAST) ではフィールド自体が APPL_DB に存在しない。

**orchagent 消費** (routeorch.cpp L765-766):
```cpp
if (fvField(i) == "blackhole")
    blackhole = fvValue(i) == "true";
```
→ フィールド不在 → `blackhole = false` として処理。`getSize()==0` の NextHopGroupKey 生成時に `blackhole=true` ルートとして SAI へ渡される (L2063-2067)。

### `protocol`

**non-ZMQ emit 条件** (routesync.cpp L1019-1021):
```cpp
if (protocol != string()) {
    fvVector.push_back(FieldValueTuple("protocol", protocol.c_str()));
}
```
→ getProtocolString() 失敗時はプロトコル番号の文字列 (例: `"186"`) が入る。空文字列になる経路はない。

**getProtocolString()** (routesync.cpp L124-135):
```cpp
if (!rtnl_route_proto2str(proto, buffer, sizeof(buffer)))
    return std::to_string(proto);
return buffer;
```
libnl の `rtnl_route_proto2str()` が失敗した場合（未知プロトコル番号）は数値文字列を返す。

**orchagent 消費** (routeorch.cpp L785-788):
```cpp
if (fvField(i) == "protocol" && fvValue(i) != "")
    ctx.protocol = fvValue(i);
```
→ フィールド不在または空文字列時は `ctx.protocol` が初期値 `""` のまま。

### `weight`

**宣言デフォルト**: `string weight = string();` (routesync.h L123) → 空文字列

**getNextHopWt() フォールバック** (routesync.cpp L3083-3088):
```cpp
uint8_t weight = rtnl_route_nh_get_weight(nexthop);
if (weight == 0)
{
    SWSS_LOG_INFO("Using default weight of 1 for nexthop");
    weight = 1; // default weight is 1
}
```
→ kernel は weight を 0-base で格納するため、weight=0 は実質 weight=1 を意味する (iproute2 v5.19.0 参照)。fpmsyncd が +1 して書き込む。

**non-ZMQ emit 条件** (routesync.cpp L1037-1039):
```cpp
if (weight != string()) {
    fvVector.push_back(FieldValueTuple("weight", weight.c_str()));
}
```
→ weight が空文字列の場合は emit しない（単一 nexthop で weight=0 の場合は "1" になる）。

**kernel nexthop group (NHG) path のフォールバック** (routesync.cpp L2361, L2523-2524):
```cpp
group[i] = std::make_pair(nha_grp[i].id, nha_grp[i].weight + 1);
// ...
weight_list += to_string(nha_grp[i].weight + 1);
```
→ NHG path でも同様に kernel weight に +1 して格納。

### `nexthop` / `ifname`

**宣言デフォルト**: `string nexthop = string();` / `string ifname = string();` (routesync.h L119-120) → 空文字列

**RTN_UNICAST + NHG path (group.size()==0)** (routesync.cpp L2214):
```cpp
string nexthops = nhg.nexthop.empty() ? (rtnl_route_get_family(route_obj) == AF_INET ? "0.0.0.0" : "::") : nhg.nexthop;
```
→ nexthop が空の場合: IPv4 は `"0.0.0.0"`、IPv6 は `"::"` を設定 (interface route のデフォルト)。

**orchagent 消費** (routeorch.cpp L748-752):
```cpp
if (fvField(i) == "nexthop" && fvValue(i) != "")
    ips = fvValue(i);
if (fvField(i) == "ifname" && fvValue(i) != "")
    aliases = fvValue(i);
```
→ フィールド不在または空文字列は `ips=""` / `aliases=""` のまま。

### `nexthop_group`

**宣言デフォルト**: `string nexthop_group = string();` (routesync.h L121) → 空文字列

**排他チェック** (routeorch.cpp L810-814):
```cpp
if (!nhg_index.empty() && (!ips.empty() || !aliases.empty()))
{
    SWSS_LOG_ERROR("Route %s has both nexthop_group and ips/aliases", key.c_str());
    it = consumer.m_toSync.erase(it);
    continue;
}
```
→ `nexthop_group` と `nexthop`/`ifname` が両方存在すると経路を棄却。

### `mpls_nh`

**宣言デフォルト**: `string mpls_nh = string();` (routesync.h L122) → 空文字列

**emit 条件** (routesync.cpp L2281-2284):
```cpp
if (!mpls_list.empty())
    fvw.mpls_nh = std::move(mpls_list);
```
→ MPLS encap なし経路では emit しない。

### `vni_label` / `router_mac` / `segment` / `seg_src`

**宣言デフォルト**: 全て `string() = ""` (routesync.h L124-127)

EVPN / SRv6 経路専用フィールド。それぞれの専用 handler (`onEvpnRouteMsg()`、`onSrv6SteerRouteMsg()`) が設定する場合のみ emit。通常 unicast 経路では存在しない。

**orchagent での `vni_label` 消費** (routeorch.cpp L757-759):
```cpp
if (fvField(i) == "vni_label" && fvValue(i) != "") {
    vni_labels = fvValue(i);
    overlay_nh = true;
}
```
→ `vni_label` が存在すると `overlay_nh=true` フラグが立ち、EVPN overlay nexthop として処理。

## ZMQ path の差異

`ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED` が有効な場合:
- `nbZmqEnabled=true` → `fieldValueTupleVector()` は全フィールドを条件なしで送信 (routesync.cpp L1006-1017)
- フィールド不在が発生しないため orchagent 側の「フィールド不在=デフォルト」ロジックは使われない
- `blackhole="false"` も明示送信される

## 管理 VRF / eth0 スキップルール

- VRF 名が `mgmt` で始まる場合: `onRouteMsg()` が即 return (routesync.cpp L2125-2137)
- nexthop が `eth0` / `docker0` / `eth1-midplane` 単一の場合: DEL を送信して経路を削除 (routesync.cpp L2250-2257)

## トレース証跡サマリ

- 訪問ファイル: 3 ファイル (routesync.h, routesync.cpp, routeorch.cpp)
- 訪問関数: 10 関数
- 検出 fallback: 9 件
  - `blackhole` 宣言デフォルト `"false"` + non-ZMQ 条件 emit
  - `protocol` 未知番号 → 数値文字列フォールバック
  - `weight` kernel 0 → 1 フォールバック (libnl path と NHG path の両方)
  - `nexthop` interface route で IPv4=`"0.0.0.0"` / IPv6=`"::"` デフォルト
  - `nexthop_group` + `nexthop`/`ifname` 排他チェック → 棄却
  - ZMQ path では全フィールド常時 emit (non-ZMQ と挙動差異)
  - 管理 VRF (`mgmt`) スキップ
  - `eth0`/`docker0`/`eth1-midplane` 経路 → DEL 変換
  - `vni_label` 存在 → `overlay_nh=true` 自動フラグ
