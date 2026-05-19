# FABRIC_PORT 失敗挙動調査メモ (Phase D)

調査対象: `sonic-swss/orchagent/fabricportsorch.cpp`

## 失敗パス一覧

### 1. `getFabricPortList()` — SAI capability 欠如

#### 1a. `SAI_SWITCH_ATTR_NUMBER_OF_FABRIC_PORTS` 取得失敗

- コード: `fabricportsorch.cpp:172-180`
- `sai_switch_api->get_switch_attribute(SAI_SWITCH_ATTR_NUMBER_OF_FABRIC_PORTS)` が失敗
- `handleSaiGetStatus()` を呼び、`task_success` 以外なら `FABRIC_PORT_ERROR (0)` を返す
- `m_getFabricPortListDone` は false のまま
- 結果: 全てのポーリング処理 (`updateFabricPortState`, `updateFabricDebugCounters`) がスキップされ続ける
- 再試行: `FABRIC_POLL` タイマー (30秒) 発火のたびに `getFabricPortList()` を再試行

#### 1b. `SAI_SWITCH_ATTR_FABRIC_PORT_LIST` 取得失敗

- コード: `fabricportsorch.cpp:190-197`
- `sai_switch_api->get_switch_attribute(SAI_SWITCH_ATTR_FABRIC_PORT_LIST)` が失敗
- `throw runtime_error("FabricPortsOrch get port list failure")` → orchagent 異常終了
- 再試行なし（プロセス再起動に依存）

#### 1c. ポートレーン番号取得失敗

- コード: `fabricportsorch.cpp:206-214`
- `sai_port_api->get_port_attribute(SAI_PORT_ATTR_HW_LANE_LIST)` が失敗
- `throw runtime_error("FabricPortsOrch get port lane failure")` → orchagent 異常終了
- 再試行なし（プロセス再起動に依存）

### 2. `isolateFabricLink()` — SAI isolation 失敗

- コード: `fabricportsorch.cpp:984-1003`
- `sai_port_api->set_port_attribute(SAI_PORT_ATTR_FABRIC_ISOLATE)` が失敗
- `SWSS_LOG_ERROR("Failed to set admin status")` のみ出力
- `task_need_retry` を返さない（エラーをログのみで吸収）
- STATE_DB の `ISOLATED` フィールドは正常パス同様に更新される（STATE_DB と SAI の乖離が発生）

### 3. `doFabricPortTask()` — データ不完全による silent drop

- コード: `fabricportsorch.cpp:1436-1484`
- `alias` / `lanes` / `isolateStatus` のいずれかが欠如し、APPL_DB からの hget でも補完できない場合
- `m_toSync.erase(it)` で消去（`task_success` 扱い）
- エラーログは INFO レベルのみ (`SWSS_LOG_INFO("hget failed")`)
- 再試行なし

### 4. `updateFabricPortState()` — SAI ポート属性取得失敗

- コード: `fabricportsorch.cpp:354-365`
- `sai_port_api->get_port_attribute(SAI_PORT_ATTR_FABRIC_ATTACHED)` が失敗
- `handleSaiGetStatus()` を呼び、`task_success` 以外なら関数全体から `return` (残ポート処理もスキップ)
- STATE_DB 更新なし（古い状態が残る）

### 5. `updateFabricPortState()` — 接続先スイッチ/ポート情報取得失敗

- コード: `fabricportsorch.cpp:378-399`
- `SAI_PORT_ATTR_FABRIC_ATTACHED_SWITCH_ID` or `SAI_PORT_ATTR_FABRIC_ATTACHED_PORT_INDEX` 取得失敗
- `throw runtime_error(...)` → orchagent 異常終了

### 6. `generateQueueStats()` — キュー情報取得失敗

- コード: `fabricportsorch.cpp:277-297`
- `SAI_PORT_ATTR_QOS_NUMBER_OF_QUEUES` or `SAI_PORT_ATTR_QOS_QUEUE_LIST` 取得失敗
- `throw runtime_error(...)` → orchagent 異常終了

## Evidence

`sonic-swss` `orchagent/fabricportsorch.cpp:159-228,277-297,354-414,984-1003,1394-1547`
