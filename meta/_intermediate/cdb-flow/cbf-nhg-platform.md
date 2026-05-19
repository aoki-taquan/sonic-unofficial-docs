# cbf-nhg Phase H — プラットフォーム / SAI Capability 差異調査

調査日: 2026-05-19
対象ファイル:
- sonic-swss/orchagent/cbf/cbfnhgorch.cpp
- sonic-swss/orchagent/cbf/nhgmaporch.cpp
- sonic-swss/orchagent/routeorch.cpp

## SAI_NEXT_HOP_GROUP_TYPE_CLASS_BASED サポート

CBF NHG は `SAI_NEXT_HOP_GROUP_TYPE_CLASS_BASED` を SAI に渡す (`cbfnhgorch.cpp:302`)。
このグループ型の対応はプラットフォーム依存であり、ASIC ベンダー (Broadcom / Marvell / Mellanox / VS 等) ごとに異なる。
VS プラットフォームはスタブ実装で SAI_STATUS_SUCCESS を返すが実転送はない。

## NHG 数上限: RouteOrch から取得

`gRouteOrch->getNhgCount() + NhgBase::getSyncedCount() >= gRouteOrch->getMaxNhgCount()` (`cbfnhgorch.cpp:100`)。
上限は Mellanox のみ `routeorch.cpp:83-87` で `SAI_SWITCH_ATTR_NUMBER_OF_ECMP_GROUPS / DEFAULT_MAX_ECMP_GROUP_SIZE(=32)` で補正される。
CBF NHG も通常 NHG と同じ上限カウンタを共有する。

## フォワーディングクラス数上限: SAI_SWITCH_ATTR_MAX_NUMBER_OF_FORWARDING_CLASSES

`NhgMapOrch::getMaxNumFcs()` (`nhgmaporch.cpp:299-325`) が初回呼出し時に SAI から取得。
- SAI 対応 ASIC: `attr.value.u8`（ASIC 依存）
- SAI 非対応 ASIC: `max_num_fcs = 0` → 全 FC 値が範囲外エラー

`CbfNhg::sync()` (`cbfnhgorch.cpp:311-312`) はメンバー数 > `getMaxNumFcs()` で SWSS_LOG_WARN を出すが処理継続。

## NHG Map 収容数: sai_object_type_get_availability

`NhgMapOrch` コンストラクタ (`nhgmaporch.cpp:26-34`) で `SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MAP` の availability を取得。
非対応 ASIC は `m_max_nhg_map_count = 0` → 以降の FC_TO_NHG_INDEX_MAP_TABLE SET が全件ブロック → CBF NHG の `selection_map` 解決が永続的に失敗する。

## SAI_NEXT_HOP_GROUP_MEMBER_ATTR_INDEX の CREATE_ONLY 制約

`SAI_NEXT_HOP_GROUP_MEMBER_ATTR_INDEX` は CREATE_ONLY 属性のため、メンバー順序変更時は全 member remove → 再 sync が必要 (`cbfnhgorch.cpp:509-516`)。これはプラットフォーム共通制約。
