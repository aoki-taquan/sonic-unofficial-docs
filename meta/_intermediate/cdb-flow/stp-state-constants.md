# stp-state — Phase E ハードコード定数調査ノート

調査日: 2026-05-19
対象ファイル:
- sonic-swss/orchagent/stporch.h
- sonic-swss/orchagent/stporch.cpp
- sonic-swss/cfgmgr/stpmgr.h
- sonic-swss/cfgmgr/stpmgr.cpp

## 抽出定数

| 定数 | 値 | 定義箇所 | 用途 |
|-----|----|---------|------|
| `STP_INVALID_INSTANCE` | `0xFFFF` (65535) | `stporch.h:8` | 未割り当て STP インスタンス ID のセンチネル値 |
| `-1` 補正 | SAI 値 − 1 | `stporch.cpp:605` | `max_stp_instance - 1` を STATE_DB に書き込む |
| `STP_DEFAULT_MAX_INSTANCES` | `255` | `stpmgr.h:38` | タイムアウト時フォールバック値 |
| `max_delay` | `60` 秒 | `stpmgr.cpp:1384` | ポーリングタイムアウト上限 |
| `L2_INSTANCE_MAX` | `MAX_VLANS` = `4096` | `stpmgr.h:34,37` | l2InstPool サイズ上限 |

## 調査根拠

```cpp
// stporch.h:8
#define STP_INVALID_INSTANCE 0xFFFF

// stporch.cpp:603-617
bool StpOrch::updateMaxStpInstance(uint32_t max_stp_instances)
{
    m_maxStpInstance = (sai_uint16_t)max_stp_instances - 1;
    ...
    FieldValueTuple tuple("max_stp_inst", to_string(m_maxStpInstance));
    tuples.push_back(tuple);
    m_stpTable->set("GLOBAL", tuples);
    return true;
}

// stpmgr.h:38
#define STP_DEFAULT_MAX_INSTANCES   255

// stpmgr.cpp:1384
uint16_t max_delay = 60;
...
while(max_delay)
{
    if (m_stateStpTable.get(key, vmEntry)) { break; }
    sleep(1);
    max_delay--;
}
if(max_stp_instances == 0)
{
    max_stp_instances = STP_DEFAULT_MAX_INSTANCES;
}
```
