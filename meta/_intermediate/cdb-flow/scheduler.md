# SCHEDULER 例外条件抽出 (cdb-batch-7)

## ソース
- `sonic-swss/orchagent/qosorch.cpp`

## 抽出した例外条件

1. **type フィールドが未知の値**: `type` が `DWRR` / `WRR` / `STRICT` 以外の場合 `SWSS_LOG_ERROR("Unknown scheduler type value:%s")` を出し `task_invalid_entry` を返す。エントリは破棄される。
   - 証拠: qosorch.cpp l.1394-1396

2. **SAI scheduler profile 作成失敗**: `sai_scheduler_api->create_scheduler(...)` が失敗した場合 `SWSS_LOG_ERROR("Failed to create scheduler profile [%s:%s], rv:%d")` → 処理中断。ASIC に反映されない。
   - 証拠: l.1463

3. **SAI scheduler attribute 設定失敗**: `sai_scheduler_api->set_scheduler_attribute(...)` が失敗した場合 `SWSS_LOG_ERROR("fail to set scheduler attribute, id:%d")` → 処理中断。
   - 証拠: l.1449

4. **SAI scheduler profile 削除失敗**: まだ QUEUE から参照されている scheduler profile を削除しようとすると SAI が EBUSY 等を返し `SWSS_LOG_ERROR("Failed to remove scheduler profile, status:%d")` となる。CONFIG_DB からは削除されても ASIC は古いプロファイルを保持し続ける。
   - 証拠: l.871

5. **weight フィールドのオーバフロー**: `weight` は `uint8` にキャストされるため 0-255 の範囲外は暗黙切り捨てとなる（バリデーションなし）。

6. **QUEUE 参照が存在する間は削除不可 (SAI 依存)**: `SCHEDULER` プロファイルを `QUEUE` が参照している状態で削除すると SAI レイヤで失敗する。qosorch は削除失敗時に `task_failed` を返し、QUEUE の参照を先に外すことを要求する。
