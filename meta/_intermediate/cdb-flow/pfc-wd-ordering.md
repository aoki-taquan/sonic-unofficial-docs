# PFC_WD ordering 調査証跡

## 調査対象

- `sonic-swss/orchagent/pfcwdorch.cpp`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-pfcwd.yang`

## 発見した順序依存

### 1. allPortsReady() ガード

`PfcWdOrch::doTask()` の冒頭 (pfcwdorch.cpp:68-71):

```cpp
if (!gPortsOrch->allPortsReady())
{
    return;
}
```

全ポート初期化完了前は doTask() が即時リターン。PFC_WD の全エントリが消費されない。

### 2. getPort() ガード

`createEntry()` 内 (pfcwdorch.cpp:193-197):

```cpp
if (!gPortsOrch->getPort(key, port))
{
    SWSS_LOG_ERROR("%s is not a port", key.c_str());
    return task_process_status::task_invalid_entry;
}
```

存在しないポート名 → task_invalid_entry（リトライなし、恒久スキップ）。

### 3. YANG must 制約 (POLL_INTERVAL <= detection_time, restoration_time)

sonic-pfcwd.yang:61-73:

GLOBAL エントリ (POLL_INTERVAL) が存在する場合、per-port の detection_time と restoration_time は
POLL_INTERVAL 以上必須。書き込み順序が逆だと YANG バリデーションが失敗する可能性。

### 4. ウォームリブート順序 (pfcwdorch.cpp:856-875)

CONFIG_DB (CFG_PFC_WD_TABLE_NAME) を先に drain してから
APPL_DB (APP_PFC_WD_TABLE_NAME) を drain する。
コールドブートでは APP_PFC_WD_TABLE_NAME が空なので順序制約なし。
