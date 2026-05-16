# SCHEDULER — Platform 差異調査 (Phase H)

> 調査日: 2026-05-16  
> ソース: `sonic-net/sonic-swss/orchagent/qosorch.cpp`  
> 担当関数: `applySchedulerToQueueSchedulerGroup()`, `handleQueueTable()`, `handleSchedulerTable()`

---

## 1. VOQ Chassis (gMySwitchType == "voq")

`applySchedulerToQueueSchedulerGroup()` (L1631–1710) に `gMySwitchType == "voq"` 分岐あり。

### リモートシステムポートへの早期 return

```cpp
// qosorch.cpp:L1637-1641
if (gMySwitchType == "voq") 
{
    if(port.m_system_port_info.type == SAI_SYSTEM_PORT_TYPE_REMOTE)
    {
        return true;  // ASIC 書き込みをスキップ
    }
```

VOQ シャーシ構成において **リモートシステムポート**（`SAI_SYSTEM_PORT_TYPE_REMOTE`）には
スケジューラグループへの SAI 書き込みを一切行わない。ローカルポートのみ処理対象。

### ローカルポート解決

リモートでない場合は `port.m_system_port_info.local_port_oid` でローカル物理ポートを取得し、
そのキュー OID (`port.m_queue_ids[queue_ind]`) を使ってスケジューラグループを探索する。

```cpp
// qosorch.cpp:L1643-1648
if (!gPortsOrch->getPort(port.m_system_port_info.local_port_oid, port))
{
    SWSS_LOG_ERROR("Port with alias:%s not found", port.m_alias.c_str());
    return task_process_status::task_invalid_entry;
}
```

処理後、`port` を元のシステムポート (`input_port`) に戻す（L1666）。

### QUEUE キー形式の違い (handleQueueTable)

VOQ モードでは QUEUE テーブルのキー形式が 4 トークン必須:

```
QUEUE|<hostname>|<ASIC_NAME>|<port>|<index_range>
# 例: STG01-0101-0400-01T2-LC6|ASIC0|Ethernet4|0-1
```

非 VOQ では 2 トークン (`<port>|<index_range>`)。キー形式の差は SCHEDULER 自体の挙動に影響しないが、QUEUE が SCHEDULER を参照する際の前提条件となる。

---

## 2. SmartSwitch / DPU

`qosorch.cpp` に SmartSwitch / DPU 固有の分岐は**存在しない**。
`grep "SmartSwitch\|DPU\|dpu"` で 0 件。SCHEDULER テーブルの処理は NPU / DPU 問わず
同一コードパスを辿る。

---

## 3. ベンダー差（SAI 抽象化）

`handleSchedulerTable()` は SAI API (`sai_scheduler_api->create_scheduler()` / `set_scheduler_attribute()` / `remove_scheduler()`) を呼ぶのみで、ベンダー固有の条件分岐はない。ただしコメント (L599) に:

> "for any color at any time, on some vendor's platforms."
> "the vendor SAI do not have a big picture regarding what attributes are being set"

という記述があり、SAI 属性の**設定順序がベンダーによって影響する**ことが示唆されている（DSCP_TO_TC 関連のコメントだが QoS 全般に共通する注意点）。

### SAI ベンダー依存の挙動まとめ

| 挙動 | ベンダー依存の程度 | 備考 |
|------|-----------------|------|
| フィールド省略時の動作（type/weight/meter_type を SAI に送らない） | 高 | SAI ベンダーデフォルト値が適用される。Broadcom は WRR=デフォルト等だが保証なし |
| `DWRR` サポート | 中 | `SAI_SCHEDULING_TYPE_DWRR` をサポートしない ASICがある場合は `SAI_STATUS_NOT_SUPPORTED` が返り `handleSaiCreateStatus` で処理される |
| `weight` の有効範囲 | 中 | YANG は 1..100 だが SAI ベンダーは 0-255 全域を受け入れる場合あり |
| CIR/PIR 単位 (`meter_type`) | 低 | `SAI_METER_TYPE_PACKETS` / `SAI_METER_TYPE_BYTES` は SAI 標準で安定 |

---

## 4. まとめ

| プラットフォーム | SCHEDULER 処理の違い |
|----------------|---------------------|
| 標準 L3 スイッチ | フルパス。`handleSchedulerTable` → SAI scheduler 作成/更新/削除 |
| VOQ シャーシ (リモートシステムポート) | `applySchedulerToQueueSchedulerGroup` が早期 return。SCHEDULER オブジェクト自体は作成されるが QUEUE への bind をスキップ |
| VOQ シャーシ (ローカルポート) | local_port_oid を経由してキュー OID を解決し、同じ SAI パスを辿る |
| SmartSwitch / DPU | 差異なし（qosorch.cpp に分岐なし） |
| ベンダー ASIC (Broadcom / Mellanox 等) | SAI 抽象化で差異を吸収。フィールド省略時のデフォルト動作はベンダー依存 |

---

## 5. 証跡

- `sonic-net/sonic-swss/orchagent/qosorch.cpp` L1631–1710 (`applySchedulerToQueueSchedulerGroup`)
- `sonic-net/sonic-swss/orchagent/qosorch.cpp` L1772–1812 (`handleQueueTable` VOQ 分岐)
- `sonic-net/sonic-swss/orchagent/qosorch.cpp` L599, L603 (ベンダーコメント)
