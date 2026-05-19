# dpu-orch — Phase D 失敗挙動調査メモ

## 調査対象

- `sonic-swss/orchagent/main.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/lib/orch_zmq_config.cpp`
- `sonic-swss/orchagent/dash/dashorch.cpp`
- `sonic-swss/orchagent/dash/dashaclorch.cpp`
- `sonic-swss/orchagent/dash/dashhaorch.cpp`
- `sonic-swss/orchagent/dash/dashrouteorch.cpp`

## 調査方法

各ファイルで `SWSS_LOG_ERROR` / `SWSS_LOG_WARN` / `return false` / `task_failed` /
`SAI_STATUS` / `exit(EXIT_FAILURE)` を grep し、失敗分岐を整理。

## A. `get_feature_status()` 失敗 (CONFIG_DB 接続失敗)

`orch_zmq_config.cpp:81-103` の `get_feature_status()`:

```
try {
    DBConnector config_db("CONFIG_DB", 0);
    enabled = config_db.hget("DEVICE_METADATA|localhost", feature);
} catch (const std::runtime_error &e) {
    SWSS_LOG_ERROR("Not found feature %s failed with exception: %s", ...);
    return default_value;  // ← フォールバック
}
```

- CONFIG_DB 接続失敗 → `runtime_error` catch → `SWSS_LOG_ERROR` + `default_value` 返却
- `orch_northbond_dash_zmq_enabled` の場合 default_value=true → ZMQ が有効化される
- `orch_northbond_route_zmq_enabled` の場合 default_value=false → ZMQ 無効
- **フォールバックのみで`init()`は中断しない**

## B. `DpuOrchDaemon::init()` 失敗 → `exit(EXIT_FAILURE)`

`orchdaemon.cpp:1322` の `DpuOrchDaemon::init()` は失敗しても `return false` しない
（コード上 `return true` のみ）。実質失敗するのは以下の経路:

1. `OrchDaemon::init()` が false → `DpuOrchDaemon::init()` は戻り値をチェックしていない
   （orchdaemon.cpp:1324 では `OrchDaemon::init()` の戻り値を無視している）
2. `main.cpp:1017-1020`:
   ```cpp
   if (!orchDaemon->init()) {
       SWSS_LOG_ERROR("Failed to initialize orchestration daemon");
       exit(EXIT_FAILURE);
   }
   ```
   `DpuOrchDaemon::init()` が例外送出 or false → `exit(EXIT_FAILURE)` → systemd が再起動

## C. `DPU_APPL_DB` / `DPU_APPL_STATE_DB` 接続失敗

`main.cpp:992-993`:
```cpp
dpu_app_db = make_shared<DBConnector>("DPU_APPL_DB", 0, true);
dpu_app_state_db = make_shared<DBConnector>("DPU_APPL_STATE_DB", 0, true);
```
- `DBConnector` コンストラクタ失敗は例外送出 → `main()` で捕捉されず orchagent abort
- systemd 再起動によって自己回復

## D. DASH Orch SAI 操作失敗 → `it++` retry / erase

`dashorch.cpp` / `dashaclorch.cpp` / `dashrouteorch.cpp` / `dashhaorch.cpp` の共通パターン:

- SAI API 失敗 (`SAI_STATUS != SAI_STATUS_SUCCESS`) → `return false` from add/remove 関数
- `doTask()` で `addXxx()` が false → `result = DASH_RESULT_FAILURE` → `writeResultToDB()` → `it++` (retry)
- `removeXxx()` が false → `it++` (retry)
- parse/validate 失敗 → `erase(it)` (恒久スキップ)
- `writeResultToDB()` は `DPU_APPL_STATE_DB` に `result=DASH_RESULT_SUCCESS(0)` / `DASH_RESULT_FAILURE(1)` を書き込む

## E. `switch_type` 不正値

`main.cpp:260-264`:
```cpp
if (switch_type != "voq" && ... && switch_type != "dpu") {
    SWSS_LOG_ERROR("Invalid switch type %s configured", switch_type.c_str());
    switch_type = "switch";  // ← "switch" にフォールバック → DpuOrchDaemon 非選択
}
```
- 不正値は `"switch"` にフォールバックし、`DpuOrchDaemon` は選択されない
- `SWSS_LOG_ERROR` がログに出力されるが orchagent は継続起動する
