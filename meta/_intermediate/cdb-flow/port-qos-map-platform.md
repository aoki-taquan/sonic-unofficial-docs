# PORT_QOS_MAP — Phase H プラットフォーム差分

evidence source: `sonic-swss/orchagent/qosorch.cpp`

## 1. SAI capability チェック (`applyDscpToTcMapToSwitch`)

`handleGlobalQosMap` が `PORT_QOS_MAP|global` の `dscp_to_tc_map` を switch level に適用する前に、
`gSwitchOrch->querySwitchCapability(SAI_OBJECT_TYPE_SWITCH, SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP)` で
switch-level DSCP-to-TC map をサポートするか問い合わせる。

- capability `false` → `"Switch level DSCP to TC QoS map configuration is not supported"` を SWSS_LOG_ERROR で出力し、`true` を返して処理続行（適用しない）
- capability `true` → `sai_switch_api->set_switch_attribute(gSwitchId, &attr)` で switch OID へ直接 SET

ソース: `qosorch.cpp:1955-1975`

## 2. Broadcom global vs Mellanox / その他 per-port の差異

`db_migrator.py` の `migrate_port_qos_map_global()` が `PORT_QOS_MAP|global` エントリを自動挿入する際、

```python
asics_require_global_dscp_to_tc_map = ["broadcom"]
if self.asic_type not in asics_require_global_dscp_to_tc_map:
    return
```

として **Broadcom ASIC のみ** に限定している。

- **Broadcom**: `PORT_QOS_MAP|global` エントリが db_migrator により自動生成 → QosOrch が `handleGlobalQosMap` を呼び出し `SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP` を switch レベルで適用
- **Mellanox / その他**: `migrate_port_qos_map_global` が早期 return → `PORT_QOS_MAP|global` エントリは自動挿入されない → `dscp_to_tc_map` は per-port の `SAI_PORT_ATTR_QOS_DSCP_TO_TC_MAP` のみで管理

ソース: `sonic-utilities/scripts/db_migrator.py:700-715`

## 3. VOQ chassis 差異 (`gMySwitchType == "voq"`)

VOQ chassis 環境では `PortQosMapHandler` から呼ばれる下位関数が switch type で分岐する。

### 3a. `applySchedulerToQueueSchedulerGroup` (qosorch.cpp:1637)

| switch type | 挙動 |
|-------------|------|
| `voq` | system port がリモートポートなら即 `return true`（スキップ）。local port を `getPort()` で取得し直してから scheduler group を設定 |
| 通常 (非 voq) | `port.m_queue_ids` から直接 queue_id を取得して scheduler group を設定 |

### 3b. `applyWredProfileToQueue` (qosorch.cpp:1715)

| switch type | 挙動 |
|-------------|------|
| `voq` | `gPortsOrch->getPortVoQIds(port)` で VOQ ID リストを取得して WRED 適用 |
| 通常 (非 voq) | `port.m_queue_ids` から直接 queue_id を取得して WRED 適用 |

### 3c. `handleQueueTable` key format (qosorch.cpp:1772)

| switch type | key 形式 | 例 |
|-------------|----------|----|
| `voq` | 4 トークン `host|asic|port|range` | `STG01-0101-0400-01T2-LC6\|ASIC0\|Ethernet4\|0-1` |
| 通常 (非 voq) | 2 トークン `port|range` | `Ethernet4\|0-1` |

VOQ 環境では `tokens[0] == gMyHostName` かつ `tokens[1].lower() == gMyAsicName.lower()` の場合のみ local port として処理され、それ以外のリモート system port はスキップされる。

ソース: `qosorch.cpp:1772-1792`

## サマリー

| 分岐軸 | Broadcom | Mellanox / その他 | VOQ chassis |
|--------|----------|-------------------|-------------|
| `PORT_QOS_MAP\|global` 自動挿入 | db_migrator が自動生成 | 自動挿入なし（per-port のみ） | 通常と同様（asic_type 依存） |
| `dscp_to_tc_map` 適用先 | switch レベル (`SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP`) | port レベル (`SAI_PORT_ATTR_QOS_DSCP_TO_TC_MAP`) | switch type 分岐は scheduler/WRED 側で発生 |
| SAI capability guard | `querySwitchCapability` で確認 | 同上（not supported なら no-op） | 同上 |
| queue ID 取得 | `port.m_queue_ids` | 同左 | `getPortVoQIds()` |
| scheduler group 適用 | local port から直接 | 同左 | remote system port はスキップ |
