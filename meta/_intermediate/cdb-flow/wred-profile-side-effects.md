# WRED_PROFILE — 副次 DB 書込 分析 (Phase F)

ソース: `sonic-swss/orchagent/qosorch.cpp`

## 概要

`QosOrch` は CONFIG_DB の `WRED_PROFILE` テーブルを購読し、SAI WRED オブジェクトの作成・更新・削除を行う。
副次 DB 書込として ASIC_DB への SAI オブジェクト登録と、QUEUE への `SAI_QUEUE_ATTR_WRED_PROFILE_ID` bind の 2 経路が存在する。
STATE_DB / COUNTERS_DB / FLEX_COUNTER_DB への直接書込はなし。

---

## ASIC_DB 書込み (SAI/syncd 経由)

`sai_wred_api` および `sai_queue_api` 呼び出し結果を syncd が ASIC_DB へ反映する。

| タイミング | SAI API | ASIC_DB への反映 |
|---|---|---|
| SET → `addQosItem()` 成功 (新規) | `sai_wred_api->create_wred(&sai_object, gSwitchId, ...)` | `ASIC_STATE:SAI_OBJECT_TYPE_WRED:<oid>` 生成 |
| SET → `modifyQosItem()` (既存更新) | `sai_wred_api->set_wred_attribute(sai_object, &attr)` | `ASIC_STATE:SAI_OBJECT_TYPE_WRED:<oid>` フィールド更新 |
| DEL → `removeQosItem()` | `sai_wred_api->remove_wred(sai_object)` | `ASIC_STATE:SAI_OBJECT_TYPE_WRED:<oid>` 削除 |
| QUEUE への bind (`applyWredProfileToQueue()`) | `sai_queue_api->set_queue_attribute(queue_id, SAI_QUEUE_ATTR_WRED_PROFILE_ID)` | `ASIC_STATE:SAI_OBJECT_TYPE_QUEUE:<queue_oid>` の `SAI_QUEUE_ATTR_WRED_PROFILE_ID` 更新 |
| QUEUE からの unbind (DEL or `wred_profile` 除去) | `sai_queue_api->set_queue_attribute(queue_id, SAI_QUEUE_ATTR_WRED_PROFILE_ID=SAI_NULL_OBJECT_ID)` | 同上フィールドを `NULL` に更新 |

証跡:
- `create_wred()` → `qosorch.cpp:855`
- `set_wred_attribute()` → `qosorch.cpp:774`
- `remove_wred()` → `qosorch.cpp:868`
- `set_queue_attribute(SAI_QUEUE_ATTR_WRED_PROFILE_ID)` → `qosorch.cpp:1735-1738`

### VoQ スイッチ分岐

`gMySwitchType == "voq"` の場合、`applyWredProfileToQueue()` は `gPortsOrch->getPortVoQIds(port)` で取得した VoQ の queue_id を使用する。物理キューではなく VoQ に `SAI_QUEUE_ATTR_WRED_PROFILE_ID` を設定する点が異なる（`qosorch.cpp:1709-1730`）。

---

## STATE_DB 書込み

なし。`QosOrch` / `WredMapHandler` は `STATE_DB` に書き込まない。

---

## COUNTERS_DB / FLEX_COUNTER_DB 書込み

なし。WRED オブジェクトは FlexCounter 対象外。CRM カウンタ更新もなし。

---

## QUEUE への副次 bind まとめ

WRED_PROFILE の SAI オブジェクト作成後、`QUEUE` テーブルで `wred_profile` フィールドが設定されている場合に限り、`applyWredProfileToQueue()` が `sai_queue_api->set_queue_attribute(SAI_QUEUE_ATTR_WRED_PROFILE_ID)` を呼び出してキューに紐付ける。

- **bind トリガー**: `handleQueueTable()` の SET パス (`qosorch.cpp:1936`)
- **unbind トリガー**: `handleQueueTable()` の DEL パス、または `QUEUE.wred_profile` フィールド削除 (`qosorch.cpp:1893`)
- **未解決時**: `task_need_retry` → WRED_PROFILE 作成後に自動再処理 (`qosorch.cpp:1869`)
- **参照カウント管理**: `setObjectReference()` / `removeMeFromObjsReferencedByMe()` で orchagent 内部マップを更新 (`qosorch.cpp:1876, 1886`)

確認コマンド:

```bash
# WRED SAI オブジェクト確認
sonic-db-cli ASIC_DB keys 'ASIC_STATE:SAI_OBJECT_TYPE_WRED:*'

# キューへの bind 確認
sonic-db-cli ASIC_DB hget 'ASIC_STATE:SAI_OBJECT_TYPE_QUEUE:<queue_oid>' SAI_QUEUE_ATTR_WRED_PROFILE_ID
```

---

## スキーマまとめ

| DB | テーブル / オブジェクト型 | 書込元 | 証跡 |
|---|---|---|---|
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_WRED` | `WredMapHandler::addQosItem()` / `modifyQosItem()` / `removeQosItem()` | `qosorch.cpp:855, 774, 868` |
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_QUEUE` (SAI_QUEUE_ATTR_WRED_PROFILE_ID) | `QosOrch::applyWredProfileToQueue()` | `qosorch.cpp:1735-1738` |
| STATE_DB | — (書込なし) | — | — |
| COUNTERS_DB | — (書込なし) | — | — |
| FLEX_COUNTER_DB | — (書込なし) | — | — |
