---
title: LABEL_ROUTE_TABLE (APPL_DB)
description: "APPL_DB LABEL_ROUTE_TABLE — MPLS incoming-label ルートエントリ。fpmsyncd がカーネル netlink から受信した MPLS inseg ルートを書き込み、routeorch が SAI inseg_entry に変換する。"
area: reference
verification: code-verified
last_verified: 2026-05-15
sources:
  - repo: sonic-net/sonic-swss
    path: fpmsyncd/routesync.h
    ref: HEAD
  - repo: sonic-net/sonic-swss
    path: fpmsyncd/routesync.cpp
    ref: HEAD
  - repo: sonic-net/sonic-swss
    path: orchagent/mplsrouteorch.cpp
    ref: HEAD
  - repo: sonic-net/sonic-swss
    path: orchagent/nhgorch.cpp
    ref: HEAD
related:
  config_db: []
  cli:
    - show mpls route
  yang: []
---

# LABEL_ROUTE_TABLE (APPL_DB)

## 概要

`APPL_DB:LABEL_ROUTE_TABLE` は MPLS **incoming-label ルート**（inseg エントリ）を保持するテーブル。
`fpmsyncd` がカーネルの netlink メッセージ（`RTM_NEWROUTE` / `RTM_DELROUTE`、アドレスファミリ MPLS）を
受信すると `LabelRouteTableFieldValueTupleWrapper` を通じて書き込む。
`routeorch` の `doLabelTask()` がこのテーブルを購読し、SAI `inseg_entry` を作成・更新・削除する。

<!-- cdb-mermaid -->
### データフロー

```mermaid
flowchart LR
  FRR["FRR / zebra<br/>(MPLS ラベル割当)"]
  KERN["Linux kernel<br/>(MPLS ルーティング)"]
  FPMS["fpmsyncd<br/>onLabelRouteMsg()"]
  APPL[("APPL_DB<br/>LABEL_ROUTE_TABLE")]
  RORCH["routeorch<br/>doLabelTask()"]
  SAI["SAI MPLS API<br/>inseg_entry"]
  HW["ASIC"]
  FRR -->|FPM netlink| FPMS
  KERN -->|netlink RTM_NEWROUTE| FPMS
  FPMS -->|ProducerStateTable SET| APPL
  APPL -->|ConsumerStateTable| RORCH
  RORCH --> SAI --> HW
```
<!-- /cdb-mermaid -->

## key 構造

```text
LABEL_ROUTE_TABLE|<incoming-label>
LABEL_ROUTE_TABLE|<vrf-name>:<incoming-label>
```

- `<incoming-label>`: 受信 MPLS ラベル値（uint32）
- `<vrf-name>`: VRF 名（非デフォルト VRF の場合。現在 fpmsyncd は非デフォルト VRF の MPLS ルートを `SWSS_LOG_INFO` のみ出力してスキップする）

## フィールド

| フィールド | 型 | デフォルト | 説明 |
|-----------|----|-----------|------|
| `nexthop` | string | `""` (省略) | outgoing ゲートウェイ IP アドレスのカンマ区切りリスト。ECMP 時は複数エントリをカンマで並べる |
| `ifname` | string | `""` (省略) | 出力インタフェース名のカンマ区切りリスト。`nexthop` と要素数を一致させる必要がある |
| `mpls_nh` | string | `""` (省略) | outgoing MPLS ラベル操作のカンマ区切りリスト。`push<N>` / `swap<N>` / `na`（IP 転送）の形式 |
| `mpls_pop` | string | `""` (省略、fpmsyncd は常に `"1"` を書く) | 受信ラベルを pop する段数。SAI `SAI_INSEG_ENTRY_ATTR_NUM_OF_POP` にマップされる |
| `blackhole` | boolean string | `"false"` (省略) | `"true"` のとき `SAI_PACKET_ACTION_DROP` を設定するブラックホールルート |
| `protocol` | string | `""` (省略) | ルート起源プロトコル名。Linux rt_protos 由来（例: `"bgp"`, `"zebra"`, `"static"`）。省略時は routeorch が無視 |
| `weight` | string | `""` (省略) | ECMP ネクストホップ重みのカンマ区切りリスト。省略時は均等分散 |
| `nexthop_group` | string | `""` (省略) | NhgOrch が管理する NHG インデックス。指定時は `nexthop`/`ifname` と排他 |

<!-- defaults -->
### コード由来デフォルトの根拠

#### `protocol` — デフォルト `""` (省略)

`LabelRouteTableFieldValueTupleWrapper` の初期値は `string()`（空文字列）。
非 ZMQ パスでは非空のときのみ fvVector に追加される:

```cpp
// sonic-swss fpmsyncd/routesync.h:144
string protocol = string();

// fpmsyncd/routesync.cpp:1073-1075
if (protocol != string()) {
    fvVector.push_back(FieldValueTuple("protocol", protocol.c_str()));
}
```

`onLabelRouteMsg()` では `getProtocolString(rtnl_route_get_protocol(route_obj))` で
Linux rt_protos 名（例: `"bgp"`, `"zebra"`, `"static"`）に変換してセットする。
省略時は routeorch 側で無視（`SAI_INSEG_ENTRY_ATTR_` へのマップなし）。

#### `nexthop` — デフォルト `""` (省略)

```cpp
// sonic-swss fpmsyncd/routesync.h:146
string nexthop = string();

// fpmsyncd/routesync.cpp:2726
fvw.nexthop = std::move(gw_list);
```

`getNextHopList()` がカーネル netlink の nexthop から GW IP リストを構築する。
非 ZMQ パスでは空のとき省略:

```cpp
// fpmsyncd/routesync.cpp:1079-1081
if (nexthop != string()) {
    fvVector.push_back(FieldValueTuple("nexthop", nexthop.c_str()));
}
```

#### `blackhole` — デフォルト `"false"`

`LabelRouteTableFieldValueTupleWrapper` の初期値として `string("false")` が宣言され、
`"false"` に一致する場合は fvVector に追加しない（非 ZMQ パス）:

```cpp
// sonic-swss fpmsyncd/routesync.h:145
string blackhole = string("false");

// fpmsyncd/routesync.cpp:1076-1078
if (blackhole != string("false")) {
    fvVector.push_back(FieldValueTuple("blackhole", blackhole.c_str()));
}
```

`RTN_BLACKHOLE` タイプのルートのみ `fvw.blackhole = "true"` にセットされる
(`routesync.cpp:2693`)。

#### `mpls_pop` — fpmsyncd は常に `"1"` を書く

`onLabelRouteMsg()` は RTN_UNICAST ルートで必ず `mpls_pop = "1"` をセットする:

```cpp
// fpmsyncd/routesync.cpp:2728
fvw.mpls_pop = "1";
```

ただし `LabelRouteTableFieldValueTupleWrapper` の初期値は `string()`（空）なので、
外部から手動で書き込む場合は省略可能（routeorch 側の `pop_count` は uint8_t のゼロ初期化
により 0 = ラベル pop なし）。

#### `mpls_nh` — outgoing ラベルが存在する場合のみ書かれる

```cpp
// fpmsyncd/routesync.cpp:2729-2732
if (!mpls_list.empty())
{
    fvw.mpls_nh = std::move(mpls_list);
}
```

空のときは省略。routeorch 側では `"na"` 要素を IP 転送（MPLS ラベルなし）として扱う:

```cpp
// orchagent/mplsrouteorch.cpp:244
if (!mpls_nhv.empty() && mpls_nhv[i] != "na")
{
    nhg_str += mpls_nhv[i] + LABELSTACK_DELIMITER;
}
```

#### `ifname` — 省略時はルートをスキップ

`ifname` が空かつ非 blackhole の場合、routeorch はルートを無効として消費する:

```cpp
// orchagent/mplsrouteorch.cpp:193-197
if (alsv.size() == 0 && !blackhole)
{
    SWSS_LOG_WARN("Skip the route %s, for it has an empty ifname field.", key.c_str());
    it = consumer.m_toSync.erase(it);
    continue;
}
```
<!-- /defaults -->

## 制約・注意事項

- 非デフォルト VRF の MPLS ルートは現在 fpmsyncd がスキップする（`SWSS_LOG_INFO` のみ）
- `nexthop_group` と `nexthop`/`ifname` の同時指定はエラー (`SWSS_LOG_ERROR`)
- `mpls_pop` は SAI の `SAI_INSEG_ENTRY_ATTR_NUM_OF_POP` に直接マップ。0 の場合はラベル pop なし
- `mpls_nh` の `push<N>` は SAI_OUTSEG_TYPE_PUSH、`swap<N>` は SAI_OUTSEG_TYPE_SWAP として解釈される

## 購読者

- `routeorch::doLabelTask()` (`sonic-swss/orchagent/mplsrouteorch.cpp`): SAI `inseg_entry` の作成・更新・削除

## 書き込み元

- `fpmsyncd::RouteSync::onLabelRouteMsg()` (`sonic-swss/fpmsyncd/routesync.cpp`): カーネル netlink MPLS ルート受信時

<!-- side-effects -->
## 副次 DB 書込

APPL_DB `LABEL_ROUTE_TABLE` の SET / DEL に対して、`routeorch::doLabelTask()`
(`orchagent/mplsrouteorch.cpp`) および `nhgorch` の MPLS NH 経路 (`isLabeled()` 分岐) は
**STATE_DB / COUNTERS_DB / APPL_STATE_DB への副次書き込みを一切行わない**。
副作用は SAI `inseg_entry` および MPLS NH (SAI `next_hop`) オブジェクトの ASIC 反映に閉じる。

| 副次 DB | 書込有無 | 根拠 |
|---|---|---|
| STATE_DB | なし | `mplsrouteorch.cpp` / `nhgorch.cpp` に `m_stateDb` / `STATE_DB` 参照なし。`routeorch.cpp:294` の `m_stateDefaultRouteTb->set()` は IPv4/IPv6 デフォルトルート (`APP_ROUTE_TABLE_NAME`) 経路でのみ呼ばれ、`doTask` (`routeorch.cpp:618`) は `APP_LABEL_ROUTE_TABLE_NAME` のとき `doLabelTask` 呼出後 `return;` するため MPLS 経路には波及しない |
| COUNTERS_DB | なし | `mplsrouteorch.cpp` / `nhgorch.cpp` に `FlexCounter` / `COUNTERS_DB` 参照なし。SAI `inseg_entry` 用カウンタは未統合 |
| APPL_STATE_DB | なし | `routeorch.cpp:3201` の `m_publisher.publish(APP_ROUTE_TABLE_NAME, ...)` は `ROUTE_TABLE` キー固定で、`LABEL_ROUTE_TABLE` に対する APPL_STATE_DB ミラーは存在しない |

詳細な走査ログは `meta/_intermediate/cdb-flow/appl-mpls-route-side.md` を参照。
<!-- /side-effects -->

<!-- platform -->
## プラットフォーム差

`mplsrouteorch.cpp` / `nhgorch.cpp` / `routeorch.cpp` の MPLS 経路を全文走査した結果、
APPL_DB `LABEL_ROUTE_TABLE` の挙動はコミュニティ master 上で **プラットフォーム非依存**である。
差は SAI ベンダ実装側 (INSEG entry サポートの有無、available count の提供) に閉じ、
CONFIG_DB / APPL_DB スキーマ・キー構造には現れない。

| 観点 | 差の有無 | 根拠 |
|---|---|---|
| SAI MPLS capability の runtime 問合せ | なし | `mplsrouteorch.cpp` / `nhgorch.cpp` に `sai_query_attribute_capability` / `sai_object_type_query` 参照 0 件。`SAI_API_MPLS` は `saihelper.cpp:220` で一律 `sai_api_query()` され、ベンダが未サポートなら orchagent 起動段階で失敗する。runtime での MPLS 有効/無効判定パスは存在しない |
| `SAI_SWITCH_ATTR_AVAILABLE_*` による上限取得 | なし | `crmorch.cpp:113` の `CRM_MPLS_INSEG` は `SAI_OBJECT_TYPE_INSEG_ENTRY` (object_type 経由)。IPv4/IPv6 route のような `SAI_SWITCH_ATTR_AVAILABLE_*` 属性は `crmorch.cpp` に存在せず、CRM `used`/`available` の精度はベンダ SAI 実装に依存 |
| switch type (voq/chassis/fabric) 分岐 | なし | `gMySwitchType` 参照は `routeorch.cpp:106-109` の **IP route ECMP sizing 限定**で、`doLabelTask` には伝搬しない。`mplsrouteorch.cpp` / `nhgorch.cpp` に `voq` / `chassis` / `fabric` 参照は 0 件 |
| multi-asic namespace 特殊化 | なし | `mplsrouteorch.cpp` / `nhgorch.cpp` / `fpmsyncd/routesync.cpp::onLabelRouteMsg()` に `namespace` / `asic_id` 参照 0 件。各 asic-namespace は独立 swss コンテナで同一ロジックを実行 |
| VRF 制限 (プラットフォーム非依存) | あり | `fpmsyncd/routesync.cpp:2674-2681` で非デフォルト VRF (`master_index != 0`) は `SWSS_LOG_INFO("Unsupported Non-default VRF")` のみでスキップ。これは fpmsyncd 全体の制約で ASIC タイプとは無関係 |

詳細な走査ログは `meta/_intermediate/cdb-flow/appl-mpls-route-platform.md` を参照。
<!-- /platform -->

<!-- failure -->
## 失敗挙動マトリクス (Phase D)

ソース: `sonic-net/sonic-swss/orchagent/mplsrouteorch.cpp`, `orchagent/nhgorch.cpp`

### SET (`doLabelTask` / `addLabelRoute` / `addLabelRoutePost`) における失敗・retry 経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `nexthop_group` と `nexthop`/`ifname` の同時指定 | `doLabelTask()` L165-171 | エントリを `m_toSync` から **erase** (drop)・retry なし | LOG_ERROR ("Route %s has both nexthop_group and ips/aliases") | `mplsrouteorch.cpp:167-170` |
| `ifname` が空かつ非 blackhole | `doLabelTask()` L193-198 | エントリを **erase** (drop)・retry なし | LOG_WARN ("Skip the route ... empty ifname field.") | `mplsrouteorch.cpp:195-197` |
| `op` が `SET_COMMAND` / `DEL_COMMAND` 以外 | `doLabelTask()` L327-330 | LOG_ERROR | LOG_ERROR ("Unknown operation type %s") | `mplsrouteorch.cpp:329` |
| `nexthop_group` 指定だが NhgOrch に該当 NHG なし (doLabelTask) | `doLabelTask()` L256-267 | LOG_ERROR・`++it` で **retry** | LOG_ERROR ("Next hop group %s does not exist") | `mplsrouteorch.cpp:262-266` |
| `nexthop_group` 指定で NHG が `addLabelRoute` 内で消失 | `addLabelRoute()` L481-490 `catch(out_of_range)` | `return false` → **retry** | LOG_WARN ("Next hop group key %s does not exist") | `mplsrouteorch.cpp:486-490` |
| 単一 NH が intf NH で RIF 未作成 | `addLabelRoute()` L502-510 | `return false` → **retry** | LOG_INFO ("Failed to get next hop %s for %u") | `mplsrouteorch.cpp:505-510` |
| 単一 NH の IP neighbor 未解決 | `addLabelRoute()` L534-540 | `resolveNeighbor()` 発火後 `return false` → **retry** | LOG_INFO ("Failed to get next hop %s for %u") | `mplsrouteorch.cpp:536-540` |
| MPLS NH の `addNextHop()` 失敗 | `addLabelRoute()` L523-531 | `return false` → **retry** | (NeighOrch 側) | `mplsrouteorch.cpp:528-531` |
| ECMP NHG (`getSize() > 1`) で `addNextHopGroup` 失敗 | `addLabelRoute()` L550-583 | 未解決メンバごとに `resolveNeighbor()` 発火・`addTempLabelRoute()` で一時ルート登録・`return false` → **retry** | LOG_INFO ("Failed to get next hop ... resolving neighbor") | `mplsrouteorch.cpp:550-583` |
| `gLabelRouteBulker.create_entry` が `SAI_STATUS_ITEM_ALREADY_EXISTS` | `addLabelRoute()` L628-633 | `return false` → **retry** | LOG_ERROR ("Failed to create label route %u with next hop(s) %s") | `mplsrouteorch.cpp:628-633` |
| Post: `object_statuses` 空 (bulker 前で異常) | `addLabelRoutePost()` L677-681 | `return false` → **retry** | なし | `mplsrouteorch.cpp:677-681` |
| Post: NhgOrch/CbfNhgOrch から NHG が消失 | `addLabelRoutePost()` L687-694 | `return false` → **retry** | LOG_WARN ("Failed to get next hop group with index %s") | `mplsrouteorch.cpp:689-693` |
| Post: 単一 NH が RIF/Neighbor で消失 | `addLabelRoutePost()` L704-724 | `return false` → **retry** | LOG_INFO ("Failed to get next hop %s for label %u") | `mplsrouteorch.cpp:707-723` |
| Post: ECMP NHG が消失 → 一時ルートで再 Post | `addLabelRoutePost()` L727-735 | `addLabelRoutePost(ctx, tmp_next_hop)` 再帰呼出後 `return false` → **retry** | なし | `mplsrouteorch.cpp:729-735` |
| Post: SAI `create_entry` 失敗 (新規) | `addLabelRoutePost()` L742-752 | NHG > 1 のとき `removeNextHopGroup()` で巻き戻し・`return false` → **retry** | LOG_ERROR ("Failed to create label %u with next hop(s) %s") | `mplsrouteorch.cpp:742-752` |
| Post: SAI `set` (PACKET_ACTION/NEXT_HOP_ID/blackhole) 失敗 | `addLabelRoutePost()` L777-840 | `handleSaiSetStatus(SAI_API_MPLS, status)` → `task_success` 以外なら `parseHandleSaiStatusFailure` で **retry / abort** 振り分け | LOG_ERROR ("Failed to set label %u with ...") | `mplsrouteorch.cpp:777-840` |

### DEL (`removeLabelRoute` / `removeLabelRoutePost`) における失敗・retry 経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| VRF に対応する route table が存在しない | `removeLabelRoute()` L859-864 | `return true` → erase (silent success) | LOG_INFO ("Failed to find route table, ...") | `mplsrouteorch.cpp:860-864` |
| 該当 label の inseg エントリが存在しない | `removeLabelRoute()` L872-877 | `return true` → erase (silent success) | LOG_INFO ("Failed to find inseg entry, ...") | `mplsrouteorch.cpp:872-877` |
| Post: `object_statuses` 空 (bulker 前で異常) | `removeLabelRoutePost()` L896-900 | `return false` → **retry** | なし | `mplsrouteorch.cpp:896-900` |
| Post: SAI `remove_entry` 失敗 | `removeLabelRoutePost()` L906-915 | `handleSaiRemoveStatus(SAI_API_MPLS, status)` で **retry / abort** 振り分け | LOG_ERROR ("Failed to remove label:%u") | `mplsrouteorch.cpp:907-915` |

### nhgorch (MPLS NH `isLabeled()` 分岐) における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `isLabeled() && isNeighborResolved` で `gNeighOrch->addNextHop(ctx)` 失敗 | `NextHopGroupMember::createSaiObject()` L563-570 | `nh_id` は `SAI_NULL_OBJECT_ID` のまま返却 → 上位で **retry** | (NeighOrch 側) | `nhgorch.cpp:563-570` |
| MPLS NH 同期時、neighbor 未解決 | `createSaiObject()` else L571-587 | `resolveNeighbor()` 発火・`nh_id = SAI_NULL_OBJECT_ID` → 上位 **retry** | LOG_INFO ("Failed to get next hop %s, resolving neighbor") | `nhgorch.cpp:583-585` |
| NHG 全体の SAI create 失敗 | `NextHopGroup::sync()` L784 付近 | LOG_ERROR・`return false` → **retry** | LOG_ERROR ("Failed to create next hop group %s, rv:%d") | `nhgorch.cpp:782-786` |
| MPLS NH メンバの SAI create 失敗 | `NextHopGroup::sync()` L975 付近 | LOG_ERROR・`return false` → **retry** | LOG_ERROR ("Failed to create next hop group %s's member %s") | `nhgorch.cpp:975` |
| MPLS NH メンバ interface down | `NextHopGroup::sync()` L949 付近 | LOG_WARN・メンバ除外 (NHG は他メンバで継続) | LOG_WARN ("Skip next hop %s ..., interface is down") | `nhgorch.cpp:949` |
| MPLS NH ref_count 0 で destructor | `~NextHopGroupMember()` L677-682 | `removeMplsNextHop()` で NeighOrch から MPLS NH 除去 | なし | `nhgorch.cpp:677-682` |

### 補足

- **retry vs drop**: `doLabelTask` のループは `addLabelRoute` / `removeLabelRoute` が `true` を返したときのみ `m_toSync.erase(it)`。`false` 戻り値は `++it` で次サイクル **retry**。入力バリデーション失敗 (両方指定・ifname 空) のみ即 erase される。
- **bulker による非同期確定**: `addLabelRoute` 正常パスの末尾も `return false` (L664)。これは bulker 登録のみの段階で、確定は `addLabelRoutePost` が `m_syncdLabelRoutes` 反映と `gCrmOrch->incCrmResUsedCounter(CRM_MPLS_INSEG)` 実行で行う。
- **neighbor 解決連動**: retry 経路の多くは `m_neighOrch->resolveNeighbor()` を呼ぶため空回りせず、ARP/NDP 解決後の次サイクルで成功する。
- **一時ルート**: ECMP NHG が一部メンバ未解決で作成不能な場合、`addTempLabelRoute()` で解決済み単独 NH を指す一時 inseg を登録し、全メンバ解決後の retry サイクルで本来の NHG に置換される。
- **`handleSaiSetStatus` / `handleSaiRemoveStatus`** は SAI ステータスから `task_success` / `task_need_retry` / `task_failed` を導出する OrchAgent 共通ハンドラで、MPLS では `SAI_API_MPLS` を渡す。

詳細な走査ログは `meta/_intermediate/cdb-flow/appl-mpls-route-failure.md` を参照。
<!-- /failure -->
