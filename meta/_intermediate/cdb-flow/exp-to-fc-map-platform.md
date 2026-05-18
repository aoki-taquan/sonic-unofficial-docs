# exp-to-fc-map — Phase H: プラットフォーム差異調査

## 調査対象

`EXP_TO_FC_MAP` テーブル。Consumer: `QosOrch::handleExpToFcTable()` / `ExpToFcMapHandler` / `NhgMapOrch::getMaxNumFcs()`.

## 主要な証跡

- `sonic-swss/orchagent/qosorch.cpp:1132-1213` — `ExpToFcMapHandler` の `convertFieldValuesToAttributes()` / `addQosItem()`
- `sonic-swss/orchagent/cbf/nhgmaporch.cpp:299-325` — `NhgMapOrch::getMaxNumFcs()` + `SAI_SWITCH_ATTR_MAX_NUMBER_OF_FORWARDING_CLASSES`
- `sonic-buildimage/files/build_templates/cbf_config.j2` — AZURE デフォルトマップ（EXP 0..7 → FC 0..7）
- `sonic-swss/tests/test_qos_map.py:314` — テスト環境 `max_num_fcs = 63`

## プラットフォーム依存ポイント

### 1. FC 上限 (`SAI_SWITCH_ATTR_MAX_NUMBER_OF_FORWARDING_CLASSES`)

`NhgMapOrch::getMaxNumFcs()` が orchagent 起動後の初回 EXP_TO_FC_MAP エントリ処理時に SAI スイッチ属性を問い合わせる（静的変数キャッシュ）。

| プラットフォーム状況 | `max_num_fcs` | 影響 |
|---|---|---|
| MPLS EXP→FC 非サポート | `0`（SAI error 時の fallback） | 全 FC 値が invalid → 全エントリが `task_invalid_entry` で reject |
| CBF サポート ASIC（テスト参考値） | `63`（`test_qos_map.py:314`） | FC 0..62 が有効 |
| YANG 定義上限 | `7`（`pattern "[0-7]?"`) | YANG は実装より保守的。ASIC が 63 まで許容しても YANG で書けるのは 0..7 のみ |

### 2. MPLS サポート自体のプラットフォーム差

`EXP_TO_FC_MAP` は MPLS EXP ビットを FC に変換する CBF 専用テーブル。MPLS EXP 分類は `SAI_QOS_MAP_TYPE_MPLS_EXP_TO_FORWARDING_CLASS` で表現され、ASIC が MPLS パケット処理をサポートしない場合、SAI の `create_qos_map` が `SAI_STATUS_NOT_SUPPORTED` を返して `task_failed` になる。

### 3. デフォルトマップ投入の差

`cbf_config.j2` は CBF 機能を有効化する際の初期投入テンプレート。CBF を使用しないプラットフォームは `cbf_config.j2` を適用しないため `EXP_TO_FC_MAP` にエントリが存在しない。非 MPLS プラットフォームでは設定自体が不要。

### 4. `allPortsReady()` 依存

ポート初期化完了前は `QosOrch::doTask()` が即 return するため、CONFIG_DB への `EXP_TO_FC_MAP` 書き込みがプラットフォーム初期化シーケンスより先行した場合、ポート ready 後に一括処理される。プラットフォームごとのポート初期化時間の差がエントリ適用タイミングに影響する。

## 結論

プラットフォーム差のうち運用上最重要なのは `max_num_fcs` の値。MPLS/CBF 未サポートの ASIC では `EXP_TO_FC_MAP` を設定しても全エントリが reject される。
