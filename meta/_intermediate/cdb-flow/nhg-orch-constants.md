# nhg-orch Phase E — ハードコード定数調査ノート

## 調査対象ファイル

- `sonic-swss/orchagent/nhgorch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/nhgorch.h`
- `sonic-swss/orchagent/cbf/cbfnhgorch.cpp`
- `sonic-swss/orchagent/cbf/nhgmaporch.cpp`
- `sonic-swss/orchagent/nexthopkey.h`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/orchagent/routeorch.cpp`

## 発見した定数

### バルクサイズ上限

```
orchdaemon.cpp:81:  #define DEFAULT_MAX_BULK_SIZE 1000
orchdaemon.cpp:82:  size_t gMaxBulkSize = DEFAULT_MAX_BULK_SIZE;
```

`NhgOrch::syncMembers()` および `CbfNhgOrch::syncMembers()` は `ObjectBulker<sai_next_hop_group_api_t>` を生成する際に `gMaxBulkSize` を渡す。デフォルト値は `1000`（CLI オプション `-k` で上書き可能）。

### ECMP グループ数上限（RouteOrch 共有）

```
routeorch.cpp:37:  #define DEFAULT_NUMBER_OF_ECMP_GROUPS   128
routeorch.cpp:38:  #define DEFAULT_MAX_ECMP_GROUP_SIZE      32
```

NhgOrch / CbfNhgOrch は `gRouteOrch->getMaxNhgCount()` を介してこの上限を参照する。

### 内部キー区切り文字

```
nexthopkey.h:17:  #define LABELSTACK_DELIMITER '+'
nexthopkey.h:18:  #define NH_DELIMITER         '@'
nexthopkey.h:19:  #define NHG_DELIMITER        ','
```

### FC_TO_NHG_INDEX_MAP_TABLE — ランタイム取得上限

```
nhgmaporch.cpp:10:  uint64_t NhgMapOrch::m_max_nhg_map_count = 0;
nhgmaporch.cpp:30:  sai_object_type_get_availability(..., &m_max_nhg_map_count)
nhgmaporch.cpp:33:  m_max_nhg_map_count = 0;  // 非対応プラットフォームのフォールバック
```

起動時に `SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MAP` の利用可能数を SAI に問い合わせる。問い合わせ失敗時は `0`（上限なしとして扱われるが実質登録不可）。

### FC 値有効範囲

```
nhgmaporch.cpp:303:  static int max_num_fcs = -1;  // 初期値（未取得）
nhgmaporch.cpp:315:  max_num_fcs = attr.value.u8;   // SAI から取得
nhgmaporch.cpp:320:  max_num_fcs = 0;               // 取得失敗フォールバック
```

`getMaxNumFcs()` は `SAI_SWITCH_ATTR_MAX_NUMBER_OF_FORWARDING_CLASSES` を SAI に問い合わせる。有効な FC 値は `[0, max_num_fcs)` 範囲のみ。取得失敗時は `0` となり、すべての FC 値が拒否される。

### SAI グループ型 (固定値)

| オーケストレータ | SAI 属性 | 固定値 | ソース |
|---|---|---|---|
| `NhgOrch` (通常 NHG) | `SAI_NEXT_HOP_GROUP_ATTR_TYPE` | `SAI_NEXT_HOP_GROUP_TYPE_ECMP` | `nhgorch.cpp:772` |
| `CbfNhgOrch` | `SAI_NEXT_HOP_GROUP_ATTR_TYPE` | `SAI_NEXT_HOP_GROUP_TYPE_CLASS_BASED` | `cbfnhgorch.cpp:302` |
| `NhgMapOrch` | `SAI_NEXT_HOP_GROUP_MAP_ATTR_TYPE` | `SAI_NEXT_HOP_GROUP_MAP_TYPE_FORWARDING_CLASS_TO_INDEX` | `nhgmaporch.cpp:119` |

## 結論

`nhg-orch.md` は既存 Phase E が `nhg.md` 側に ECMP グループ数定数・区切り文字をカバーしている。本ページ（APPL_DB オーケストレータ側）では `NhgOrch` / `CbfNhgOrch` / `NhgMapOrch` 固有の定数（バルクサイズ、マップ数上限、FC 値範囲、SAI グループ型固定値）を Phase E として記述する。
