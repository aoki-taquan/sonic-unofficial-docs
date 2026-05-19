# stp-state-failure: Phase D 証跡

## 調査対象

- `sonic-swss/orchagent/stporch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/stpmgr.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/stpmgrd.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/stpmgr.h` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## 調査日

2026-05-19

## 失敗経路まとめ

### 1. SAI 取得失敗 → STATE_DB 未書込み

`stporch.cpp:34-42`:
```cpp
status = sai_switch_api->get_switch_attribute(gSwitchId, (uint32_t)attrs.size(), attrs.data());
if (status == SAI_STATUS_SUCCESS)
{
    m_defaultStpId = attrs[0].value.oid;
    updateMaxStpInstance(attrs[1].value.u32);
    ret = true;
}
SWSS_LOG_NOTICE("StpOrch initialization %s", (ret == true)?"success":"failure");
```

SAI 取得失敗時: `updateMaxStpInstance()` 呼ばれず → `STP_TABLE|GLOBAL` エントリ未作成。
エラーレベル: `SWSS_LOG_NOTICE` で "failure" のみ (ERROR でない)。

### 2. stpmgr.cpp のタイムアウトフォールバック

`stpmgr.cpp:1381-1413`:
- 60 秒ポーリング (`max_delay = 60`, `sleep(1)`)
- `STP_TABLE|GLOBAL` が 60 秒以内に見つからない場合 → `max_stp_instances = STP_DEFAULT_MAX_INSTANCES = 255` (`stpmgr.h:38`)
- タイムアウト時は `SWSS_LOG_NOTICE("set default max stp instance %d", ...)` のみ (ERROR ログなし)

### 3. Redis 接続失敗 (STATE_DB)

`m_stpTable->set("GLOBAL", tuples)` は `swss::Table::set()` で void 戻り値。
Redis I/O エラー時は `system_error` / `runtime_error` が `swss::DBConnector` から送出される。
`stporch.cpp` には try/catch なし → 例外は `orchdaemon` まで伝播 → orchagent プロセス abort。
systemd / supervisord による再起動で自己回復。

### 4. stpmgrd の `runtime_error` catch

`stpmgrd.cpp:119-122`:
```cpp
catch (const exception &e)
{
    SWSS_LOG_ERROR("Runtime error: %s", e.what());
}
return -1;
```

stpmgrd プロセスは `catch` してログ出力後に `-1` で終了 (retry なし)。
MAC アドレス取得失敗 (`couldn't find MAC address of the device from config DB`) も同経路。

### 5. ipcInitStpd() / sendMsgStpd() の失敗

IPC ソケット初期化失敗は stpmgrd 起動失敗につながるが STATE_DB への影響なし。
`STP_TABLE|GLOBAL` の読み取り (`getStpMaxInstances()`) は `ipcInitStpd()` の後、
`sendMsgStpd()` の前に呼ばれる (stpmgrd.cpp:71-78)。
