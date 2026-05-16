# flex-counter-table Phase H — プラットフォーム差分 (platform differences)

Generated: 2026-05-16  
Source: sonic-swss/orchagent/flexcounterorch.cpp  
Target doc: docs/reference/config-db/flex-counter-table.md

## SAI counter capability 差分

### FLOW_CNT_ROUTE — SAI capability ガード

```cpp
// flexcounterorch.cpp:324
if (gFlowCounterRouteOrch && gFlowCounterRouteOrch->getRouteFlowCounterSupported() && key == FLOW_CNT_ROUTE_KEY)
```

- `getRouteFlowCounterSupported()` が `false` の場合（SAI が route flow counter を未サポートの ASIC）、`FLEX_COUNTER_STATUS = enable` を CONFIG_DB に書いても SAI 設定は一切行われない。
- エラー通知なし（silent no-op）。`COUNTERS_DB` には該当エントリが現れないため、ユーザーはカウンタが増分しないことで初めて気づく。
- 対応 ASIC: SAI で `SAI_SWITCH_ATTR_SUPPORTED_COUNTER_EVENTS` に route flow counter が含まれているかどうかに依存（実装は `flowcounterrouteorch.cpp` 参照）。

## ASIC ベンダー対応差

### Gearbox 有効時のダブル登録 (PORT / MACSEC)

```cpp
// flexcounterorch.cpp:204-209, 382-388
if (gPortsOrch && gPortsOrch->isGearboxEnabled())
{
    if (key == PORT_KEY || key.rfind("MACSEC", 0) == 0)
    {
        setFlexCounterGroupPollInterval(flexCounterGroupMap[key], value, true);
        setFlexCounterGroupOperation(flexCounterGroupMap[key], value, true);
    }
}
```

- PHY チップ (Gearbox) を搭載する ASIC プラットフォームでは、`PORT` および `MACSEC*` グループに対し **追加の PHY 側 FlexCounter グループ** にも同一の POLL_INTERVAL と STATUS が設定される（第3引数 `true` = PHY 側コンテキスト）。
- Gearbox なし環境（大多数の標準 TOR スイッチ）ではこの分岐は無効。影響グループ: `PORT`, `MACSEC_SA`, `MACSEC_SA_ATTR`, `MACSEC_FLOW`。

### PORT_PHY_ATTR / PORT_PHY_SERDES_ATTR — 物理層属性カウンタ

```cpp
// flexcounterorch.cpp:341-368
if (gPortsOrch && (key == PORT_PHY_ATTR_KEY))
{
    if(value == "enable")
    {
        gPortsOrch->generatePortPhyAttrCounterMap();
        gPortsOrch->generatePortPhySerdesAttrCounterMap();
    }
    ...
}
// POLL_INTERVAL も連動
if (key == PORT_PHY_ATTR_KEY)
{
    setFlexCounterGroupPollInterval(flexCounterGroupMap[PORT_PHY_SERDES_ATTR_KEY], value);
}
```

- `PORT_PHY_ATTR` を enable/disable にすると `PORT_PHY_SERDES_ATTR` も **自動で連動** する。
- SERDES 属性をサポートする ASIC（Broadcom Tomahawk 系等のファミリー）でのみ実際に値が返る。SERDES 未対応 ASIC では空のカウンタリストが登録されるが、エラーにはならない。
- CONFIG_DB に `FLEX_COUNTER_TABLE|PORT_PHY_SERDES_ATTR` キーを直接書く必要はなく、書いても orchagent が `PORT_PHY_ATTR` の設定で上書きする。

### WRED_ECN カウンタ — ASIC WRED サポート依存

- `WRED_ECN_PORT` / `WRED_ECN_QUEUE` は、SAI が WRED/ECN マーキングカウンタをサポートするプラットフォームでのみ意味を持つ。
- SAI で `SAI_QUEUE_STAT_WRED_*` 属性が未実装の ASIC では、enable しても COUNTERS_DB にゼロのみが返る（no-op に近い）。

## VOQ chassis 差分

### VOQ chassis での QUEUE / WRED_ECN_QUEUE カウンタ全量収集

```cpp
// flexcounterorch.cpp:544-551 (getQueueConfigurations)
// For VOQ chassis, flexcounterorch adds the Queue Counters for all egress and VOQ queues
// of all front panel and system ports to the FLEX_COUNTER_DB irrespective of BUFFER_QUEUE configuration.
if ((!isCreateOnlyConfigDbBuffers()) || (gMySwitchType == "voq"))
{
    FlexCounterQueueStates flexCounterQueueState(0);
    queuesStateVector.insert(make_pair(createAllAvailableBuffersStr, flexCounterQueueState));
    return queuesStateVector;
}
```

- 通常構成 (`create_only_config_db_buffers = true`) では BUFFER_QUEUE テーブルに設定されたポート/キューのみカウンタを収集。
- **VOQ chassis** (`gMySwitchType == "voq"`) では、BUFFER_QUEUE 設定に関わらず **全フロントパネルポートおよびシステムポートの全エグレス・VOQ キュー** をカウンタ収集対象とする。
- この差は FLEX_COUNTER_TABLE への書き込み内容には依存せず、スイッチ種別 (`switch_type`) により自動的に分岐する。

### VOQ chassis での PG カウンタ — 差分なし

```cpp
// flexcounterorch.cpp:615-620 (getPgConfigurations)
if (!isCreateOnlyConfigDbBuffers())
{
    // 全 PG を収集（create_only_config_db_buffers = false の場合）
    ...
}
```

- PG カウンタ (`PG_DROP`, `PG_WATERMARK`) は VOQ 特例なし。`create_only_config_db_buffers` フラグのみで分岐。
- VOQ chassis でも BUFFER_PG 設定分のみが収集対象。QUEUE との非対称な動作に注意。

## プラットフォーム別グループ有効化サマリ

| グループ | 標準 TOR | Gearbox 搭載 | VOQ chassis | DPU |
|---------|---------|------------|------------|-----|
| `PORT` | ○ | ○ (PHY 側にも二重登録) | ○ | △ (DPU 用 ENI が優先) |
| `MACSEC_*` | △ (MACsec ライセンスが必要) | ○ (PHY 側にも二重登録) | △ | — |
| `PORT_PHY_ATTR` | △ (SERDES 対応 ASIC のみ有効) | ○ | △ | — |
| `PORT_PHY_SERDES_ATTR` | 自動連動 (PORT_PHY_ATTR 依存) | 自動連動 | 自動連動 | — |
| `FLOW_CNT_ROUTE` | △ (SAI capability 要確認) | △ | △ | △ |
| `ENI` / `DASH_METER` / `HA_SET` | — | — | — | ○ (DPU のみ) |
| `QUEUE` (全量) | BUFFER_QUEUE 分のみ | BUFFER_QUEUE 分のみ | 全量 (VOQ 特例) | — |
| `WRED_ECN_*` | △ (WRED 対応 ASIC のみ) | △ | △ | — |

凡例: ○=常に有効、△=条件付き、—=非対応/未定義

## 検出された discrepancy / 注意点

1. **FLOW_CNT_ROUTE silent no-op**: SAI が route flow counter を未サポートの場合、enable を書いてもエラーなし・カウンタなし。`getRouteFlowCounterSupported()` を orchagent 内でチェックしているが結果をユーザー通知しない。
2. **VOQ chassis の QUEUE/PG 非対称性**: QUEUE は全量収集になるが PG はならない。同じ VOQ 環境でもグループによって動作が異なる。
3. **Gearbox 二重登録の opacity**: POLL_INTERVAL 変更時に PHY 側 FlexCounter グループにも同一値が書かれるが、CONFIG_DB 上は `PORT` グループへの単一エントリのみ。`FLEX_COUNTER_DB` を直接見ないと PHY 側の状態が確認できない。
4. **PORT_PHY_SERDES_ATTR の YANG 非定義**: `PORT_PHY_SERDES_ATTR` は `flexCounterGroupMap` に存在するが、YANG `sonic-flex_counter` には対応する list entry がない（YANG スキーマ外の implicit グループ）。
