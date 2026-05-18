# nhg-orch — Platform / SAI Capability 差異 (Phase H) 調査メモ

## 調査対象ファイル

- `sonic-swss/orchagent/nhgorch.cpp` (4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/cbf/cbfnhgorch.cpp` (同上)
- `sonic-swss/orchagent/cbf/nhgmaporch.cpp` (同上)
- `sonic-swss/orchagent/routeorch.cpp` (同上 — getMaxNhgCount を提供)

## 1. ECMP グループ上限: Mellanox プラットフォームのみ補正

`RouteOrch::RouteOrch()` (routeorch.cpp:61-89) で `SAI_SWITCH_ATTR_NUMBER_OF_ECMP_GROUPS` を取得後、
`getenv("platform")` に `MLNX_PLATFORM_SUBSTRING == "mellanox"` が含まれる場合のみ
`m_maxNextHopGroupCount /= DEFAULT_MAX_ECMP_GROUP_SIZE(32)` で補正する。

NhgOrch と CbfNhgOrch はこの `gRouteOrch->getMaxNhgCount()` を参照して上限判定する:
- nhgorch.cpp:252 — 通常 NHG 作成
- nhgorch.cpp:320 — NHG プロモーション判断
- cbfnhgorch.cpp:100 — CBF NHG 作成

Mellanox 以外 (Broadcom / Marvell / VS / VPP / Cisco silicon-one 等) は SAI 戻り値をそのまま採用。

## 2. CBF / FC: SAI_SWITCH_ATTR_MAX_NUMBER_OF_FORWARDING_CLASSES

`NhgMapOrch::getMaxNumFcs()` (nhgmaporch.cpp:299-325) が初回呼出し時に
`SAI_SWITCH_ATTR_MAX_NUMBER_OF_FORWARDING_CLASSES` を取得。非対応 ASIC は 0 を返す。

`CbfNhg::sync()` (cbfnhgorch.cpp:311) で `m_members.size() > getMaxNumFcs()` の場合
SWSS_LOG_WARN のみで処理は継続する。

## 3. NHG Map 数の上限: sai_object_type_get_availability

`NhgMapOrch::NhgMapOrch()` コンストラクタ (nhgmaporch.cpp:26-34) で
`sai_object_type_get_availability(SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MAP)` を呼び出す。
非対応 ASIC は SAI_STATUS_SUCCESS を返さず `m_max_nhg_map_count = 0` のまま。
以降 `FC_TO_NHG_INDEX_MAP_TABLE` の全 SET が `SWSS_LOG_WARN` + `success=false` になる。

## 4. SRv6 NHG: temp NHG 非対応

nhgorch.cpp:256-261 で NHG 上限到達時、`nhg_key.is_srv6_nexthop()` が真の場合は
temp NHG を作成せず `++it; continue` でスキップする (普通 ECMP と異なる挙動)。
SRv6 サポートの有無は ASIC ベンダー実装依存。VS プラットフォームはスタブ実装。

## 5. VS / multi-asic

VS プラットフォームでは SAI シムが ECMP / CBF / NHG Map の create を SUCCESS で返すが
実 ASIC 転送はない。CRM 統計もダミー値。
multi-asic (namespace 別 orchagent) では NhgOrch は名前空間ごとに独立して起動し、
NHG インデックスの名前空間は交わらない。
