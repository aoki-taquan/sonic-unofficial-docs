# WRED_PROFILE — Phase A: コード由来の暗黙デフォルト

対象: `docs/reference/config-db/wred-profile.md`

## 調査対象ファイル (entry grep 1回)

```
grep -rln "WRED_PROFILE" .cache/sonic-sources/
```

主要ソース:
- `sonic-swss/orchagent/qosorch.cpp` (WredMapHandler)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-wred-profile.yang`
- `sonic-buildimage/files/build_templates/qos_config.j2`

---

## Per-field 暗黙デフォルト一覧

### 1. `ecn`

| 層 | 機構 | デフォルト値 | ソース |
|---|---|---|---|
| YANG `default` | フィールド省略時 | `ecn_none` | `sonic-wred-profile.yang:128` |
| qos_config.j2 (AZURE_LOSSLESS) | テンプレート生成 | `"ecn_all"` | `qos_config.j2:489-506` |

**備考**: YANG default は `ecn_none`。ただし自動生成される `AZURE_LOSSLESS` プロファイルでは `ecn_all` が明示設定される。

---

### 2. `wred_green_enable` / `wred_yellow_enable` / `wred_red_enable`

| 層 | 機構 | デフォルト値 | ソース |
|---|---|---|---|
| YANG `default` | フィールド省略時 | `false` | `sonic-wred-profile.yang:134,140,146` |
| qos_config.j2 (AZURE_LOSSLESS) | テンプレート生成 | `"true"` (全3色) | `qos_config.j2:489-506` |

**備考**: YANG default は `false`（WRED 無効）。AZURE_LOSSLESS では `"true"` を明示設定。

---

### 3. `green_drop_probability` / `yellow_drop_probability` / `red_drop_probability`

| 層 | 機構 | デフォルト値 | ソース |
|---|---|---|---|
| YANG `default` | フィールド省略時 | `100` (%) | `sonic-wred-profile.yang:155,164,173` |
| C++ runtime fallback | `addQosItem()`: `wred_*_enable=true` かつ `*_drop_probability` フィールドが CONFIG_DB に存在しない | `100` (SAI_WRED_ATTR_*_DROP_PROBABILITY = 100) | `qosorch.cpp:836-850` |
| qos_config.j2 (AZURE_LOSSLESS) | テンプレート生成 | `"5"` (%) | `qos_config.j2:489-506` |

**C++ fallback 詳細**:
```cpp
// qosorch.cpp:836-840
if (!(drop_prob_set & GREEN_DROP_PROBABILITY_SET) && (wred_enable_set & GREEN_WRED_ENABLED))
{
    attr.id = SAI_WRED_ATTR_GREEN_DROP_PROBABILITY;
    attr.value.s32 = 100;  // 暗黙補完
    attrs.push_back(attr);
}
// 同様に yellow:842-845, red:847-850
```

YANG default と C++ fallback が一致 (100%)。AZURE_LOSSLESS は例外的に 5%。

---

### 4. `green_min_threshold` / `yellow_min_threshold` / `red_min_threshold`

| 層 | 機構 | デフォルト値 | ソース |
|---|---|---|---|
| YANG | `default` 宣言なし | なし（省略可能、uint64） | `sonic-wred-profile.yang:47-61` |
| C++ | フィールドが省略された場合のフォールバックなし。SAI に送らない | — | `qosorch.cpp:666-695` |
| qos_config.j2 (AZURE_LOSSLESS) | テンプレート生成 | `"1048576"` (1 MiB) | `qos_config.j2:489-506` |

**備考**: YANG default なし。省略時は SAI に対応属性が渡されない（SAI ベンダーデフォルトに依存）。AZURE_LOSSLESS でのみ 1 MiB が設定される。

---

### 5. `green_max_threshold` / `yellow_max_threshold` / `red_max_threshold`

| 層 | 機構 | デフォルト値 | ソース |
|---|---|---|---|
| YANG | `default` 宣言なし（`must` 制約のみ）| なし | `sonic-wred-profile.yang:64-89` |
| C++ | フィールドが省略された場合のフォールバックなし | — | `qosorch.cpp:636-685` |
| qos_config.j2 (AZURE_LOSSLESS) | テンプレート生成 | `"2097152"` (2 MiB) | `qos_config.j2:489-506` |

**備考**: YANG default なし。省略時は SAI に対応属性が渡されない。

---

### 6. `SAI_WRED_ATTR_WEIGHT` (暗黙追加、CONFIG_DB フィールドなし)

| 層 | 機構 | デフォルト値 | ソース |
|---|---|---|---|
| C++ 無条件追加 | `addQosItem()` の先頭で常に付与 | `0` | `qosorch.cpp:794-796` |

```cpp
// qosorch.cpp:794-796
attr.id = SAI_WRED_ATTR_WEIGHT;
attr.value.s32 = 0;
attrs.push_back(attr);
```

**備考**: CONFIG_DB に対応フィールドなし。orchagent が SAI 作成時に常に `WEIGHT=0` を先頭 attribute として挿入する。

---

## サマリー表

| フィールド | YANG default | C++ fallback | qos_config.j2 AZURE_LOSSLESS |
|---|---|---|---|
| `ecn` | `ecn_none` | なし | `ecn_all` |
| `wred_*_enable` | `false` | なし | `true` |
| `*_drop_probability` | `100` (%) | `100` (`wred_enable=true` かつ省略時) | `5` (%) |
| `*_min_threshold` | なし | なし | `1048576` bytes (1 MiB) |
| `*_max_threshold` | なし | なし | `2097152` bytes (2 MiB) |
| `SAI_WRED_ATTR_WEIGHT` | — (no CONFIG_DB field) | 常に `0` を注入 | — |

---

## スキャン証跡

- `convertFieldValuesToAttributes()` L585-762 全行読了
- `addQosItem()` L784-860 全行読了
- `sonic-wred-profile.yang` L1-179 全行読了
- entry grep 1回実施済み
- 追加 grep なし
