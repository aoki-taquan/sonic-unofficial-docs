# EXP_TO_FC_MAP — ハードコード定数分析

## ソース

- `sonic-swss/orchagent/qosorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/qosorch.h`
- `sonic-swss/orchagent/cbf/nhgmaporch.cpp`

## 定数一覧

### EXP 値上限

| 定数 | 値 | 箇所 |
|------|----|------|
| `EXP_MAX_VAL` | `7` | `qosorch.cpp:120` — `#define EXP_MAX_VAL 7` |

EXP 値は 0..7 の範囲のみ有効。`convertFieldValuesToAttributes()` L1150-1161 で `value < 0` または `value > EXP_MAX_VAL` を検出し `false` を返す。

### FC 値上限（実行時取得）

| 取得方法 | 箇所 | 備考 |
|----------|------|------|
| `NhgMapOrch::getMaxNumFcs()` — `SAI_SWITCH_ATTR_MAX_NUMBER_OF_FORWARDING_CLASSES` を SAI 問い合わせ | `nhgmaporch.cpp:299-325` | 初回呼び出しで取得後キャッシュ (`static int max_num_fcs = -1`) |
| スイッチ FC 未サポート時 | `nhgmaporch.cpp:319` | `max_num_fcs = 0` → 全 FC 値が reject |
| テスト環境 | `test_qos_map.py:314` | `max_num_fcs = 63` で確認済み |

### SAI 属性定数

| 定数 | 値 | 箇所 |
|------|----|------|
| `SAI_QOS_MAP_ATTR_TYPE` | `SAI_QOS_MAP_TYPE_MPLS_EXP_TO_FORWARDING_CLASS` | `addQosItem()` L1189-1213 にハードコード |
| `SAI_QOS_MAP_ATTR_MAP_TO_VALUE_LIST` | — | `convertFieldValuesToAttributes()` L1140 |
| `SAI_PORT_ATTR_QOS_MPLS_EXP_TO_FORWARDING_CLASS_MAP` | — | PORT_QOS_MAP バインド時。`qosorch.cpp:72` |

### フィールド名定数 (qosorch.h)

| 定数 | 値 | 説明 |
|------|----|------|
| `exp_to_fc_field_name` | `"exp_to_fc_map"` | PORT_QOS_MAP フィールド名（`qosorch.h:33`） |

### テーブル名定数

| 定数 | 値（推定） | 説明 |
|------|----|------|
| `CFG_EXP_TO_FC_MAP_TABLE_NAME` | `"EXP_TO_FC_MAP"` | CONFIG_DB テーブル名。`qosorch.cpp:93,112,1338` |

### YANG パターン制約（参考）

| フィールド | YANG パターン | 実装上限 |
|-----------|--------------|---------|
| `exp` (key) | `"[0-7]?"` | `EXP_MAX_VAL=7`（実装一致） |
| `fc` (value) | `"[0-7]?"` | `max_num_fcs-1`（SAI 依存、YANG より広い場合あり） |

> **Evidence**: `qosorch.cpp:120` (`EXP_MAX_VAL`); `qosorch.cpp:1132-1187` (`convertFieldValuesToAttributes`); `qosorch.cpp:1189-1213` (`addQosItem`); `qosorch.h:33` (`exp_to_fc_field_name`); `nhgmaporch.cpp:299-325` (`getMaxNumFcs`)
