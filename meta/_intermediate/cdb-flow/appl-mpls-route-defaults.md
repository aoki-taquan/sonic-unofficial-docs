# APPL_DB LABEL_ROUTE_TABLE フィールド暗黙デフォルト調査メモ

調査日: 2026-05-15  
対象テーブル: APPL_DB `LABEL_ROUTE_TABLE`

## 調査対象ファイル

- `sonic-swss/fpmsyncd/routesync.h` — `LabelRouteTableFieldValueTupleWrapper` 定義
- `sonic-swss/fpmsyncd/routesync.cpp` — `onLabelRouteMsg()` / `LabelRouteTableFieldValueTupleWrapper::fieldValueTupleVector()`
- `sonic-swss/orchagent/mplsrouteorch.cpp` — `doLabelTask()` / `addLabelRoute()`
- `sonic-swss/tests/test_mpls.py` — 統合テスト

---

## テーブル概要

`fpmsyncd` がカーネルの netlink から MPLS inseg（受信ラベルルート）を受信し、
`APPL_DB:LABEL_ROUTE_TABLE` に書き込む。`routeorch::doLabelTask()` がそれを購読して
SAI `inseg_entry` を作成する。

key 構造: `LABEL_ROUTE_TABLE|<incoming-label>`  
(VRF あり: `LABEL_ROUTE_TABLE|<vrf-name>:<incoming-label>`)

---

## フィールド別 暗黙デフォルト

### `protocol`

**コード由来デフォルト**: `""` (空文字列 = 省略)

```cpp
// routesync.h:144
string protocol = string();
```

非空のときのみ fvVector に追加される（非 ZMQ パス）。
値は `getProtocolString(rtm_protocol)` により Linux rt_protos 名（例: `"bgp"`, `"zebra"`, `"static"`）に変換される。
省略時は routeorch 側でデフォルト扱い（無視）。

```cpp
// routesync.cpp:1073-1075
if (protocol != string()) {
    fvVector.push_back(FieldValueTuple("protocol", protocol.c_str()));
}
```

---

### `blackhole`

**コード由来デフォルト**: `"false"`

```cpp
// routesync.h:145
string blackhole = string("false");
```

`"false"` は送信されない（デフォルト値と一致するためスキップ）。
`RTN_BLACKHOLE` タイプのルートのとき `"true"` に設定される。

```cpp
// routesync.cpp:1076-1078
if (blackhole != string("false")) {
    fvVector.push_back(FieldValueTuple("blackhole", blackhole.c_str()));
}
// onLabelRouteMsg:2693
fvw.blackhole = "true";  // RTN_BLACKHOLE のみ
```

routeorch 側: `blackhole = fvValue(i) == "true"` で変換（mplsrouteorch.cpp:152）。

---

### `nexthop`

**コード由来デフォルト**: `""` (空文字列 = 省略)

```cpp
// routesync.h:146
string nexthop = string();
```

ゲートウェイ IP アドレスのカンマ区切りリスト。
`getNextHopList()` が netlink nexthop から取得する。
空のときは省略（非 ZMQ パス）。

```cpp
// onLabelRouteMsg:2726
fvw.nexthop = std::move(gw_list);
```

---

### `ifname`

**コード由来デフォルト**: `""` (空文字列 = 省略)

```cpp
// routesync.h:147
string ifname = string();
```

出力インタフェース名のカンマ区切りリスト。
`getNextHopList()` が netlink nexthop から取得する。

routeorch: `ifname` が空かつ非 blackhole の場合はルートをスキップ:
```cpp
// mplsrouteorch.cpp:193-197
if (alsv.size() == 0 && !blackhole)
{
    SWSS_LOG_WARN("Skip the route %s, for it has an empty ifname field.", key.c_str());
    it = consumer.m_toSync.erase(it);
    continue;
}
```

---

### `mpls_nh`

**コード由来デフォルト**: `""` (空文字列 = 省略)

```cpp
// routesync.h:148
string mpls_nh = string();
```

outgoing MPLS ラベル操作のカンマ区切りリスト。
フォーマット: `push<label>` / `swap<label>` / `na`（IP forward）。

空のとき省略（非 ZMQ パス）。
`onLabelRouteMsg` では mpls_list が空でない場合のみセット:

```cpp
// routesync.cpp:2729-2732
if (!mpls_list.empty())
{
    fvw.mpls_nh = std::move(mpls_list);
}
```

routeorch 側: `"na"` を含む要素は MPLS ラベルなし扱い:
```cpp
// mplsrouteorch.cpp:244
if (!mpls_nhv.empty() && mpls_nhv[i] != "na")
{
    nhg_str += mpls_nhv[i] + LABELSTACK_DELIMITER;
}
```

---

### `mpls_pop`

**コード由来デフォルト**: `""` (空文字列 = 省略 → routeorch では `pop_count = 0`)

```cpp
// routesync.h:149
string mpls_pop = string();
```

受信ラベルを何段 pop するかの数値文字列。
`onLabelRouteMsg` では**常に `"1"` にセット**（ラベルルートでは必ず 1 段 pop）:

```cpp
// routesync.cpp:2728
fvw.mpls_pop = "1";
```

routeorch 側:
```cpp
// mplsrouteorch.cpp:148-149
if (fvField(i) == "mpls_pop")
    pop_count = to_uint<uint8_t>(fvValue(i));
// → SAI: SAI_INSEG_ENTRY_ATTR_NUM_OF_POP = pop_count
```

省略（空文字列）のとき `pop_count` は 0 のまま（uint8_t ゼロ初期化）。
SAI の `SAI_INSEG_ENTRY_ATTR_NUM_OF_POP` が 0 = ラベル pop なし。

---

### `weight`

**コード由来デフォルト**: `""` (空文字列 = 省略)

`LabelRouteTableFieldValueTupleWrapper` には `weight` フィールドが存在しない
（routesync.h の LabelRoute ラッパーには定義なし）。

routeorch 側では受け付ける:
```cpp
// mplsrouteorch.cpp:154-155
if (fvField(i) == "weight")
    weights = fvValue(i);
```

ECMP NHG で使用。省略時は均等分散（NextHopGroupKey で重みなし）。

---

### `nexthop_group`

**コード由来デフォルト**: `""` (空文字列 = 省略)

`LabelRouteTableFieldValueTupleWrapper` には定義なし（routesync.h）。
routeorch 側では受け付け、NhgOrch から NHG を参照する:
```cpp
// mplsrouteorch.cpp:157-158
if (fvField(i) == "nexthop_group")
    nhg_index = fvValue(i);
```

`nexthop_group` と `nexthop`/`ifname` の同時指定はエラー。

---

## まとめ表

| フィールド | C++ 初期値 | fvVector 条件 | 実運用デフォルト |
|-----------|-----------|--------------|----------------|
| `protocol` | `""` | 非空のみ送信 | 省略 → routeorch 無視 |
| `blackhole` | `"false"` | `!= "false"` のみ送信 | `"false"`（省略） |
| `nexthop` | `""` | 非空のみ送信 | GW IP リスト（必須に準ずる） |
| `ifname` | `""` | 非空のみ送信 | intf リスト（必須に準ずる） |
| `mpls_nh` | `""` | 非空のみ送信 | outgoing ラベル操作リスト（省略可） |
| `mpls_pop` | `""` | 非空のみ送信 | fpmsyncd は常に `"1"` を書く |
| `weight` | N/A（ラッパー未定義） | routeorch のみ受け付け | 省略 = 均等分散 |
| `nexthop_group` | N/A（ラッパー未定義） | routeorch のみ受け付け | 省略 |

---

## ソース参照

| ファイル | 行 | 内容 |
|---------|---|------|
| `sonic-swss/fpmsyncd/routesync.h` | 129-150 | `LabelRouteTableFieldValueTupleWrapper` 定義・初期値 |
| `sonic-swss/fpmsyncd/routesync.cpp` | 1059-1093 | `fieldValueTupleVector()` 実装 |
| `sonic-swss/fpmsyncd/routesync.cpp` | 2646-2735 | `onLabelRouteMsg()` 実装 |
| `sonic-swss/orchagent/mplsrouteorch.cpp` | 20-418 | `doLabelTask()` 実装 |
| `sonic-swss/orchagent/mplsrouteorch.cpp` | 460-664 | `addLabelRoute()` SAI 変換 |
| `sonic-swss/tests/test_mpls.py` | 273-502 | 統合テスト（フィールド値例） |
