# route-handler — Phase E ハードコード定数スキャンノート

対象ファイル:
- `fpmsyncd/routesync.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `fpmsyncd/fpmsyncd.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`

---

## 経路処理上限

### MAX_MULTIPATH_NUM = 514

`routesync.cpp` L121:

```cpp
#define MAX_MULTIPATH_NUM 514
```

nexthop group のメンバー数上限。`onRouteMsg()` 内 L2352-2355 でグループ数がこの値を超えた場合に SWSS_LOG_ERROR を出力してクランプする。kernel NHG path (`onMsgRaw()` L2510-2511) でも同様にクランプされる。超過分は永続的に欠落する。

### IPV4_MAX_BITLEN = 32 / IPV6_MAX_BITLEN = 128

`routesync.cpp` L54-55:

```cpp
#define IPV4_MAX_BITLEN    32
#define IPV6_MAX_BITLEN   128
```

プレフィックス長がこれより大きい場合、SWSS_LOG_ERROR で警告してその経路をスキップする (L787-796, L836-837)。ホストルート判定にも使用。

### protocolNameBufferSize = 128

`routesync.cpp` L126:

```cpp
static constexpr size_t protocolNameBufferSize = 128;
```

`getProtocolString()` 内で `rtnl_route_proto2str()` に渡すバッファサイズ。プロトコル名文字列がこれを超えると切り詰められる（実用上は問題なし）。

---

## encap タイプ識別子

### NH_ENCAP_VXLAN = 100

`routesync.cpp` L48:

```cpp
#define NH_ENCAP_VXLAN      100
```

VXLAN encap の識別番号。`getEncapType()` が返す値と比較して VXLAN 経路を識別。

### NH_ENCAP_SRV6_ROUTE = 101

`routesync.cpp` L50:

```cpp
#define NH_ENCAP_SRV6_ROUTE 101
```

`onMsgRaw()` のスイッチ分岐で SRv6 ステアリングルート (`onSrv6SteerRouteMsg()`) へ分岐するトリガー値。`101` はカーネルの `LWTUNNEL_ENCAP_SEG6` とは異なる SONiC 独自番号。

### VXLAN_VNI = 0

`routesync.cpp` L46:

```cpp
#define VXLAN_VNI             0
```

`tb_encap` 配列内 VNI 属性のインデックス (L254)。

---

## インタフェース名プレフィクス

`routesync.cpp` L24-27:

```cpp
#define VXLAN_IF_NAME_PREFIX    "Brvxlan"
#define VNET_PREFIX             "Vnet"
#define VRF_PREFIX              "Vrf"
#define MGMT_VRF_PREFIX         "mgmt"
```

- `VNET_PREFIX`: master デバイス名チェックで使用 (`onMsg()` L2076-2103)
- `VRF_PREFIX`: 同上
- `MGMT_VRF_PREFIX`: `onRouteMsg()` でこのプレフィクスの VRF をスキップ (L2131-2136)

---

## SRv6 My SID デフォルト長

`routesync.cpp` L59-62:

```cpp
#define DEFAULT_SRV6_MY_SID_BLOCK_LEN "32"
#define DEFAULT_SRV6_MY_SID_NODE_LEN  "16"
#define DEFAULT_SRV6_MY_SID_FUNC_LEN  "16"
#define DEFAULT_SRV6_MY_SID_ARG_LEN   "0"
```

`onSrv6MySidMsg()` でフィールドが APPL_DB に存在しない場合のフォールバック値。これらは RFC 8986 の典型値 (block=32, node=16, function=16) に対応している。

---

## タイマー・フラッシュ間隔

`fpmsyncd.cpp` L24-28, L46:

```cpp
#define INFINITE       -1
#define FLUSH_TIMEOUT  500   // 500 milliseconds
static int gFlushTimeout = FLUSH_TIMEOUT;
#define SMALL_TRAFFIC  500
...
const uint32_t DEFAULT_ROUTING_RESTART_INTERVAL = 120;
```

- `FLUSH_TIMEOUT = 500 ms`: Redis パイプラインのフラッシュ上限間隔。`flushPipeline()` (L335-363) のタイムアウト閾値。
- `SMALL_TRAFFIC = 500`: `remaining < SMALL_TRAFFIC` の場合に低トラフィックと判定して即時フラッシュ。
- `DEFAULT_ROUTING_RESTART_INTERVAL = 120 s`: warm-restart タイマーのデフォルト値。`DEVICE_METADATA.restart_timer` が未設定の場合に使用 (L158-160)。

これらは CONFIG_DB や YANG で上書きできない。warm-restart 中は `reconcile()` が呼ばれるまで APPL_DB への書き込みがバッファされる。
