# crm — Phase D 失敗挙動スキャンノート

ソース: `sonic-swss/orchagent/crmorch.cpp`

## 抽出した失敗挙動

### 1. 不正 threshold_type 値 → `std::out_of_range` → エラーログ + return

`handleSetCommand()` L494-508: `crmThreshTypeMap.at(value)` で未知の threshold_type 文字列を渡すと `std::out_of_range` が発生。catch ブロック (L529-533) で `SWSS_LOG_ERROR("Failed to parse CRM %s attribute %s error: %s.")` を出力し `return`。後続フィールドも適用されない。

evidence: `crmorch.cpp:496, 529-533`

### 2. percentage 閾値 > 100 → `runtime_error` → エラーログ + return

`CrmResourceEntry` コンストラクタ (L428-431): `thresholdType == CRM_PERCENTAGE` かつ `lowThreshold > 100 || highThreshold > 100` のとき `runtime_error("CRM percentage threshold value must be <= 100%%")` をスロー。呼び出し元 `handleSetCommand` の catch (L529-533) で `SWSS_LOG_ERROR` + `return`。

evidence: `crmorch.cpp:428-431, 529-533`

### 3. low >= high → `runtime_error` → エラーログ + return

同コンストラクタ (L433-435): `!(lowThreshold < highThreshold)` のとき `runtime_error("CRM low threshold must be less then high threshold")` をスロー。同様に catch → `SWSS_LOG_ERROR` + `return`。

evidence: `crmorch.cpp:433-435, 529-533`

### 4. 不正 polling_interval 値 → `to_uint` 失敗 → エラーログ + return

`handleSetCommand()` L489: `to_uint<uint32_t>(value)` で非数値・負値・uint32 超の文字列を渡すと例外。catch (L529-533) で `SWSS_LOG_ERROR` + `return`。タイマーは更新されない。

evidence: `crmorch.cpp:489, 529-533`

### 5. 未知フィールド → エラーログのみ（return せず次フィールドへ）

`handleSetCommand()` L524-527: いずれのマップにも該当しない field 名のとき `SWSS_LOG_ERROR("Failed to parse CRM %s configuration. Unknown attribute %s.")` を出力。ただし `return` せず次フィールドのループを継続する（exception を throw しないため catch に入らない）。

evidence: `crmorch.cpp:524-527`

### 6. SAI リソース取得失敗 → エラーログ + return false（カウンタ未更新）

`getResAvailability()` L823-826: `sai_object_type_get_availability` / `sai_switch_api->get_switch_attribute` が `SAI_STATUS_SUCCESS` 以外を返すと `SWSS_LOG_ERROR("Failed to get availability counter for %s CRM resource")` + `return false`。COUNTERS_DB の availableCounter は前回値のまま。

`getResAvailableCounters()` L953-974: `CRM_ACL_TABLE`/`CRM_ACL_GROUP` 系で `get_switch_attribute` 失敗時も同様。`handleSaiGetStatus` で non-success なら break（ループ継続なし）。

evidence: `crmorch.cpp:823-826, 972-979`

### 7. SAI 未サポートリソース → `CRM_RES_NOT_SUPPORTED` マーク + 以後スキップ

`getResAvailability()` L812-820: `SAI_STATUS_NOT_SUPPORTED` / `SAI_STATUS_NOT_IMPLEMENTED` / `IS_ATTR_NOT_SUPPORTED` / `IS_ATTR_NOT_IMPLEMENTED` の場合 `res.resStatus = CRM_RES_NOT_SUPPORTED` に設定し `SWSS_LOG_NOTICE` + `return false`。以降のポーリングでは `getResAvailableCounters()` L884-888 のガードで skip される。

evidence: `crmorch.cpp:812-820, 884-888`

### 8. DEL コマンド → エラーログのみ（設定変更なし）

`doTask()` L463-466: `op == DEL_COMMAND` 時 `SWSS_LOG_ERROR("Unsupported operation type %s")` を出力するが閾値・interval は一切変更しない。

evidence: `crmorch.cpp:463-466`

### 9. 不明テーブル名 → エラーログのみ

`doTask()` L446-449: `table_name != CFG_CRM_TABLE_NAME` のとき `SWSS_LOG_ERROR("Invalid table %s")` を出力するが処理は継続（return しない）。

evidence: `crmorch.cpp:446-449`
