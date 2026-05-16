# TC_TO_QUEUE_MAP — Phase B 書込み順依存スキャンノート

対象テーブル: `TC_TO_QUEUE_MAP`
Consumer: `TcToQueueMapHandler::processWorkItem()` / `QosOrch::handlePortQosMapTable()` (`sonic-swss/orchagent/qosorch.cpp`)
スキャン範囲: qosorch.cpp 全行精読（L56-120, L130-200, L430-480, L2112-2135, L2230-2252）

---

## 検出した順序依存・タイミング依存

### 1. TC_TO_QUEUE_MAP は PORT_QOS_MAP より先行必須（ポートバインド）

- `handlePortQosMapTable()` qosorch.cpp:2118-2129: フィールド処理ループで `resolveFieldRefValue()` を呼び、`ref_resolve_status::success` でない場合（対象 `TC_TO_QUEUE_MAP|<name>` の SAI オブジェクトが未作成）、`task_need_retry` を即返す。
- `qos_to_ref_table_map` (qosorch.cpp:103) で `tc_to_queue_field_name → CFG_TC_TO_QUEUE_MAP_TABLE_NAME` が静的にマッピングされており、PORT_QOS_MAP の `tc_to_queue_map` フィールドは必ず `TC_TO_QUEUE_MAP` テーブルを参照する。
- **推奨順序**: `TC_TO_QUEUE_MAP|<name>` を先に書き → 次に `PORT_QOS_MAP|<port> tc_to_queue_map=<name>` で参照する。
- evidence: `qosorch.cpp:2118-2129`

### 2. QosOrch::doTask() が map 系テーブルを PORT_QOS_MAP より先に drain する

- `QosOrch::doTask()` qosorch.cpp:2231-2251: ループで `port_qos_map_cfg_exec` と `queue_exec` をスキップし、他のすべての Consumer（TC_TO_QUEUE_MAP を含む）を先に `drain()` する。その後 `port_qos_map_cfg_exec->drain()` を呼ぶ。
- この drain 順序により、同一 doTask() 呼び出し内に TC_TO_QUEUE_MAP と PORT_QOS_MAP が両方到着した場合でも、TC_TO_QUEUE_MAP の SAI 作成が PORT_QOS_MAP の参照解決より**必ず先行**する。
- evidence: `qosorch.cpp:2231-2251`

### 3. encap_tc_to_queue_field_name でも同一テーブルを参照

- `qos_to_ref_table_map` (qosorch.cpp:116) で `encap_tc_to_queue_field_name → CFG_TC_TO_QUEUE_MAP_TABLE_NAME` もマッピングされている。Tunnel encap 経路でも TC_TO_QUEUE_MAP が先に存在しなければ PORT_QOS_MAP / Tunnel 設定が `task_need_retry` になる。
- evidence: `qosorch.cpp:116`

### 4. DEL 時の参照先確認（pending_remove ロック）

- `processWorkItem()` qosorch.cpp:181-186: DEL コマンド処理時、`isObjectBeingReferenced()` が true（PORT_QOS_MAP から参照中）なら `m_pendingRemove = true` を立てて `task_need_retry` を返す。SAI `remove_qos_map()` は参照が解放されるまで呼ばれない。
- pending_remove 中の SET（再書き込み）も `task_need_retry` で即返却される（qosorch.cpp:136-139）。
- **推奨 DEL 順序**: `PORT_QOS_MAP|<port>` の `tc_to_queue_map` フィールドを先に除去 → 次に `TC_TO_QUEUE_MAP|<name>` を DEL。
- evidence: `qosorch.cpp:136-139`, `181-191`

### 5. SAI map type のハードコードと create の不可分性

- `TcToQueueMapHandler::addQosItem()` qosorch.cpp:457-458: `SAI_QOS_MAP_ATTR_TYPE = SAI_QOS_MAP_TYPE_TC_TO_QUEUE` がハードコードされ、`SAI_QOS_MAP_ATTR_MAP_TO_VALUE_LIST` と同時に `create_qos_map()` で 1 回の SAI 呼び出しで作成される。
- MAP_TO_VALUE_LIST が空（エントリなし）の場合、`tc_map_list.count = 0` のまま SAI に渡されるため、SAI の実装によっては空マップ作成に失敗する可能性がある。
- evidence: `qosorch.cpp:433-469`

### 6. SAI 操作失敗（task_failed）と retry なし

- CREATE / SET / DELETE で SAI エラーが発生した場合 `task_failed` を返し自動 retry は行われない（qosorch.cpp:153-155, 162-170, 188-194）。
- `stoi()` 呼び出しに例外処理なし（qosorch.cpp:440-441）。TC 値または queue_index が整数として解釈できない場合 `std::invalid_argument` → `task_invalid_entry`（エントリキューから除去）。
- evidence: `qosorch.cpp:151-194`, `440-441`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | TC_TO_QUEUE_MAP SAI 作成完了 → PORT_QOS_MAP SET | 強制先行（自動 retry） | task_need_retry で自動再試行 |
| 2 | drain 順序: TC_TO_QUEUE_MAP → PORT_QOS_MAP | 実装固定（doTask ループ順） | 同時投入でも自動的に正順 |
| 3 | TC_TO_QUEUE_MAP 作成 → Tunnel encap SET | 強制先行（自動 retry） | encap_tc_to_queue_field_name も同テーブル参照 |
| 4 | PORT_QOS_MAP 参照解除 → TC_TO_QUEUE_MAP DEL | 強制先行（pending_remove ロック） | 参照ポートの qos_map 設定削除が必要 |
| 5 | 有効な整数文字列（TC/queue_index） → SET 実行 | 必須（非数値は task_invalid_entry） | 例外処理なし、silent drop に注意 |
