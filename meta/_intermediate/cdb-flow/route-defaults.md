# ROUTE_TABLE — Phase A: コード由来の暗黙デフォルト調査

## 調査対象ソース

- `sonic-swss/fpmsyncd/routesync.h` — `RouteTableFieldValueTupleWrapper` 構造体メンバー宣言
- `sonic-swss/fpmsyncd/routesync.cpp` — `RouteTableFieldValueTupleWrapper::fieldValueTupleVector()` / `onRouteMsg()` / `getNextHopWt()`
- `sonic-swss/orchagent/routeorch.cpp` — フィールド消費側 (L746-804)
- `sonic-swss-common/common/schema.h` — テーブル名定数 `APP_ROUTE_TABLE_NAME = "ROUTE_TABLE"`

**注意**: `ROUTE_TABLE` は **APPL_DB** テーブルであり CONFIG_DB には存在しない。fpmsyncd が FRR (zebra/FPM) から netlink メッセージを受信して APPL_DB に書き込み、orchagent が読み取って SAI route へ変換する。

---

## 1. フィールドごとのコード由来デフォルト

### `protocol`

- **宣言** (`routesync.h` L116): `string protocol = string();`（空文字列）
- **生成** (`routesync.cpp` L2167-2168):
  ```cpp
  auto proto_num = rtnl_route_get_protocol(route_obj);
  auto proto_str = getProtocolString(proto_num);
  ```
  `getProtocolString()` は `rtnl_route_proto2str()` を呼び出し、/usr/share/iproute2/rt_protos から名前を解決。解決失敗時は数値文字列を返す。
- **書込み条件** (non-ZMQ path, L1019-1021):
  ```cpp
  if (protocol != string()) {
      fvVector.push_back(FieldValueTuple("protocol", protocol.c_str()));
  }
  ```
  空文字列の場合はフィールド自体が APPL_DB エントリに存在しない。
- **暗黙デフォルト**: rtm_protocol が不明な場合は数値文字列（例: `"186"`）。FRR 由来の経路は通常 `"bgp"` / `"static"` / `"kernel"` 等。フィールド不在の場合 orchagent は `ctx.protocol = ""` (L787 相当) として処理する。

### `blackhole`

- **宣言** (`routesync.h` L117): `string blackhole = string("false");`（**明示デフォルト `"false"`**）
- **生成** (`routesync.cpp` L2173-2179):
  ```cpp
  case RTN_BLACKHOLE:
  {
      RouteTableFieldValueTupleWrapper fvw {...};
      fvw.blackhole = "true";
      setRouteWithWarmRestart(fvw, *m_routeTable);
      return;
  }
  ```
  `RTN_BLACKHOLE` 経路のみ `"true"` を設定。それ以外 (`RTN_UNICAST`) ではコード上で `blackhole` フィールドを更新しないため、宣言デフォルトの `"false"` が維持される。
- **書込み条件** (non-ZMQ path, L1022-1024):
  ```cpp
  if (blackhole != string("false")) {
      fvVector.push_back(FieldValueTuple("blackhole", blackhole.c_str()));
  }
  ```
  `"false"` の場合はフィールドが APPL_DB に書き込まれない。`"true"` のみ書き込まれる。
- **ZMQ path** (L1008): 常に `"false"` または `"true"` を書き込む。
- **orchagent** (L765-766): `blackhole = fvValue(i) == "true"` でフィールド不在は `false`（通常経路）。
- **暗黙デフォルト**: `"false"`。フィールド不在 = blackhole 無効。

### `nexthop`

- **宣言** (`routesync.h` L119): `string nexthop = string();`（空文字列）
- **生成** (`routesync.cpp` L2278): `fvw.nexthop = std::move(gw_list);`（`getNextHopList()` の出力）
- カンマ区切りの nexthop IP リスト。ECMP の場合は複数 IP。
- **書込み条件** (non-ZMQ, L1025-1027): `nexthop != string()` の場合のみ書き込み。
- **interface route** (L2214): nexthop が空の場合: `nhg.nexthop.empty() ? (AF_INET ? "0.0.0.0" : "::") : nhg.nexthop`。interface-only route では `"0.0.0.0"` / `"::"` がプレースホルダーとして使われる。
- **暗黙デフォルト**: フィールド不在 = nexthop なし。orchagent は `ips` が空でも処理を継続する。

### `ifname`

- **宣言** (`routesync.h` L120): `string ifname = string();`（空文字列）
- **生成** (`routesync.cpp` L2279): `fvw.ifname = std::move(intf_list);`（`getNextHopList()` の出力）
- カンマ区切りの出力インターフェース名リスト。
- **eth0/docker0/eth1-midplane フィルタ** (L2250-2273): これらのインターフェースへの経路は APPL_DB 書き込みをスキップして DEL を送る（管理経路の混入防止）。
- **書込み条件** (non-ZMQ, L1028-1030): `ifname != string()` の場合のみ書き込み。
- **暗黙デフォルト**: フィールド不在 = 出力 IF なし（nexthop IP のみで転送先を決定）。

### `nexthop_group`

- **宣言** (`routesync.h` L121): `string nexthop_group = string();`（空文字列）
- **生成** (`routesync.cpp` L2227-2228):
  ```cpp
  nhg_id_key = getNextHopGroupKeyAsString(nhg_id);
  fvw.nexthop_group = std::move(nhg_id_key);
  ```
  kernel の nexthop group ID が存在する場合のみ設定。
- **書込み条件** (non-ZMQ, L1031-1033): `nexthop_group != string()` の場合のみ書き込み。
- **相互排他**: `nexthop_group` が設定された場合、`nexthop` / `ifname` は設定されない（L2225-2228 の分岐）。orchagent も両方存在する場合はエラーとして棄却 (L810-813)。
- **暗黙デフォルト**: フィールド不在 = 個別 nexthop/ifname で処理。

### `mpls_nh`

- **宣言** (`routesync.h` L122): `string mpls_nh = string();`（空文字列）
- **生成** (`routesync.cpp` L2281-2283):
  ```cpp
  if (!mpls_list.empty()) {
      fvw.mpls_nh = std::move(mpls_list);
  }
  ```
  `getNextHopList()` が MPLS ラベルを解析した場合のみ設定。非 MPLS 経路では空。
- **書込み条件** (non-ZMQ, L1034-1036): `mpls_nh != string()` の場合のみ書き込み。
- **暗黙デフォルト**: フィールド不在 = MPLS なし（通常 IP 転送）。

### `weight`

- **宣言** (`routesync.h` L123): `string weight = string();`（空文字列）
- **生成** (`routesync.cpp` L2244 + `getNextHopWt()` L3075-3098):
  ```cpp
  weights = getNextHopWt(route_obj);
  ```
  ```cpp
  uint8_t weight = rtnl_route_nh_get_weight(nexthop);
  if (weight == 0)
  {
      SWSS_LOG_INFO("Using default weight of 1 for nexthop");
      weight = 1; // default weight is 1
  }
  ```
  各 nexthop の weight が 0（未設定）の場合は **1** にフォールバック。カンマ区切り文字列として生成。
- **書込み条件** (L2285-2287 + non-ZMQ L1037-1039):
  ```cpp
  if (!weights.empty()) {
      fvw.weight = std::move(weights);
  }
  ```
- **ECMP 均等配分** (`routeorch.cpp` L768): `weight` フィールド不在の場合 orchagent は等コスト(equal-weight) として扱う。
- **暗黙デフォルト**: 単一 nexthop かつ weight=0 → `"1"` が書き込まれる。ECMP では各 nexthop に最低 `"1"` が保証される。フィールド不在 = orchagent がデフォルト等重みで処理。

### `vni_label`

- **宣言** (`routesync.h` L124): `string vni_label = string();`（空文字列）
- **生成**: EVPN 経路 (`onEvpnRouteMsg()`) のみ設定 (L921): `fvw.vni_label = std::move(vni_list);`
- VNI (VXLAN Network Identifier) のカンマ区切りリスト。
- **書込み条件** (non-ZMQ, L1040-1042): `vni_label != string()` の場合のみ書き込み。
- **orchagent** (L757-760): `vni_label != ""` の場合 `overlay_nh = true` を設定して EVPN オーバーレイ処理を行う。
- **暗黙デフォルト**: フィールド不在 = 非 EVPN 経路（通常 IP 転送）。

### `router_mac`

- **宣言** (`routesync.h` L125): `string router_mac = string();`（空文字列）
- **生成**: EVPN 経路 (`onEvpnRouteMsg()`) のみ設定 (L922): `fvw.router_mac = std::move(mac_list);`
- EVPN の宛先 VTEP MAC アドレスのカンマ区切りリスト。
- **書込み条件** (non-ZMQ, L1043-1045): `router_mac != string()` の場合のみ書き込み。
- **暗黙デフォルト**: フィールド不在 = 非 EVPN 経路。

### `segment`

- **宣言** (`routesync.h` L126): `string segment = string();`（空文字列）
- **生成**: SRv6 経路 (`onSrv6SteerRouteMsg()`) のみ設定 (L1439): `rfvw.segment = std::move(srv6SidListTableKey);`
- SRv6 SID リストキーの文字列。
- **書込み条件** (non-ZMQ, L1046-1048): `segment != string()` の場合のみ書き込み。
- **orchagent** (L774-778): `segment != ""` の場合 `srv6_seg = true; srv6_nh = true;` を設定して SRv6 処理へ分岐。
- **暗黙デフォルト**: フィールド不在 = 非 SRv6 経路。

### `seg_src`

- **宣言** (`routesync.h` L127 相当): `string seg_src = string();`（空文字列）
- **生成**: SRv6 経路 (`onSrv6SteerRouteMsg()`) のみ設定 (L1443):
  ```cpp
  rfvw.seg_src = std::move(src_addr_str);
  ```
  SRv6 encapsulation source IPv6 アドレス。
- **書込み条件** (non-ZMQ, L1049-1051): `seg_src != string()` の場合のみ書き込み。
- **orchagent** (L780-783): `seg_src != ""` の場合 `srv6_nh = true;`。
- **暗黙デフォルト**: フィールド不在 = SRv6 ソースアドレス指定なし。

---

## 2. ハードコード値

| 定数名 | 値 | 定義場所 | 意味 |
|--------|-----|---------|------|
| `APP_ROUTE_TABLE_NAME` | `"ROUTE_TABLE"` | `schema.h` L47 | APPL_DB テーブル名 |
| `APP_LABEL_ROUTE_TABLE_NAME` | `"LABEL_ROUTE_TABLE"` | `schema.h` L48 | MPLS ラベル経路テーブル名 |
| `DefaultRtProtoPath` | `"/usr/share/iproute2/rt_protos"` | `routesync.h` L58 | protocol 名解決のデフォルトパス |
| `OverrideRtProtoPath` | `"/etc/iproute2/rt_protos"` | `routesync.h` L60 | protocol 名解決のオーバーライドパス |
| `NHG_DELIMITER` | `','` | `routesync.cpp` L29 | nexthop/ifname/weight 区切り文字 |
| default weight | `1` | `routesync.cpp` L3087 | netlink weight=0 の場合のフォールバック値 |
| `VXLAN_IF_NAME_PREFIX` | `"Brvxlan"` | `routesync.cpp` L24 | EVPN 用 VXLAN ブリッジ IF プレフィックス |
| `VNET_PREFIX` | `"Vnet"` | `routesync.cpp` L25 | VNET 名プレフィックス判定 |
| `VRF_PREFIX` | `"Vrf"` | `routesync.cpp` L26 | VRF 名プレフィックス判定 |
| `MGMT_VRF_PREFIX` | `"mgmt"` | `routesync.cpp` L27 | 管理 VRF プレフィックス（スキップ対象） |
| `MAX_MULTIPATH_NUM` | `514` | `routesync.cpp` L121 | 最大マルチパス数 |

---

## 3. 書込み分岐サマリ (non-ZMQ vs ZMQ)

| フィールド | non-ZMQ 書込み条件 | ZMQ 書込み条件 |
|----------|-------------------|----------------|
| `protocol` | `!= ""` のみ | 常に書き込み（空でも） |
| `blackhole` | `!= "false"` のみ (`"true"` のみ) | 常に書き込み |
| `nexthop` | `!= ""` のみ | 常に書き込み |
| `ifname` | `!= ""` のみ | 常に書き込み |
| `nexthop_group` | `!= ""` のみ | 常に書き込み |
| `mpls_nh` | `!= ""` のみ | 常に書き込み |
| `weight` | `!= ""` のみ | 常に書き込み |
| `vni_label` | `!= ""` のみ | 常に書き込み |
| `router_mac` | `!= ""` のみ | 常に書き込み |
| `segment` | `!= ""` のみ | 常に書き込み |
| `seg_src` | `!= ""` のみ | 常に書き込み |

ZMQ path（`ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED` 有効時）では全フィールドが常に送信される。

---

## 4. Silent drop / 書込み順依存

### Silent drop: eth0/docker0/eth1-midplane へのルート

- `onRouteMsg()` L2250-2273: 出力 IF が `eth0`、`docker0`、`eth1-midplane` の場合は APPL_DB への SET の代わりに DEL を送信する。
- これは FRR が管理インターフェース向けデフォルト経路を誤って注入するケースへの対処。ログは `SWSS_LOG_DEBUG` レベルでのみ出力される（**silent drop に近い**）。

### Silent drop: EVPN nexthop または rmac が空

- `onEvpnRouteMsg()` L909-912:
  ```cpp
  if (nexthops.empty() || mac_list.empty())
  {
      SWSS_LOG_NOTICE("EVPN IP Prefix: %s nexthop or rmac is empty", destipprefix);
      return;
  }
  ```
  EVPN 経路で nexthop または MAC が取れない場合はサイレントスキップ。

### Silent drop: Multipath SRv6 経路

- `getSrv6SteerRouteNextHop()` L959-961: `RTA_MULTIPATH` がある SRv6 steer route は未対応としてドロップ。

### 書込み順依存: nexthop group の存在チェック

- `onRouteMsg()` L2204-2208: kernel の nexthop group ID が `m_nh_groups` に存在しない場合は `SWSS_LOG_ERROR` を出してルートをドロップ。nexthop group メッセージがルートメッセージより先に処理されている必要がある。

### 管理 VRF スキップ

- `onRouteMsg()` L2125-2136: VRF 名が `"mgmt"` プレフィックスを持つ場合は `SWSS_LOG_INFO` を出して処理をスキップ（管理 VRF の経路は APPL_DB に書かない）。

---

## 5. プラットフォーム依存

- `getProtocolString()` (L124-135): `/usr/share/iproute2/rt_protos`（`DefaultRtProtoPath`）が存在しない場合は protocol 番号を数値文字列で返す。`/etc/iproute2/rt_protos`（`OverrideRtProtoPath`）が存在すれば上書き可能（`rtnl_route_proto2str()` は iproute2 ライブラリ依存）。
- `MAX_MULTIPATH_NUM = 514`: ECMP 最大数はこの定数で制限されているが、orchagent 側の SAI 制限に依存する場合もある。

---

## 6. まとめ: defaults ブロックに追記すべき主要知見

1. **`blackhole`**: 宣言デフォルト `"false"`。non-ZMQ では `"true"` のみ APPL_DB に書き込まれ、フィールド不在 = `false`（blackhole 無効）。
2. **`protocol`**: FRR から rtm_protocol 番号を iproute2 ライブラリで名前解決。解決失敗時は数値文字列。フィールド不在時は orchagent が空文字列として扱う。
3. **`weight`**: netlink weight=0 の場合は **1** にフォールバック（`getNextHopWt()` L3087 ハードコード）。フィールド不在は orchagent が等コスト扱い。
4. **`nexthop`** / **`ifname`**: 空文字列がデフォルト。eth0/docker0/eth1-midplane は特殊フィルタで DEL に変換される。
5. **`nexthop_group`** vs **`nexthop`/`ifname`**: 相互排他。同時存在は orchagent がエラー棄却。
6. **`vni_label`** / **`router_mac`**: EVPN 経路のみ。フィールド不在 = 通常 IP 経路。
7. **`segment`** / **`seg_src`**: SRv6 経路のみ。フィールド不在 = 非 SRv6。
8. **`mpls_nh`**: MPLS nexthop がある場合のみ。フィールド不在 = 通常 IP 転送。
9. **管理 VRF**: mgmt VRF の経路は fpmsyncd がスキップするため APPL_DB に記録されない。
10. **ZMQ vs non-ZMQ**: ZMQ 有効時は全フィールドを常に送信するため、フィールド不在が発生しない（orchagent 側の「フィールド不在=デフォルト」ロジックが使われない）。
