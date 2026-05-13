# WRED_PROFILE enum 値別深掘り grep 証跡 (v2)

生成日: 2026-05-13
対象ファイル: sonic-swss/orchagent/qosorch.cpp
          sonic-buildimage/src/sonic-yang-models/yang-models/sonic-wred-profile.yang
          sonic-mgmt-common/cvl/testdata/schema/sonic-wred-profile.yang

---

## フィールド: ecn (8 値)

YANG 定義: sonic-wred-profile.yang — 8 値、default `ecn_none`
実装 map: `qosorch.cpp:36-44` `ecn_map` — 8 エントリ
SAI attr: `SAI_WRED_ATTR_ECN_MARK_MODE` (`qosorch.cpp:743`)
エラー: `ecn_map.at(fvValue(*i))` — 不正値は `std::out_of_range` 例外 → entry 破棄

### ecn_none
- grep hit: `qosorch.cpp:37` `{"ecn_none", SAI_ECN_MARK_MODE_NONE}`
- grep hit: `sonic-wred-profile.yang:95` enum ecn_none, description "Disable ECN marking for all colors."
- grep hit: YANG default `ecn_none` (`sonic-wred-profile.yang:128`)
- SAI: `SAI_ECN_MARK_MODE_NONE`
- 挙動: 全カラー ECN マーキング無効。`ecn` フィールド省略時のデフォルト値

### ecn_green
- grep hit: `qosorch.cpp:38` `{"ecn_green", SAI_ECN_MARK_MODE_GREEN}`
- grep hit: YANG `enum ecn_green` — "Enable ECN marking for green color. Yellow and red are disabled."
- SAI: `SAI_ECN_MARK_MODE_GREEN`
- 挙動: Green カラーのみ ECN マーキング有効。Yellow/Red は WRED drop のみ

### ecn_yellow
- grep hit: `qosorch.cpp:39` `{"ecn_yellow", SAI_ECN_MARK_MODE_YELLOW}`
- grep hit: YANG `enum ecn_yellow` — "Enable ECN marking for yellow color. Green and red are disabled."
- SAI: `SAI_ECN_MARK_MODE_YELLOW`
- 挙動: Yellow カラーのみ ECN マーキング有効

### ecn_red
- grep hit: `qosorch.cpp:40` `{"ecn_red",SAI_ECN_MARK_MODE_RED}`
- grep hit: YANG `enum ecn_red` — "Enable ECN marking for red color. Green and red are disabled."
- SAI: `SAI_ECN_MARK_MODE_RED`
- 挙動: Red カラーのみ ECN マーキング有効

### ecn_green_yellow
- grep hit: `qosorch.cpp:41` `{"ecn_green_yellow", SAI_ECN_MARK_MODE_GREEN_YELLOW}`
- grep hit: YANG `enum ecn_green_yellow` — "Enable ECN marking for green and yellow colors. Red is disabled."
- SAI: `SAI_ECN_MARK_MODE_GREEN_YELLOW`
- 挙動: Green + Yellow カラーで ECN マーキング有効、Red は WRED drop のみ

### ecn_green_red
- grep hit: `qosorch.cpp:42` `{"ecn_green_red", SAI_ECN_MARK_MODE_GREEN_RED}`
- grep hit: YANG `enum ecn_green_red` — "Enable ECN marking for green and red colors. Yellow is disabled."
- SAI: `SAI_ECN_MARK_MODE_GREEN_RED`
- 挙動: Green + Red カラーで ECN マーキング有効、Yellow は WRED drop のみ

### ecn_yellow_red
- grep hit: `qosorch.cpp:43` `{"ecn_yellow_red", SAI_ECN_MARK_MODE_YELLOW_RED}`
- grep hit: YANG `enum ecn_yellow_red` — "Enable ECN marking for yellow and red colors. Green is disabled."
- SAI: `SAI_ECN_MARK_MODE_YELLOW_RED`
- 挙動: Yellow + Red カラーで ECN マーキング有効、Green は WRED drop のみ

### ecn_all
- grep hit: `qosorch.cpp:44` `{"ecn_all", SAI_ECN_MARK_MODE_ALL}`
- grep hit: YANG `enum ecn_all` — "Enable ECN marking for all colors."
- 挙動: Green + Yellow + Red 全カラーで ECN マーキング有効。典型的なロスレストラフィック設定

---

## 複合条件

1. **ecn_none + wred_*_enable=true**: WRED drop は発生するが ECN マーキングはしない。通常のランダムドロップ動作。
2. **ecn_all + wred_*_enable=false**: ECN マーキングモード設定はされるが WRED が無効なので閾値に達しない。実質 ECN 無効と同じ。
3. **ecn_green + wred_yellow_enable=true**: Yellow パケットは drop されるが ECN マーキングなし。Green のみ ECN 通知。
4. **threshold 2 フェーズ適用**: `qosorch.cpp` WredMapHandler — 「現在 min > 新 max」または「現在 max < 新 min」になる変更は deferred リストに退避してから後適用。SAI 順序エラー回避のため ECN 変更と閾値変更が絡む場合に影響あり。

---

## 値別 grep カバレッジサマリ

| フィールド | 値 | hit数 | 主要証跡 |
|---|---|---|---|
| ecn | ecn_none | 3 | qosorch.cpp:37, yang:95, yang(default):128 |
| ecn | ecn_green | 2 | qosorch.cpp:38, yang |
| ecn | ecn_yellow | 2 | qosorch.cpp:39, yang |
| ecn | ecn_red | 2 | qosorch.cpp:40, yang |
| ecn | ecn_green_yellow | 2 | qosorch.cpp:41, yang |
| ecn | ecn_green_red | 2 | qosorch.cpp:42, yang |
| ecn | ecn_yellow_red | 2 | qosorch.cpp:43, yang |
| ecn | ecn_all | 2 | qosorch.cpp:44, yang:123 |

全 8 値 hit。0 hit なし。

## 複合条件発見数: 4
