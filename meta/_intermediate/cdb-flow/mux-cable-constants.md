# mux-cable Phase E — ハードコード定数

source: `sonic-swss/orchagent/muxorch.cpp`, `sonic-swss/orchagent/muxorch.h`, `sonic-swss/orchagent/tunneldecaporch.h`, `sonic-swss-common/common/schema.h`

## state enum (MuxState)

```cpp
// muxorch.h:15-22
enum MuxState
{
    MUX_STATE_INIT,     // "init"   — 初期状態 / warmboot復旧待ち
    MUX_STATE_ACTIVE,   // "active" — このToRがトラフィックを転送
    MUX_STATE_STANDBY,  // "standby"— ピアToR経由で転送
    MUX_STATE_PENDING,  // "pending"— 状態遷移中
    MUX_STATE_FAILED,   // "failed" — プローブ失敗等で異常
};
```

## state enum (MuxStateChange) — 状態遷移

```cpp
// muxorch.h:24-31
enum MuxStateChange
{
    MUX_STATE_INIT_ACTIVE,
    MUX_STATE_INIT_STANDBY,
    MUX_STATE_ACTIVE_STANDBY,
    MUX_STATE_STANDBY_ACTIVE,
    MUX_STATE_UNKNOWN_STATE
};
```

## MuxCableType enum

```cpp
// muxorch.h:33-37
enum MuxCableType
{
    ACTIVE_STANDBY,   // "active-standby" (default)
    ACTIVE_ACTIVE     // "active-active"
};
```

## MuxNbrHandlerType enum

```cpp
// muxorch.h:39-43
enum MuxNbrHandlerType
{
    NBR_HANDLER_HOST_ROUTE,   // neighbor_mode="host-route" (default)
    NBR_HANDLER_PREFIX_BASED  // neighbor_mode="prefix-route"
};
```

## state 文字列マッピング

```cpp
// muxorch.cpp:68-85
const map<MuxState, string> muxStateValToString =
{
    { MUX_STATE_ACTIVE,  "active"  },
    { MUX_STATE_STANDBY, "standby" },
    { MUX_STATE_INIT,    "init"    },
    { MUX_STATE_FAILED,  "failed"  },
    { MUX_STATE_PENDING, "pending" },
};

const map<string, MuxState> muxStateStringToVal =
{
    { "active",  MUX_STATE_ACTIVE  },
    { "standby", MUX_STATE_STANDBY },
    { "unknown", MUX_STATE_STANDBY },  // "unknown" → STANDBY に fallback
    { "init",    MUX_STATE_INIT    },
    { "failed",  MUX_STATE_FAILED  },
    { "pending", MUX_STATE_PENDING },
};
```

重要: `"unknown"` 文字列は `MUX_STATE_STANDBY` として扱われる（ハードウェアが未知状態を返した場合に standby 動作）。

## HW state 定数

```cpp
// muxorch.cpp:50-51
#define MUX_HW_STATE_UNKNOWN "unknown"
#define MUX_HW_STATE_ERROR   "error"
```

## ACL テーブル定数

```cpp
// muxorch.cpp:48-49
#define MUX_ACL_TABLE_NAME INGRESS_TABLE_DROP  // = "INGRESS_TABLE_DROP"
#define MUX_ACL_RULE_NAME  "mux_acl_rule"
```

## トンネル名定数

```cpp
// tunneldecaporch.h:21
#define MUX_TUNNEL "MuxTunnel0"
```

active-standby 切替時のトンネルは常に `MuxTunnel0` として参照される。

## DB テーブル名定数 (schema.h)

```cpp
// sonic-swss-common/common/schema.h
#define APP_MUX_CABLE_TABLE_NAME         "MUX_CABLE_TABLE"      // APPL_DB
#define APP_HW_MUX_CABLE_TABLE_NAME      "HW_MUX_CABLE_TABLE"   // APPL_DB
#define APP_TUNNEL_ROUTE_TABLE_NAME      "TUNNEL_ROUTE_TABLE"   // APPL_DB
#define STATE_MUX_CABLE_TABLE_NAME       "MUX_CABLE_TABLE"      // STATE_DB
#define STATE_MUX_METRICS_TABLE_NAME     "MUX_METRICS_TABLE"    // STATE_DB
```

## 初期状態ハードコード

```cpp
// muxorch.cpp:437-448
if (WarmStart::isWarmStart()) {
    // warmboot: APP DB sync 後に前回の状態に復旧するまで init を保持
    state_ = MuxState::MUX_STATE_INIT;
}
else
{
    // 通常起動: 初期状態は standby
    stateStandby();
    state_ = MuxState::MUX_STATE_STANDBY;
}
```

**ハードコードデフォルト**: 通常起動時は常に `standby` から開始。warmboot 時は `init`。

## cable_type / neighbor_mode デフォルト

```cpp
// muxorch.cpp:2209-2210
MuxCableType cable_type = MuxCableType::ACTIVE_STANDBY;
auto nbr_handler_type = MuxNbrHandlerType::NBR_HANDLER_HOST_ROUTE;
```

フィールドが CONFIG_DB に設定されていない場合のコードレベルデフォルト:
- `cable_type` → `ACTIVE_STANDBY` ("active-standby")
- `neighbor_mode` → `NBR_HANDLER_HOST_ROUTE` ("host-route")

## SOC IP の扱い

```cpp
// muxorch.cpp:2218-2228
if (name == "soc_ipv4")
{
    auto soc_ip = request.getAttrIpPrefix("soc_ipv4");
    skip_neighbors.insert(soc_ip.getIp());  // neighbor テーブルから除外
}
else if (name == "soc_ipv6")
{
    auto soc_ip6 = request.getAttrIpPrefix("soc_ipv6");
    skip_neighbors.insert(soc_ip6.getIp());
}
```

`soc_ipv4` / `soc_ipv6` は active-active 構成の SoC IP アドレス。orchagent は当該 IP を `skip_neighbors` リストに追加し、通常の neighbor エントリ（ARP/NDP）として処理しないようにする。

## metrics タイムスタンプ精度

```cpp
// muxorch.cpp:2535
const int precision = 6;  // マイクロ秒精度 (6桁)
```

`MUX_METRICS_TABLE` に記録されるタイムスタンプは マイクロ秒 6桁精度。

## 状態遷移テーブル (有効な遷移のみ)

```cpp
// muxorch.cpp:53-66
const map<pair<MuxState, MuxState>, MuxStateChange> muxStateTransition =
{
    { {MUX_STATE_INIT,    MUX_STATE_ACTIVE},  MUX_STATE_INIT_ACTIVE    },
    { {MUX_STATE_INIT,    MUX_STATE_STANDBY}, MUX_STATE_INIT_STANDBY   },
    { {MUX_STATE_ACTIVE,  MUX_STATE_STANDBY}, MUX_STATE_ACTIVE_STANDBY },
    { {MUX_STATE_STANDBY, MUX_STATE_ACTIVE},  MUX_STATE_STANDBY_ACTIVE },
};
```

これ以外の遷移は `MUX_STATE_UNKNOWN_STATE` として扱われ、エラーログ後に無視される。
