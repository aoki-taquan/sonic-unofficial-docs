# pfcwd-state — 副次 DB 書込 (Phase F) 調査メモ

source: sonic-swss/orchagent/pfcwdorch.cpp, pfcactionhandler.cpp (ref: master)

## 1. APPL_DB への書込 (storm 状態の永続化)

storm 検知時 (`startWdActionOnQueue("storm", ...)`, `pfcwdorch.cpp:998,1017,1034`):
```cpp
string key = m_applTable->getTableName() + m_applTable->getTableNameSeparator() + entry->second.portAlias;
m_applDb->hset(key, to_string(entry->second.index), PFC_WD_IN_STORM);
```
- テーブル: `APPL_DB:PFC_WD_INSTORM|<port>`
- フィールド: `<queue_index>` = `"storm"`
- 目的: warm-reboot 後に storm 状態を復元するための永続化

storm 復旧時 (`pfcwdorch.cpp:1056-1058`):
```cpp
string key = m_applTable->getTableName() + m_applTable->getTableNameSeparator() + entry->second.portAlias;
m_applDb->hdel(key, to_string(entry->second.index));
```
- `hdel` で queue エントリを削除

## 2. SAI 経由のポート PFC マスク変更 (LossyHandler)

storm アクションが `drop` または `alert` の場合、`PfcWdLossyHandler` コンストラクタ
(`pfcactionhandler.cpp:541-568`) が呼ばれ:
- `gPortsOrch->getPortPfc(port, &pfcMask)` で現在の PFC マスクを取得
- `pfcMask &= ~(1 << queueId)` でストームキューの PFC ビットをクリア
- `gPortsOrch->setPortPfc(port, pfcMask)` → SAI `sai_port_api->set_port_attribute()` でハードウェアに反映

storm 復旧時 (`~PfcWdLossyHandler()`):
- `pfcMask |= (1 << queueId)` でビットを戻す → `setPortPfc()` で再有効化

Cisco 8000 および Broadcom+DLR INIT 有効環境ではこのマスク変更をスキップ。

## 3. SAI 経由の SAI_QUEUE_ATTR_PFC_DLR_INIT 設定 (DLR ハンドラ)

`PfcWdSaiDlrInitHandler` / `PfcWdDlrHandler` コンストラクタ (`pfcactionhandler.cpp:225-305`):
- storm 検知時: `sai_queue_api->set_queue_attribute(queue, SAI_QUEUE_ATTR_PFC_DLR_INIT=true)` → DLR 開始
- storm 復旧時 (デストラクタ): `set_queue_attribute(SAI_QUEUE_ATTR_PFC_DLR_INIT=false)` → DLR 停止

Broadcom + DLR INIT が有効な場合に使用される。

## 4. SAI スイッチレベル属性設定 (Broadcom + DLR 初回登録)

`createEntry()` (`pfcwdorch.cpp:244-251`) で Broadcom + PFC DLR INIT 有効 + 初回ポート登録時:
```cpp
sai_switch_api->set_switch_attribute(gSwitchId, SAI_SWITCH_ATTR_PFC_DLR_PACKET_ACTION=action)
```
- スイッチ全体に PFC DLR パケットアクション (`drop`/`forward`) を設定
- 2 ポート目以降はアクション一致確認のみ（変更なし）

## 5. FLEX_COUNTER_DB / FlexCounterManager 経由の書込

`registerInWdDb()` (`pfcwdorch.cpp:558-595`) が FlexCounterTaggedCachedManager 経由で:
- PORT: `PFC_WD` グループにポート stat ID リストを登録 (`setCounterIdList(port_id, CounterType::PORT, ...)`)
- QUEUE: `PFC_WD` グループにキュー stat ID リストを登録 (`setCounterIdList(queue_id, CounterType::QUEUE, ...)`)
- QUEUE_ATTR: queue attr ID リストを登録 (FlexCounterManager 直接)

`unregisterFromWdDb()` (`pfcwdorch.cpp:648-660`) が `clearCounterIdList()` で削除。

## 6. SONiC events framework 経由の storm イベント発行

`report_pfc_storm()` (`pfcwdorch.cpp:965`):
```cpp
event_publish(g_events_handle, "pfc-storm", &params);
```
- SONiC events framework に `pfc-storm` イベントを発行（gNMI/event-driven telemetry向け）
- params: `port-id`, `queue-index`, `additional_info`

## 7. 副次書込なし

- STATE_DB: pfcwdorch / pfcactionhandler は STATE_DB に書き込まない
- ERROR_TABLE: 失敗時もエラーフィードバックテーブルへの書込なし
- ASIC_DB: SAI 経由で syncd が書き込む（orchagent の直接書込なし）
