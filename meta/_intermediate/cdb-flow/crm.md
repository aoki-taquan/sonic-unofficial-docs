# CONFIG_DB 例外条件分析: CRM

## Consumer

- `orchagent` の `CrmOrch::doTask` / `handleSetCommand`: CRM テーブルを読み取り、リソース閾値とポーリング間隔を内部状態に保持。タイマーで周期的に SAI リソース使用量を確認し閾値超過時に syslog 警告。

## 例外条件

### 1. percentage 閾値が 100 超 → runtime_error
- ソース: `crmorch.cpp` L429-431
- `thresholdType = CRM_PERCENTAGE` のとき `lowThreshold > 100` または `highThreshold > 100` の場合 `throw runtime_error("CRM percentage threshold value must be <= 100%%")`。caller 側で catch → `SWSS_LOG_ERROR` + return。

### 2. low >= high → runtime_error
- ソース: `crmorch.cpp` L433-435
- `!(lowThreshold < highThreshold)` の場合 `throw runtime_error("CRM low threshold must be less then high threshold")`。同様に catch → エラーログ + return。

### 3. DEL コマンド → 非対応エラーログ
- ソース: `crmorch.cpp` L465-466
- `op == DEL_COMMAND` が来ると `SWSS_LOG_ERROR("Unsupported operation type %s")` を出力しエントリを消費 (削除は適用されない; 閾値は変わらない)。

### 4. 不明属性フィールド → エラーログ + return
- ソース: `crmorch.cpp` L526
- `polling_interval`, threshold_type, threshold_low/high 以外のフィールドが来ると `SWSS_LOG_ERROR("Failed to parse CRM ... Unknown attribute %s.")` して当該フィールド以降の処理を中断 (`return`)。残りフィールドも適用されない。

### 5. 型変換エラー (to_uint 等) → 例外 catch + エラーログ + return
- ソース: `crmorch.cpp` L529-536
- `stoul` 等で変換失敗した場合 `std::exception` catch → `SWSS_LOG_ERROR("... error: %s")` して `return`。

### 6. 未知リソース種別 → エラーログ (集計スキップ)
- ソース: `crmorch.cpp` L1057
- タイマー処理で `m_resourcesMap` にないリソース種別が来ると `SWSS_LOG_ERROR("Failed to get CRM resource type ... Unknown resource type.")` 。

### 7. 未対応リソース → ignore (884)
- ソース: `crmorch.cpp` L884
- SAI から取得できないリソースのカウント取得は `// ignore unsupported resources` としてスキップ。
