# APPL_DB ROUTE_TABLE フィールドのコード由来デフォルト (Phase A)

調査対象: `docs/reference/config-db/appl-db-route.md`

## ソース

- `sonic-swss/fpmsyncd/routesync.h` — `RouteTableFieldValueTupleWrapper` 構造体定義
- `sonic-swss/fpmsyncd/routesync.cpp` — フィールド書き込みロジック
- `sonic-swss/orchagent/routeorch.cpp` — APPL_DB 読み取り / consumer 側

sha: `4305596156d70e9797e8a881b3d19b46de0bce0d` (sonic-swss)

---

## フィールド一覧と初期値

`routesync.h` L116-L126 の `RouteTableFieldValueTupleWrapper` 構造体メンバーから読み取った C++ 初期値:

| フィールド | C++ 初期値 | APPL_DB 省略条件 | 備考 |
|-----------|-----------|----------------|------|
| `protocol` | `string()` (空文字列) | 空文字列のとき省略 | `getProtocolString()` 変換値。静的経路 → `"static"` など |
| `blackhole` | `string("false")` | `"false"` のとき省略 | デフォルト: フィールドなし = false |
| `nexthop` | `string()` | 空のとき省略 | ECMP はカンマ区切り |
| `ifname` | `string()` | 空のとき省略 | ECMP はカンマ区切り |
| `nexthop_group` | `string()` | 空のとき省略 | NHG ID キー文字列 |
| `mpls_nh` | `string()` | 空のとき省略 | MPLS ラベルスタック |
| `weight` | `string()` | 空のとき省略 | ECMP 重み（カンマ区切り）|
| `vni_label` | `string()` | 空のとき省略 | EVPN VNI |
| `router_mac` | `string()` | 空のとき省略 | EVPN 宛先 MAC |
| `segment` | `string()` | 空のとき省略 | SRv6 SID-list テーブルキー |
| `seg_src` | `string()` | 空のとき省略 | SRv6 source address |

## 省略ロジック (非 ZMQ パス)

`routesync.cpp` L1019-L1051:

```cpp
// 非 ZMQ パス: 値が空 / デフォルトのときフィールドを送らない
if (protocol != string()) { push("protocol") }
if (blackhole != string("false")) { push("blackhole") }
if (nexthop != string()) { push("nexthop") }
if (ifname != string()) { push("ifname") }
if (nexthop_group != string()) { push("nexthop_group") }
if (mpls_nh != string()) { push("mpls_nh") }
if (weight != string()) { push("weight") }
// vni_label, router_mac, segment, seg_src も同様
```

ZMQ 有効時は全フィールドを常に送信する（空文字列含む）。

## orchagent (consumer) 側デフォルト

`routeorch.cpp` L737-L803:

```cpp
bool blackhole = false;      // フィールド不在 → false
string ips;                  // fvField == "nexthop" かつ非空 → 上書き
string aliases;              // fvField == "ifname" かつ非空 → 上書き
string weights;              // fvField == "weight" かつ非空 → 上書き
string nhg_index;            // fvField == "nexthop_group" かつ非空 → 上書き
string srv6_segments;        // fvField == "segment" かつ非空 → 上書き
string srv6_source;          // fvField == "seg_src" かつ非空 → 上書き
bool overlay_nh = false;     // vni_label 存在時 → true
bool fallback_to_default_route = false;
```

`blackhole` フィールドが absent の場合 orchagent は `false` と解釈する。

## key 構造

```
ROUTE_TABLE|<prefix>              (デフォルト VRF)
ROUTE_TABLE|Vrf<name>:<prefix>    (VRF-aware)
```

VRF 付きルートは key に `Vrf<name>:` プレフィクスが埋め込まれる（コロン区切り）。
`routesync.cpp` L826-L833 参照。

## `protocol` フィールドの変換

`getProtocolString()` (routesync.cpp L123-L130) が rtm_protocol 番号を文字列に変換:

| rtm_protocol 値 | 文字列 |
|----------------|-------|
| RTPROT_STATIC | `"static"` |
| RTPROT_BGP | `"bgp"` |
| RTPROT_OSPF | `"ospf"` |
| RTPROT_ISIS | `"isis"` |
| その他 | iproute2 `/etc/iproute2/rt_protos` 参照 |

`protocol` 未設定・不明プロトコルの場合は空文字列→フィールド省略。

## 排他: nexthop vs nexthop_group

orchagent は `nexthop_group` と `nexthop` / `ifname` が両方存在する場合エラーにする
(`routeorch.cpp` 内コメント: "A route should not fill both nexthop_group and ips/aliases")。
fpmsyncd 側も NHG ID が有効な場合は `nexthop_group` のみ、そうでなければ `nexthop`+`ifname` のみを送る。
