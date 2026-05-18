# route-handler-cross-refs — RouteSync (fpmsyncd) 暗黙参照 (Phase C)

ソース: `fpmsyncd/routesync.cpp`, `fpmsyncd/routesync.h`, `fpmsyncd/fpmsyncd.cpp`
SHA: `4305596156d70e9797e8a881b3d19b46de0bce0d`

## 入力参照（RouteSync が読み取るテーブル）

### 1. CONFIG_DB:DEVICE_METADATA|localhost — suppress-fib-pending フラグ

`fpmsyncd.cpp:113` で起動時に 1 回のみ `hget("localhost", "suppress-fib-pending", ...)` を読む。
値が `"enabled"` の場合、orchagent からの応答を待つ suppress-FIB pending モードに切り替わり、
`APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL` の NotificationConsumer が有効化される。

```cpp
// fpmsyncd.cpp:113-118
deviceMetadataTable.hget("localhost", "suppress-fib-pending", suppressionEnabledStr);
if (suppressionEnabledStr == "enabled")
{
    routeResponseChannel = std::make_unique<NotificationConsumer>(&applStateDb, routeResponseChannelName);
    sync.setSuppressionEnabled(true);
}
```

起動後の変更は fpmsyncd 再起動まで反映されない（`SubscriberStateTable deviceMetadataTableSubscriber` は
フィールド変更を監視するが、suppress-fib-pending の動的変更パスは `fpmsyncd.cpp:278` で個別に処理）。

### 2. STATE_DB:BGP_STATE_TABLE — EOIU フラグ（warm-restart 時のみ）

warm-restart が有効な場合、`fpmsyncd.cpp:54-70` の `eoiuFlagsSet()` が
`BGP_STATE_TABLE|IPv4|eoiu.state` および `BGP_STATE_TABLE|IPv6|eoiu.state` を定期ポーリングする。
両フラグが `"reached"` になると EOIU ホールドタイマーを起動して reconciliation に移行する。

```cpp
// fpmsyncd.cpp:54-70
static bool eoiuFlagsSet(Table &bgpStateTable) {
    string value;
    bgpStateTable.hget("IPv4|eoiu", "state", value);
    bool v4 = (value == "reached");
    bgpStateTable.hget("IPv6|eoiu", "state", value);
    return v4 && (value == "reached");
}
```

非 warm-restart 起動では `bgpStateTable` は参照されない。

### 3. APPL_STATE_DB (ROUTE_TABLE_RESPONSE_CHANNEL) — suppress-fib-pending 応答（条件付き）

`suppress-fib-pending` が有効な場合のみ。orchagent が SAI プログラミング結果を
`APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL` チャネル経由で通知し、fpmsyncd がそれを受信して
`onRouteResponse()` を呼び出す。成功応答（`err_str=SWSS_RC_SUCCESS`）で FRR への FIB オフロード通知
(`RTM_F_OFFLOAD` フラグ付き netlink メッセージ) を送信する。

## 出力テーブル（RouteSync が書き込むテーブル）

| APPL_DB テーブル | マクロ名 | ハンドラ |
|---|---|---|
| `ROUTE_TABLE` | `APP_ROUTE_TABLE_NAME` | `onRouteMsg()` / `onEvpnRouteMsg()` / `onSrv6SteerRouteMsg()` / `onSrv6VpnRouteMsg()` |
| `NEXTHOP_GROUP_TABLE` | `APP_NEXTHOP_GROUP_TABLE_NAME` | `onNextHopMsg()` |
| `LABEL_ROUTE_TABLE` | `APP_LABEL_ROUTE_TABLE_NAME` | `onLabelRouteMsg()` |
| `VNET_ROUTE_TABLE` | `APP_VNET_RT_TABLE_NAME` | `onVnetRouteMsg()` |
| `VNET_ROUTE_TUNNEL_TABLE` | `APP_VNET_RT_TUNNEL_TABLE_NAME` | `onVnetRouteMsg()` (VXLAN tunnel 経路) |
| `SRV6_MY_SID_TABLE` | `APP_SRV6_MY_SID_TABLE_NAME` | `onSrv6MySidMsg()` |
| `SRV6_SID_LIST_TABLE` | `APP_SRV6_SID_LIST_TABLE_NAME` | `onSrv6RouteMsg()` 内 SID list 登録 |
| `PIC_CONTEXT_TABLE` | `APP_PIC_CONTEXT_TABLE_NAME` | `onPicContextMsg()` |

Evidence: `routesync.cpp:156-164` (ProducerStateTable 初期化); `fpmsyncd.cpp:78-118` (接続・suppress 設定)
