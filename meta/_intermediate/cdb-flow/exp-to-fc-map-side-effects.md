# EXP_TO_FC_MAP — Phase F 副作用スキャンノート

対象ページ: `docs/reference/config-db/exp-to-fc-map.md`
対象テーブル: `EXP_TO_FC_MAP`
Consumer: `QosOrch::handleExpToFcTable()` / `QosMapHandler::processWorkItem()` (`orchagent/qosorch.cpp`)
スキャン範囲: `qosorch.cpp:124-201` (QosMapHandler::processWorkItem), `qosorch.cpp:1132-1213` (ExpToFcMapHandler), `qosorch.cpp:2046-2240` (handlePortQosMapTable / doTask), `nhgmaporch.cpp:299-325` (getMaxNumFcs)

---

## 直接副作用

### SET (新規)
- `addQosItem()` → `sai_qos_map_api->create_qos_map()` で SAI QoS map オブジェクト (`SAI_QOS_MAP_TYPE_MPLS_EXP_TO_FORWARDING_CLASS`) を生成。
- 生成 OID を `getTypeMap()[CFG_EXP_TO_FC_MAP_TABLE_NAME][<name>].m_saiObjectId` に格納 (`qosorch.cpp:168`)。
- `m_pendingRemove = false` にリセット (`qosorch.cpp:169`)。

### SET (既存 — 上書き)
- `modifyQosItem()` → `sai_qos_map_api->set_qos_map_attribute()` で既存 SAI map を in-place 更新。
- **現在そのマップを参照しているポートの MPLS EXP→FC 分類が即座に変更される**（SAI 経由で ASIC に伝播）。PORT_QOS_MAP の再操作は不要。

### DEL (参照なし)
- `removeQosItem()` → `sai_qos_map_api->remove_qos_map()` で SAI map 削除。
- `getTypeMap()` からエントリを erase (`qosorch.cpp:194`)。
- 以降 `PORT_QOS_MAP.exp_to_fc_map` でこの名前を解決しようとすると `task_need_retry` が発生する。

### DEL (参照あり)
- `isObjectBeingReferenced()` が真 → `m_pendingRemove = true` + `task_need_retry` を返す (`qosorch.cpp:185-186`)。
- SAI map はまだ削除されない。PORT_QOS_MAP 参照解除後の次サイクルで再実行。
- `m_pendingRemove = true` の期間中、同名への SET は即 `task_need_retry` (`qosorch.cpp:136-139`)。

---

## PORT_QOS_MAP 経由の間接副作用

`EXP_TO_FC_MAP` エントリ作成後に `PORT_QOS_MAP.exp_to_fc_map` を SET すると、
`handlePortQosMapTable()` 内の `resolveFieldRefValue()` が OID 解決成功 →
`sai_port_api->set_port_attribute(port_id, SAI_PORT_ATTR_QOS_MPLS_EXP_TO_FORWARDING_CLASS_MAP, oid)` でポートへ適用される。

MAP 削除 (DEL) の場合、PORT_QOS_MAP 参照解除後に orchagent の次サイクルで自動的に
`set_port_attribute(..., SAI_NULL_OBJECT_ID)` が呼ばれてポートのマッピングが解除される。

---

## 書き込みなし・通知なし の確認

| 確認対象 | 結果 | 根拠 |
|---------|------|------|
| STATE_DB への書き込み | **なし** | `handleExpToFcTable` は STATE_DB を参照・書込みしない |
| APPL_DB への書き込み | **なし** | CONFIG_DB → SAI 直結。APPL_DB 中継なし |
| FLEX_COUNTER 更新 | **なし** | EXP_TO_FC MAP オブジェクトは flex counter 対象外 |
| ERROR_TABLE への書き込み | **なし** | エラーは syslog のみ |
| channel_ready / pub-sub 通知 | **なし** | Notification なし |

---

## 副作用サマリ

| 副作用 | トリガー | ソース |
|--------|---------|--------|
| SAI QoS map 生成 (`SAI_QOS_MAP_TYPE_MPLS_EXP_TO_FORWARDING_CLASS`) | SET 新規 | `qosorch.cpp:1189-1213` |
| SAI QoS map 属性更新 (`set_qos_map_attribute`) | SET 既存 | `qosorch.cpp:204-214` |
| 参照ポートの MPLS EXP→FC 分類の即時変更 | SET 既存（in-place 更新）| `qosorch.cpp:151-157`, ASIC 経由 |
| SAI QoS map 削除 (`remove_qos_map`) | DEL かつ参照なし | `qosorch.cpp:188-194` |
| `getTypeMap()` OID 登録 | SET 新規成功 | `qosorch.cpp:168` |
| `getTypeMap()` エントリ erase | DEL 成功 | `qosorch.cpp:194` |
| `m_pendingRemove = true` — 後続 SET も `task_need_retry` 化 | DEL 時に PORT_QOS_MAP 参照あり | `qosorch.cpp:185` |
| ポートへの `SAI_PORT_ATTR_QOS_MPLS_EXP_TO_FORWARDING_CLASS_MAP` 適用 | PORT_QOS_MAP SET 後 | `qosorch.cpp:2124-2133`, `qosorch.cpp:2193-2200` |

---

## ページ反映方針

- `<!-- side-effects -->` ブロックを `<!-- /constants -->` の直後に追加する。
- pfc-priority-to-priority-group-map の side-effects ブロックと同構造で記述。
- EXP_TO_FC_MAP 固有のポイント: in-place 更新時に参照ポートの ASIC 分類が即時変更される点を明記。
