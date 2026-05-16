# nhg-orch Phase A — orchagent フィールドデフォルト調査

調査日: 2026-05-14
対象ファイル:
- sonic-swss/orchagent/nhgorch.cpp (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- sonic-swss/orchagent/nhgorch.h
- sonic-swss/orchagent/cbf/cbfnhgorch.cpp
- sonic-swss/orchagent/cbf/cbfnhgorch.h
- sonic-swss/orchagent/cbf/nhgmaporch.cpp
- sonic-swss/orchagent/cbf/nhgmaporch.h
- sonic-swss/orchagent/nhgbase.h

## 対象テーブル

NhgOrch は APPL_DB の以下 3 テーブルを購読する（CONFIG_DB 直接購読なし）:

| orch クラス | APPL_DB テーブル | スキーマ定数 |
|------------|----------------|------------|
| `NhgOrch` | `NEXTHOP_GROUP_TABLE` | `APP_NEXTHOP_GROUP_TABLE_NAME` |
| `CbfNhgOrch` | `CLASS_BASED_NEXT_HOP_GROUP_TABLE` | `APP_CLASS_BASED_NEXT_HOP_GROUP_TABLE_NAME` |
| `NhgMapOrch` | `FC_TO_NHG_INDEX_MAP_TABLE` | `APP_FC_TO_NHG_INDEX_MAP_TABLE_NAME` |

## NEXTHOP_GROUP_TABLE フィールド (NhgOrch)

`NhgOrch::doTask()` (nhgorch.cpp:37) が解析するフィールド:

| フィールド | 型 | デフォルト | コード根拠 |
|----------|----|-----------|---------| 
| `nexthop` | カンマ区切り IP アドレス文字列 | `""` (空文字列) | nhgorch.cpp:73-74: `if (fvField(i) == "nexthop" && fvValue(i) != "") ips = fvValue(i);` |
| `ifname` | カンマ区切りインタフェース名文字列 | `""` (空文字列) | nhgorch.cpp:76-77: `if (fvField(i) == "ifname" && fvValue(i) != "") aliases = fvValue(i);` |
| `weight` | カンマ区切り整数文字列 | `""` (空文字列) | nhgorch.cpp:79-80: `if (fvField(i) == "weight" && fvValue(i) != "") weights = fvValue(i);` |
| `mpls_nh` | カンマ区切り MPLS ラベルスタック文字列 | `""` (空文字列) | nhgorch.cpp:82-83: `if (fvField(i) == "mpls_nh" && fvValue(i) != "") mpls_nhs = fvValue(i);` |
| `seg_src` | カンマ区切り SRv6 ソースアドレス文字列 | `""` (空文字列) | nhgorch.cpp:85-89: `if (fvField(i) == "seg_src" && fvValue(i) != "") { srv6_source = fvValue(i); srv6_nh = true; }` |
| `nexthop_group` | NHG_DELIMITER 区切り NHG インデックス文字列 | `""` (空文字列) | nhgorch.cpp:91-95: `if (fvField(i) == "nexthop_group" && fvValue(i) != "") { nhgs = fvValue(i); is_recursive = true; }` |

### 内部変数デフォルト

- `is_recursive`: `false` (nhgorch.cpp:65)
- `overlay_nh`: `false` (nhgorch.cpp:67)
- `srv6_nh`: `false` (nhgorch.cpp:68)

### weight の SAI マッピング

`createNhgmAttrs()` (nhgorch.cpp:1095) では `weight == 0` 時は SAI 属性に追加しない:
```cpp
auto weight = nhgm.getWeight();
if (weight != 0) {
    nhgm_attr.id = SAI_NEXT_HOP_GROUP_MEMBER_ATTR_WEIGHT;
    nhgm_attr.value.s32 = weight;
    nhg_attrs.push_back(nhgm_attr);
}
```
つまり `weight` フィールド省略時 (= `""`) → key.weight は 0 → SAI_NEXT_HOP_GROUP_MEMBER_ATTR_WEIGHT は設定されず ECMP 均等分散となる。

### SAI タイプ

- 通常 NHG (2 メンバー以上): `SAI_NEXT_HOP_GROUP_TYPE_ECMP` (nhgorch.cpp:772)
- 1 メンバー非 recursive NHG: グループ作成なし、neighbor の SAI NH ID を直接使用 (nhgorch.cpp:741-760)

### Temp NHG

- `gRouteOrch->getNhgCount() + NextHopGroup::getSyncedCount() >= gRouteOrch->getMaxNhgCount()` が真の場合、仮グループを作成 (nhgorch.cpp:252)
- 仮グループはランダムに 1 メンバーを選択して代表させる (nhgorch.cpp:853-854)
- SRv6 NHG は仮グループ非対応 (nhgorch.cpp:257)

## CLASS_BASED_NEXT_HOP_GROUP_TABLE フィールド (CbfNhgOrch)

`CbfNhgOrch::doTask()` (cbfnhgorch.cpp:38) が解析するフィールド:

| フィールド | 型 | デフォルト | コード根拠 |
|----------|----|-----------|---------| 
| `members` | カンマ区切り NHG インデックス文字列 | `""` (空文字列、検証失敗→エントリ破棄) | cbfnhgorch.cpp:69: `if (fvField(i) == "members") members = fvValue(i);` |
| `selection_map` | NHG_MAP インデックス文字列 | `""` (空文字列) | cbfnhgorch.cpp:72: `else if (fvField(i) == "selection_map") selection_map = fvValue(i);` |

### CBF NHG 検証ロジック

- `members` が空 → `SWSS_LOG_ERROR` + エントリ破棄 (cbfnhgorch.cpp:225-226)
- `members` に重複あり → `SWSS_LOG_ERROR` + エントリ破棄 (cbfnhgorch.cpp:231-233)
- メンバー数 > `getMaxNumFcs()` → `SWSS_LOG_WARN` (cbfnhgorch.cpp:313-315)
- `selection_map` に対応する NHG マップが存在しない → `SWSS_LOG_ERROR` + `return false` (cbfnhgorch.cpp:320-324)
- NHG マップが参照するインデックス >= メンバー数 → `SWSS_LOG_ERROR` + `return false` (cbfnhgorch.cpp:326-330)

### CBF NHG SAI タイプ

- `SAI_NEXT_HOP_GROUP_TYPE_CLASS_BASED` (cbfnhgorch.cpp:302)
- メンバー数: `SAI_NEXT_HOP_GROUP_ATTR_CONFIGURED_SIZE` (cbfnhgorch.cpp:306)
- 選択マップ: `SAI_NEXT_HOP_GROUP_ATTR_SELECTION_MAP` (cbfnhgorch.cpp:318)
- メンバーの INDEX は 0 ベース順序 (cbfnhgorch.cpp:258: `idx++`)

## FC_TO_NHG_INDEX_MAP_TABLE フィールド (NhgMapOrch)

`NhgMapOrch::doTask()` および `getMap()` が処理するフィールド:

| フィールド | 型 | デフォルト | コード根拠 |
|----------|----|-----------|---------| 
| `<FC値>` (フィールド名) | 整数 [0, max_num_fcs) | — (必須、空は error) | nhgmaporch.cpp:340-365 |
| `<NH_index値>` (フィールド値) | 非負整数 | — (必須) | nhgmaporch.cpp:370-375 |

### NHG マップ検証ロジック

- マップが空 → `SWSS_LOG_ERROR` + `success=false` (nhgmaporch.cpp:340)
- FC 値が負または >= max_num_fcs → `SWSS_LOG_ERROR` + 破棄 (nhgmaporch.cpp:359-364)
- NH index が負 → `SWSS_LOG_ERROR` + 破棄 (nhgmaporch.cpp:371-374)
- スイッチが NHG マップ非対応 → `m_max_nhg_map_count = 0` + `SWSS_LOG_WARN` (nhgmaporch.cpp:32-34)

### SAI タイプ

- `SAI_NEXT_HOP_GROUP_MAP_ATTR_TYPE`: `SAI_NEXT_HOP_GROUP_MAP_TYPE_FORWARDING_CLASS_TO_INDEX` (nhgmaporch.cpp:118-119)

## ハードコードデフォルトまとめ

| 項目 | 値 | 根拠ファイル |
|-----|----|------------|
| weight 省略時の SAI 動作 | SAI 属性なし (均等 ECMP) | nhgorch.cpp:1113-1118 |
| is_recursive デフォルト | `false` | nhgorch.cpp:65 |
| NHG SAI グループ型 | `SAI_NEXT_HOP_GROUP_TYPE_ECMP` | nhgorch.cpp:772 |
| CBF NHG SAI グループ型 | `SAI_NEXT_HOP_GROUP_TYPE_CLASS_BASED` | cbfnhgorch.cpp:302 |
| CBF member INDEX | 0 ベース (投入順) | cbfnhgorch.cpp:258 |
| NHG マップ型 | `SAI_NEXT_HOP_GROUP_MAP_TYPE_FORWARDING_CLASS_TO_INDEX` | nhgmaporch.cpp:118 |
