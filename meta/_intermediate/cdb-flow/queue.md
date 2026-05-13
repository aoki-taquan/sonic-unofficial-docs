# QUEUE 例外条件抽出 (cdb-batch-7)

## ソース
- `sonic-swss/orchagent/qosorch.cpp`

## 抽出した例外条件

1. **key トークン数不正**: 非 VOQ 環境では key が `<ifname>|<qindex>` の 2 トークンでなければならない。VOQ 環境では 4 トークン必須。違反時は `task_invalid_entry` を返して処理中断。
   - 証拠: `SWSS_LOG_ERROR("malformed key:%s. Must contain 2 tokens", key.c_str())` (l.1803) / `"Must contain 4 tokens"` (l.1776)

2. **queue index 範囲外**: `<qindex>` が SAI の queue 数を超えた場合 `SWSS_LOG_ERROR("Invalid queue index specified:%zd")` でスキップ。
   - 証拠: qosorch.cpp l.1653 / l.1672 / l.1720 / l.1729

3. **SCHEDULER 参照未解決 (リトライ)**: `scheduler` フィールドが存在するが `SCHEDULER` テーブルに対象プロファイルがまだ存在しない場合は `task_need_retry` を返して後で再試行される。
   - 証拠: `SWSS_LOG_INFO("Missing or invalid scheduler reference"); return task_process_status::task_need_retry`

4. **WRED_PROFILE 参照未解決 (リトライ)**: 同様に `wred_profile` が解決できない場合も `task_need_retry`。

5. **SCHEDULER 参照解決失敗 (永続エラー)**: `not_resolved` 以外の解決エラーは `task_failed` で恒久エラーになる。
   - 証拠: `SWSS_LOG_ERROR("Resolving scheduler reference failed"); return task_process_status::task_failed`

6. **WRED min > max 制約**: WRED プロファイルの `green_min_threshold > green_max_threshold` 等の場合 qosorch がエラー出力して SAI 設定をスキップ。
   - 証拠: `SWSS_LOG_ERROR("Wrong wred profile: min threshold is greater than max threshold")`

7. **port 未検出**: key の `<ifname>` が PORT テーブルに存在しない場合 `SWSS_LOG_ERROR("Port with alias:%s not found")` でスキップ。

8. **scheduler group 未検出**: port が存在しても queue index に対応する SAI scheduler group が見つからない場合 `task_failed`。
