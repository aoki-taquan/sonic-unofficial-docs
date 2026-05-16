# WRED_PROFILE — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-swss/orchagent/qosorch.cpp` — WredMapHandler 実装
- `sonic-swss/orchagent/qosorch.h` — 定数・フィールド名定義

---

## 1. ECN enum 定数 (qosorch.h:55-63 / qosorch.cpp:37-44)

CONFIG_DB `ecn` フィールドの文字列値を SAI `SAI_ECN_MARK_MODE_*` にマッピングする `ecn_map` (qosorch.cpp:36-44)。

| 文字列定数 (qosorch.h) | 値 | SAI マッピング |
|---|---|---|
| `ecn_none = "ecn_none"` | `"ecn_none"` | `SAI_ECN_MARK_MODE_NONE` |
| `ecn_green = "ecn_green"` | `"ecn_green"` | `SAI_ECN_MARK_MODE_GREEN` |
| `ecn_yellow = "ecn_yellow"` | `"ecn_yellow"` | `SAI_ECN_MARK_MODE_YELLOW` |
| `ecn_red = "ecn_red"` | `"ecn_red"` | `SAI_ECN_MARK_MODE_RED` |
| `ecn_green_yellow = "ecn_green_yellow"` | `"ecn_green_yellow"` | `SAI_ECN_MARK_MODE_GREEN_YELLOW` |
| `ecn_green_red = "ecn_green_red"` | `"ecn_green_red"` | `SAI_ECN_MARK_MODE_GREEN_RED` |
| `ecn_yellow_red = "ecn_yellow_red"` | `"ecn_yellow_red"` | `SAI_ECN_MARK_MODE_YELLOW_RED` |
| `ecn_all = "ecn_all"` | `"ecn_all"` | `SAI_ECN_MARK_MODE_ALL` |

不正値: `ecn_map.at(fvValue)` が `std::out_of_range` を throw → エントリ破棄 (qosorch.cpp:741-746)。

---

## 2. フィールド名定数 (qosorch.h:23-42, 55)

| 定数名 | 値 (CONFIG_DB フィールド名) | ソース |
|---|---|---|
| `green_min_threshold_field_name` | `"green_min_threshold"` | qosorch.h:28 |
| `green_max_threshold_field_name` | `"green_max_threshold"` | qosorch.h:27 |
| `yellow_min_threshold_field_name` | `"yellow_min_threshold"` | qosorch.h:26 |
| `yellow_max_threshold_field_name` | `"yellow_max_threshold"` | qosorch.h:25 |
| `red_min_threshold_field_name` | `"red_min_threshold"` | qosorch.h:24 |
| `red_max_threshold_field_name` | `"red_max_threshold"` | qosorch.h:23 |
| `green_drop_probability_field_name` | `"green_drop_probability"` | qosorch.h:31 |
| `yellow_drop_probability_field_name` | `"yellow_drop_probability"` | qosorch.h:30 |
| `red_drop_probability_field_name` | `"red_drop_probability"` | qosorch.h:29 |
| `wred_green_enable_field_name` | `"wred_green_enable"` | qosorch.h:42 |
| `wred_yellow_enable_field_name` | `"wred_yellow_enable"` | qosorch.h:41 |
| `wred_red_enable_field_name` | `"wred_red_enable"` | qosorch.h:40 |
| `wred_profile_field_name` | `"wred_profile"` | qosorch.h:39 |
| `ecn_field_name` | `"ecn"` | qosorch.h:55 |

---

## 3. SAI WRED 属性定数 (qosorch.cpp)

`WredMapHandler::convertFieldValuesToAttributes()` が CONFIG_DB フィールドを以下の SAI 属性 ID に変換する。

| CONFIG_DB フィールド | SAI 属性 ID | ソース |
|---|---|---|
| `green_min_threshold` | `SAI_WRED_ATTR_GREEN_MIN_THRESHOLD` | qosorch.cpp:668-673 |
| `green_max_threshold` | `SAI_WRED_ATTR_GREEN_MAX_THRESHOLD` | qosorch.cpp:656-664 |
| `yellow_min_threshold` | `SAI_WRED_ATTR_YELLOW_MIN_THRESHOLD` | qosorch.cpp:646-654 |
| `yellow_max_threshold` | `SAI_WRED_ATTR_YELLOW_MAX_THRESHOLD` | qosorch.cpp:636-644 |
| `red_min_threshold` | `SAI_WRED_ATTR_RED_MIN_THRESHOLD` | qosorch.cpp:686-694 |
| `red_max_threshold` | `SAI_WRED_ATTR_RED_MAX_THRESHOLD` | qosorch.cpp:676-684 |
| `green_drop_probability` | `SAI_WRED_ATTR_GREEN_DROP_PROBABILITY` | qosorch.cpp:696-700 |
| `yellow_drop_probability` | `SAI_WRED_ATTR_YELLOW_DROP_PROBABILITY` | qosorch.cpp:702-706 |
| `red_drop_probability` | `SAI_WRED_ATTR_RED_DROP_PROBABILITY` | qosorch.cpp:708-712 |
| `wred_green_enable` | `SAI_WRED_ATTR_GREEN_ENABLE` | qosorch.cpp:714-721 |
| `wred_yellow_enable` | `SAI_WRED_ATTR_YELLOW_ENABLE` | qosorch.cpp:723-730 |
| `wred_red_enable` | `SAI_WRED_ATTR_RED_ENABLE` | qosorch.cpp:732-739 |
| `ecn` | `SAI_WRED_ATTR_ECN_MARK_MODE` | qosorch.cpp:741-746 |

---

## 4. デフォルト threshold / probability ハードコード値

### 4-1. drop probability のデフォルト補完 (qosorch.cpp:836-850)

`addQosItem()` 内で、`wred_*_enable=true` かつ対応する `*_drop_probability` フィールドが CONFIG_DB に存在しない場合、SAI 属性リストに以下の値を自動補完する。

| 対象色 | SAI 属性 | ハードコード値 | ソース |
|---|---|---|---|
| Green | `SAI_WRED_ATTR_GREEN_DROP_PROBABILITY` | `100` (%) | qosorch.cpp:839 |
| Yellow | `SAI_WRED_ATTR_YELLOW_DROP_PROBABILITY` | `100` (%) | qosorch.cpp:845 |
| Red | `SAI_WRED_ATTR_RED_DROP_PROBABILITY` | `100` (%) | qosorch.cpp:851 |

YANG `default 100` と同値だが、C++ fallback は SAI API 呼び出し直前の補完であり YANG validation 層とは独立した 2 重安全網となっている。

### 4-2. threshold のデフォルト

`*_min_threshold` / `*_max_threshold` には YANG にも orchagent にも明示的なデフォルト値なし。フィールド省略時は SAI ベンダーデフォルト依存。実用上は `qos_config.j2:AZURE_LOSSLESS` テンプレートが min=1,048,576 bytes (1 MiB) / max=2,097,152 bytes (2 MiB) を設定する。

---

## 5. weight デフォルト (qosorch.cpp:794-796)

CONFIG_DB の `WRED_PROFILE` テーブルに `weight` フィールドは存在しない。`addQosItem()` は WRED オブジェクト作成時に常に `SAI_WRED_ATTR_WEIGHT = 0` を属性リスト先頭に無条件挿入する。

```cpp
attr.id = SAI_WRED_ATTR_WEIGHT;
attr.value.s32 = 0;
attrs.push_back(attr);
```

これは SAI WRED オブジェクト作成に必要な必須属性を満たすための固定値であり、ユーザー設定不可。

---

## 6. WRED enable ビットフラグ定数 (qosorch.cpp:54-56)

| 定数 | 値 | 用途 |
|---|---|---|
| `GREEN_WRED_ENABLED` | `(1U << 0)` = `0x01` | green enable ビット |
| `YELLOW_WRED_ENABLED` | `(1U << 1)` = `0x02` | yellow enable ビット |
| `RED_WRED_ENABLED` | `(1U << 2)` = `0x04` | red enable ビット |

drop_probability 設定済みビットフラグ:

| 定数 | 値 | 用途 |
|---|---|---|
| `GREEN_DROP_PROBABILITY_SET` | `(1U << 0)` = `0x01` | green probability 設定済み |
| `YELLOW_DROP_PROBABILITY_SET` | `(1U << 1)` = `0x02` | yellow probability 設定済み |
| `RED_DROP_PROBABILITY_SET` | `(1U << 2)` = `0x04` | red probability 設定済み |

---

## まとめ

| 定数種別 | 件数 |
|---|---|
| ECN enum 値 | 8 |
| フィールド名定数 | 14 |
| SAI wred_attr マッピング | 13 |
| ハードコードデフォルト (prob=100) | 3 (色別) |
| ハードコードデフォルト (weight=0) | 1 |
| WRED enable ビットフラグ | 6 |
