# Phase F: 副作用 — PFC_PRIORITY_TO_PRIORITY_GROUP_MAP

調査対象: `sonic-swss/orchagent/qosorch.cpp`  
調査日: 2026-05-16

## 調査方法

`QosOrch::handlePfcPrioToPgTable` → `PfcPrioToPgHandler::processWorkItem` を起点に
呼び出しグラフを追跡し、CONFIG_DB 書き込み以外で生じる状態変化を列挙した。

---

## 直接副作用 (MAP SET/DEL 時)

| 副作用 | トリガー | ソース |
|--------|---------|--------|
| SAI QoS map オブジェクト生成 (`SAI_QOS_MAP_TYPE_PFC_PRIORITY_TO_PRIORITY_GROUP`) | SET (新規) | `qosorch.cpp:974` |
| SAI QoS map 属性更新 (`set_qos_map_attribute`) | SET (既存) | `qosorch.cpp:153` |
| SAI QoS map 削除 (`remove_qos_map`) | DEL かつ参照なし | `qosorch.cpp:190` |
| `getTypeMap()[CFG_PFC_PRIORITY_TO_PRIORITY_GROUP_MAP_TABLE_NAME]` への OID 登録 | SET 新規成功 | `qosorch.cpp:168` |
| 同上エントリの erase | DEL 成功 | `qosorch.cpp:194` |
| `m_pendingRemove = true` — 後続 SET を `task_need_retry` に | DEL 時に参照が残っている | `qosorch.cpp:185` |

- **STATE_DB への書き込みなし** — `QosOrch` は PFC_PRIORITY_TO_PRIORITY_GROUP_MAP の処理で STATE_DB / APPL_DB へ書き込まない。
- **APPL_DB への書き込みなし** — APP_DB 側の `PFC_PRIORITY_TO_PRIORITY_GROUP_MAP_TABLE` は schema.h に定数があるが、master の orchagent は CONFIG_DB → SAI 直結であり APPL_DB 経由しない。

---

## 間接副作用 (PORT_QOS_MAP 経由)

`PFC_PRIORITY_TO_PRIORITY_GROUP_MAP` の MAP OID が解決されると、
`PORT_QOS_MAP` の `handlePortQosMapTable` ハンドラが以下を実行する:

| 副作用 | API | ソース |
|--------|-----|--------|
| ポートへの `SAI_PORT_ATTR_QOS_PFC_PRIORITY_TO_PRIORITY_GROUP_MAP` 適用 | `sai_port_api->set_port_attribute()` | `qosorch.cpp:2086,2193` |
| PFC enable bitmask の更新 (`setPortPfc`) | `gPortsOrch->setPortPfc()` | `qosorch.cpp:2215` |
| PFC watchdog ステータス更新 | `gPortsOrch->setPortPfcWatchdogStatus()` | `qosorch.cpp:2224` |

これらは `PORT_QOS_MAP` の SET/DEL 時に実行されるが、
`PFC_PRIORITY_TO_PRIORITY_GROUP_MAP` の OID 未解決中は `task_need_retry`
で保留され、MAP 作成後に自動再処理される (qosorch.cpp:2124–2129)。

---

## m_pendingRemove 連鎖の副作用

DEL 試行時に `PORT_QOS_MAP` 等から参照が残っている場合:

1. `m_pendingRemove = true` がセット (qosorch.cpp:185)
2. 以後この MAP 名への SET 操作が即 `task_need_retry` を返す (qosorch.cpp:136-139)
3. 参照側 (`PORT_QOS_MAP`) が pfc_to_pg_map フィールドを削除/変更して参照解除されるまで保留継続
4. 参照解除後の doTask() サイクルで DEL が再実行されてエントリ erase・SAI 削除が完了

---

## SWSS_LOG 出力 (副作用として観測可能なもの)

| ログレベル | メッセージ | 条件 |
|-----------|-----------|------|
| NOTICE | `"Created [%s:%s]"` | SAI QoS map 新規作成成功 |
| NOTICE | `"Set [%s:%s]"` | SAI QoS map 更新成功 |
| NOTICE | `"Can't remove object %s due to being referenced (%s)"` | DEL 時参照あり → m_pendingRemove |
| NOTICE | `"Entry %s %s is pending remove, need retry"` | m_pendingRemove 中に SET 再試行 |
| ERROR | `"Failed to create pfc_priority_to_queue map. status:%d"` | SAI create 失敗 (ログ文字列が誤記) |
| ERROR | `"Failed to remove QoS map. db name:%s sai object:%"` PRIx64 | SAI remove 失敗 |

---

## グレップカバレッジ

| パターン | hit 数 | 証跡 |
|---------|--------|------|
| `m_pendingRemove` | 6 | `qosorch.cpp:136,169,185,1366,1473,1487` |
| `setPortPfcWatchdogStatus` | 1 | `qosorch.cpp:2224` |
| `STATE_DB` / `stateTable` | 0 | STATE_DB 書き込みなし確認 |
| `APPL_DB` 書き込み | 0 | APPL_DB 書き込みなし確認 |
