# APPL_DB ROUTE_TABLE — Phase A: コード由来デフォルト

調査対象: `docs/reference/config-db/app-route.md`
Phase A 目的: APPL_DB `ROUTE_TABLE` シンプル経路フィールドのコード由来デフォルト確定

## ソースファイル

- `sonic-swss/fpmsyncd/routesync.h` L101-L127 — `RouteTableFieldValueTupleWrapper` 構造体定義
- `sonic-swss/fpmsyncd/routesync.cpp` L1000-L1055 — `fieldValueTupleVector()` 書き込みロジック
- `sonic-swss/fpmsyncd/routesync.cpp` L2111-L2303 — `onRouteMsg()` フィールド設定ロジック
- `sonic-swss/orchagent/routeorch.cpp` L720-L804 — consumer 側フィールド読み取り
- `sonic-swss-common/common/schema.h` L47 — `APP_ROUTE_TABLE_NAME "ROUTE_TABLE"`

sha: HEAD (sonic-swss master)

---

## RouteTableFieldValueTupleWrapper C++ 初期値

`routesync.h` L116-L126:

```cpp
class RouteTableFieldValueTupleWrapper : public FieldValueTupleWrapperBase {
    string protocol = string();           // 空文字列
    string blackhole = string("false");   // "false"
    string nexthop = string();            // 空文字列
    string ifname = string();             // 空文字列
    string nexthop_group = string();      // 空文字列
    string mpls_nh = string();            // 空文字列
    string weight = string();             // 空文字列
    string vni_label = string();          // 空文字列
    string router_mac = string();         // 空文字列
    string segment = string();            // 空文字列
    string seg_src = string();            // 空文字列
};
```

## APPL_DB 省略ロジック (非 ZMQ パス)

`routesync.cpp` L1018-L1051:

```cpp
if (protocol != string())          push("protocol");   // 空なら省略
if (blackhole != string("false"))  push("blackhole");  // "false" なら省略
if (nexthop != string())           push("nexthop");
if (ifname != string())            push("ifname");
if (nexthop_group != string())     push("nexthop_group");
if (mpls_nh != string())           push("mpls_nh");
if (weight != string())            push("weight");
if (vni_label != string())         push("vni_label");
if (router_mac != string())        push("router_mac");
if (segment != string())           push("segment");
if (seg_src != string())           push("seg_src");
```

ZMQ 有効時（`nbZmqEnabled == true`）は全フィールドを常に送信（空文字列含む）。

## フィールド別デフォルトまとめ

| フィールド | writer C++ 初期値 | APPL_DB 省略条件 | orchagent 受信時デフォルト |
|-----------|-----------------|----------------|--------------------------|
| `protocol` | `""` | 空文字列のとき | 空文字列（スキップ） |
| `blackhole` | `"false"` | `"false"` のとき | `bool blackhole = false` |
| `nexthop` | `""` | 空文字列のとき | 空文字列（ルートスキップ） |
| `ifname` | `""` | 空文字列のとき | 空文字列（ルートスキップ） |
| `nexthop_group` | `""` | 空文字列のとき | 空文字列 |
| `mpls_nh` | `""` | 空文字列のとき | 空文字列 |
| `weight` | `""` | 空文字列のとき | 空文字列（均等分散） |
| `vni_label` | `""` | 空文字列のとき | `overlay_nh = false` |
| `router_mac` | `""` | 空文字列のとき | 空文字列 |
| `segment` | `""` | 空文字列のとき | `srv6_seg = false` |
| `seg_src` | `""` | 空文字列のとき | 空文字列 |

## onRouteMsg() フィールド設定の流れ

`routesync.cpp` L2171-L2303:

1. `RTN_BLACKHOLE`: `fvw.blackhole = "true"` のみ。他フィールドは初期値。
2. `RTN_UNICAST` + NHG ID あり:
   - 単一 NH: `fvw.nexthop`, `fvw.ifname`, (必要なら)`fvw.weight` を設定
   - マルチ NH: `fvw.nexthop_group` のみ設定（`nexthop`/`ifname` は設定しない）
3. `RTN_UNICAST` + NHG ID なし:
   - `getNextHopList()` → `fvw.nexthop`, `fvw.ifname`
   - `getNextHopWt()` → (空でなければ) `fvw.weight`
   - mpls_list が空でなければ `fvw.mpls_nh`

## orchagent consumer 側デフォルト

`routeorch.cpp` L727-L803:

```cpp
bool blackhole = false;          // フィールド不在 → false
string ips;                      // "nexthop" フィールドから
string aliases;                  // "ifname" フィールドから
string mpls_nhs;                 // "mpls_nh" フィールドから
string weights;                  // "weight" フィールドから
string nhg_index;                // "nexthop_group" フィールドから
string srv6_segments;            // "segment" フィールドから
string srv6_source;              // "seg_src" フィールドから
bool overlay_nh = false;         // "vni_label" が存在すれば true
bool fallback_to_default_route = false;  // "fallback_to_default_route" == "true"
```

`nexthop_group` と `nexthop`/`ifname` の同時指定はエラー（L810-L814）。

## protocol 文字列変換

`getProtocolString()` は `rtnl_route_proto2str()` を呼ぶ（libnl）。
典型的な変換: `RTPROT_STATIC` → `"static"`, `RTPROT_BGP` → `"bgp"` など。
未知プロトコルは数値文字列に変換。
