# mux-cable-state — Phase E constants 調査メモ

## 調査対象

`STATE_DB.MUX_CABLE_TABLE` / `STATE_DB.HW_MUX_CABLE_TABLE` の実装に含まれるハードコード定数。

## ソース

- `sonic-swss/orchagent/muxorch.cpp` (lines 48-95)
- `sonic-swss/orchagent/tunneldecaporch.h` (line 21)
- `sonic-swss/orchagent/aclorch.h` (lines 111-112)
- `sonic-swss-common/common/schema.h` (lines 140-143, 457-465)
- `sonic-platform-daemons/sonic-ycabled/ycable/ycable_utilities/y_cable_helper.py` (lines 55-115)
- `sonic-linkmgrd/src/DbInterface.cpp` (lines 667-730)
- `sonic-linkmgrd/src/DbInterface.h` (line 58)

## 発見した定数

### muxorch.cpp — STATE 文字列リテラル (lines 48-95)

```cpp
#define MUX_HW_STATE_UNKNOWN "unknown"   // line 50
#define MUX_HW_STATE_ERROR   "error"     // line 51
#define MUX_ACL_TABLE_NAME   INGRESS_TABLE_DROP  // = "IngressTableDrop"  line 48
#define MUX_ACL_RULE_NAME    "mux_acl_rule"       // line 49
```

state 文字列マッピング (lines 68-84):
- `MUX_STATE_ACTIVE`  → `"active"`
- `MUX_STATE_STANDBY` → `"standby"`
- `MUX_STATE_INIT`    → `"init"`
- `MUX_STATE_FAILED`  → `"failed"`
- `MUX_STATE_PENDING` → `"pending"`

reverse マッピング (incoming `"unknown"` → `MUX_STATE_STANDBY`) (line 81):
- `"unknown"` input is silently mapped to `MUX_STATE_STANDBY` (not `MUX_STATE_UNKNOWN`)

### tunneldecaporch.h — トンネル名 (line 21)

```cpp
#define MUX_TUNNEL "MuxTunnel0"
```

### schema.h — テーブル名定数 (lines 457-465)

```cpp
#define STATE_MUX_CABLE_TABLE_NAME                "MUX_CABLE_TABLE"
#define STATE_HW_MUX_CABLE_TABLE_NAME             "HW_MUX_CABLE_TABLE"
#define STATE_MUX_LINKMGR_TABLE_NAME              "MUX_LINKMGR_TABLE"
#define STATE_MUX_METRICS_TABLE_NAME              "MUX_METRICS_TABLE"
#define STATE_MUX_CABLE_INFO_TABLE_NAME           "MUX_CABLE_INFO"
#define STATE_PEER_HW_FORWARDING_STATE_TABLE_NAME "HW_MUX_CABLE_TABLE_PEER"
```

APP_DB テーブル (lines 140-143):
```cpp
#define APP_MUX_CABLE_TABLE_NAME         "MUX_CABLE_TABLE"
#define APP_HW_MUX_CABLE_TABLE_NAME      "HW_MUX_CABLE_TABLE"
#define APP_MUX_CABLE_COMMAND_TABLE_NAME "MUX_CABLE_COMMAND_TABLE"
#define APP_MUX_CABLE_RESPONSE_TABLE_NAME "MUX_CABLE_RESPONSE_TABLE"
```

### y_cable_helper.py — gRPC / ycabled 定数 (lines 55-115)

```python
GRPC_PORT = 50075                     # line 55
read_side = -1                        # line 57 (global initial, unresolved)

LOOPBACK_INTERFACE_T0   = "10.212.64.1/32"   # line 63
LOOPBACK_INTERFACE_LT0  = "10.212.64.2/32"   # line 64
LOOPBACK_INTERFACE_T0_NIC  = "10.1.0.38/32"  # line 65
LOOPBACK_INTERFACE_LT0_NIC = "10.1.0.39/32"  # line 66

GRPC_CLIENT_OPTIONS = [
    ('grpc.keepalive_timeout_ms', 8000),   # line 71
    ('grpc.keepalive_time_ms', 4000),      # line 72
    ('grpc.keepalive_permit_without_calls', True),  # line 73
    ('grpc.http2.max_pings_without_data', 0)        # line 74
]

CONFIG_MUX_STATES = ["active", "standby", "auto", "manual", "detach"]   # line 76
DEFAULT_PORT_IDS = [0, 1]              # line 78

Y_CABLE_STATUS_NO_TOR_ACTIVE = 0      # line 109
Y_CABLE_STATUS_TORA_ACTIVE = 1        # line 110
Y_CABLE_STATUS_TORB_ACTIVE = 2        # line 111
```

### DbInterface.cpp — Loopback3 文字列 (line 672)

```cpp
const std::string loopback3 = "Loopback3|";
```

Loopback3 IPv4 が見つからない場合 `MUXLOGFATAL` を出してデフォルト値を使用 (line 730)。

## 注目すべき点

1. `"unknown"` 文字列の入力は `MUX_STATE_STANDBY` にマッピングされる (muxorch.cpp:81)。つまり
   APP_DB から `unknown` が来ても orchagent は内部で standby として処理する。
2. gRPC ポート `50075` は環境変数・CONFIG_DB のいずれからも変更不可。SoC IP (`soc_ipv4`) は
   CONFIG_DB から取得するが、接続ポートはコード固定。
3. `MuxTunnel0` トンネル名はコード固定。`DEVICE_METADATA` や `MIRROR_SESSION` など、
   トンネル名を外から注入する手段はない。
4. `mux_acl_rule` ACL ルール名もコード固定 (muxorch.cpp:49)。
5. Loopback3 IP のデフォルト値 (`10.212.64.1/32` 等) はコード定数だが、実際には CONFIG_DB の
   値を読んで上書きするため、デフォルトが実効する状況 = FATAL 状態。
