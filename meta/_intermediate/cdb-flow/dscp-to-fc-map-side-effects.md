# DSCP_TO_FC_MAP — Phase F 副作用スキャンノート

対象テーブル: `DSCP_TO_FC_MAP`
Consumer: `QosOrch::handleDscpToFcTable()` / `QosMapHandler::processWorkItem()` (`sonic-swss/orchagent/qosorch.cpp`)
スキャン範囲: `qosorch.cpp` 全行精読; `nhgmaporch.cpp:299-325`

---

## 副作用分類

### 1. SAI QoS map オブジェクトへの直接副作用

| 副作用 | トリガー | コード箇所 |
|--------|---------|-----------|
| `sai_qos_map_api->create_qos_map()` で SAI オブジェクト生成 (`SAI_QOS_MAP_TYPE_DSCP_TO_FORWARDING_CLASS`) | SET (新規) | `DscpToFcMapHandler::addQosItem()` qosorch.cpp:1112-1115 |
| `sai_qos_map_api->set_qos_map_attribute()` で属性更新 | SET (既存) | `QosMapHandler::modifyQosItem()` qosorch.cpp:207 |
| `sai_qos_map_api->remove_qos_map()` で SAI オブジェクト削除 | DEL かつ参照なし | `QosMapHandler::removeQosItem()` qosorch.cpp:212-220 |
| `getTypeMap()[CFG_DSCP_TO_FC_MAP_TABLE_NAME]` へ OID 登録 | SET 新規成功 | `qosorch.cpp:168` |
| 同上マップエントリの erase | DEL 成功 | `qosorch.cpp:194` |
| `m_pendingRemove = true` — 後続 SET を `task_need_retry` に | DEL 時に参照が残っている | `qosorch.cpp:185` |

- **STATE_DB への書き込みなし** — `QosOrch` は `DSCP_TO_FC_MAP` 処理で STATE_DB / APPL_DB に書き込まない。CONFIG_DB → SAI 直結。
- **APPL_DB への書き込みなし** — master の `orchagent` は `DSCP_TO_FC_MAP` 処理で APPL_DB を操作しない。

### 2. PORT_QOS_MAP 経由の間接副作用

`DSCP_TO_FC_MAP` の SAI OID が解決された後、`PORT_QOS_MAP.dscp_to_fc_map` を参照しているポートエントリが自動再処理（`task_need_retry` → 次サイクルで再実行）される:

| 副作用 | SAI API | コード箇所 |
|--------|---------|-----------|
| ポートへの `SAI_PORT_ATTR_QOS_DSCP_TO_FORWARDING_CLASS_MAP` 適用 | `sai_port_api->set_port_attribute()` | `qosorch.cpp:2193` |

MAP が未作成の間は `PORT_QOS_MAP` 処理が `task_need_retry` で保留され (`qosorch.cpp:2124-2129`)、MAP 作成完了後の `doTask()` サイクルで自動再処理される。

**PFC 関連副作用はなし**: `dscp_to_fc_map` は CBF（Class-Based Forwarding）用途であり、PFC enable bitmask (`SAI_PORT_ATTR_PRIORITY_FLOW_CONTROL`) や PFC watchdog の更新は行わない。これは `pfc_to_pg_map` / `pfc_to_queue_map` 等と対照的な点。`handlePortQosMapTable` 内で pfc_enable 更新は `pfc_enable_name` フィールドのみで条件発火する (`qosorch.cpp:2136-2156`)。

### 3. m_pendingRemove 連鎖副作用

DEL 試行時に `PORT_QOS_MAP` からの参照が残っている場合:

1. `m_pendingRemove = true` がセット (`qosorch.cpp:185`)
2. 以後この MAP 名への SET 操作も即 `task_need_retry` を返す (`qosorch.cpp:136-139`)
3. 参照側 (`PORT_QOS_MAP.dscp_to_fc_map`) の解除後に次サイクルで DEL が再実行され連鎖解消

### 4. NhgMapOrch::getMaxNumFcs() の静的キャッシュ副作用

- SET 処理中に `NhgMapOrch::getMaxNumFcs()` を呼び出す (`nhgmaporch.cpp:299-325`)
- 初回呼び出し時のみ SAI query (`SAI_SWITCH_ATTR_MAX_NUMBER_OF_FORWARDING_CLASSES`) を発行し static 変数にキャッシュ
- 副作用: orchagent 再起動まで ASIC の FC capability 変化が反映されない（実運用上問題なし）

---

## 副作用サマリ

| # | 副作用 | スコープ | 備考 |
|---|--------|---------|------|
| 1 | SAI QoS map 生成 / 更新 / 削除 | ASIC | 新規/既存で API が異なる |
| 2 | PORT_QOS_MAP ポートへの SAI_PORT_ATTR_QOS_DSCP_TO_FORWARDING_CLASS_MAP バインド | ASIC ポート | MAP 作成後の次サイクルで自動発火 |
| 3 | m_pendingRemove 連鎖（後続 SET ブロック） | orchagent 内部状態 | 参照解除で解消 |
| 4 | getMaxNumFcs() static キャッシュ更新（初回のみ） | orchagent 内部状態 | 再起動まで固定 |
| 5 | STATE_DB / APPL_DB への書き込み | なし | CONFIG_DB → SAI 直結 |
