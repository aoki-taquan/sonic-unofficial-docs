# DSCP_TO_FC_MAP — Phase D 失敗挙動スキャンノート

対象ページ: `docs/reference/config-db/dscp-to-fc-map.md`
対象テーブル: `CONFIG_DB DSCP_TO_FC_MAP`
Producer/Consumer: `qosorch` (`QosOrch` / `DscpToFcMapHandler`)
スキャン範囲: `QosMapHandler::processWorkItem()` (qosorch.cpp:124-210); `DscpToFcMapHandler::convertFieldValuesToAttributes()` (qosorch.cpp:1039-1094); `DscpToFcMapHandler::addQosItem()` (qosorch.cpp:1095-1124)

---

## SET 時の失敗パターン

### 1. DSCP 値バリデーション失敗 → `task_invalid_entry`

- 負値 (`value < 0`): `SWSS_LOG_ERROR("DSCP value %d is negative", value)` → `delete[]` → `return false` → `task_invalid_entry`
- 64 以上 (`value > DSCP_MAX_VAL`): `SWSS_LOG_ERROR("DSCP value %d is greater than max value %d", value, DSCP_MAX_VAL)` → `delete[]` → `return false` → `task_invalid_entry`
- 非整数文字列: `stoi` が `std::invalid_argument` を throw → catch ブロック内で `SWSS_LOG_ERROR` + `delete[]` → `return false` → `task_invalid_entry`
- evidence: `qosorch.cpp:1057-1069`

### 2. FC 値バリデーション失敗 → `task_invalid_entry`

- 負値または `max_num_fcs` 以上 (`(value < 0) || (value >= max_num_fcs)`): `SWSS_LOG_ERROR` → `delete[]` → `return false` → `task_invalid_entry`
- FC 非対応スイッチ (`max_num_fcs = 0`): 条件 `value >= 0` が常に真 → **全 FC 値が reject**。SAI map 未作成。エラーログのみ、orchagent は継続動作
- 非整数文字列: `stoi` で `std::invalid_argument` catch → 同上
- evidence: `qosorch.cpp:1072-1082`, `nhgmaporch.cpp:299-325`

### 3. SAI create 失敗 → `task_failed`

- `addQosItem()` が `SAI_NULL_OBJECT_ID` を返した場合: `SWSS_LOG_ERROR("Failed to create [%s:%s]", ...)` → `task_failed`
- `sai_qos_map_api->create_qos_map()` が `SAI_STATUS_SUCCESS` 以外: `SWSS_LOG_ERROR("Failed to create dscp_to_fc map. status:%d", sai_status)` → `return SAI_NULL_OBJECT_ID`
- **retry**: `task_failed` はフレームワークによりエントリが `m_toSync` から erase される（無限 retry しない）
- evidence: `qosorch.cpp:1115-1120`, `qosorch.cpp:157-164`

### 4. SAI modify 失敗 → `task_failed`

- 既存マップの属性更新 (`modifyQosItem()`) が失敗: `SWSS_LOG_ERROR("Failed to set [%s:%s]", ...)` → `task_failed`
- `task_failed` → erase（無限 retry しない）
- evidence: `qosorch.cpp:151-158`

### 5. `m_pendingRemove` 中に SET → `task_need_retry`

- `PORT_QOS_MAP` から参照中の状態で DEL が来て `m_pendingRemove = true` になっている間に SET が来た場合: `SWSS_LOG_NOTICE("Entry %s %s is pending remove, need retry", ...)` → `task_need_retry`
- これは `task_need_retry` であるためエントリは `m_toSync` に残り、次のサイクルで再評価される
- evidence: `qosorch.cpp:135-140`

## DEL 時の失敗パターン

### 6. 存在しないオブジェクトへの DEL → `task_invalid_entry`

- `sai_object == SAI_NULL_OBJECT_ID`（内部マップに未登録）の場合: `SWSS_LOG_ERROR("Object with name:%s not found.", ...)` → `task_invalid_entry`
- evidence: `qosorch.cpp:177-180`

### 7. 参照中オブジェクトへの DEL → `task_need_retry` + `m_pendingRemove`

- `isObjectBeingReferenced()` が true（`PORT_QOS_MAP` の `dscp_to_fc_map` フィールドから参照中）: `m_pendingRemove = true` → `task_need_retry`
- CONFIG_DB から DEL しても SAI 側の remove は行われない。`PORT_QOS_MAP` の参照解除後の次サイクルで自動実行
- evidence: `qosorch.cpp:181-187`

### 8. SAI remove 失敗 → `task_failed`

- `removeQosItem()` が false を返した場合: `SWSS_LOG_ERROR("Failed to remove QoS map. db name:%s sai object:%" PRIx64, ...)` → `task_failed`
- `task_failed` → erase（内部マップからの削除は行われない可能性あり）
- evidence: `qosorch.cpp:188-193`

---

## 失敗時のログ出力先・確認方法

- すべての失敗は `SWSS_LOG_ERROR` または `SWSS_LOG_NOTICE` で `/var/log/syslog` および `orchagent.log` に出力
- `ERROR_TABLE` への書き込みはなし
- STATE_DB へのステータス記録はなし（`DSCP_TO_FC_MAP` は CONFIG_DB → SAI 直行経路で STATE_DB を介さない）
- CONFIG_DB のエントリは失敗後も残る（orchagent は書き戻さない）

### 確認コマンド

```bash
# SAI map 作成確認
sonic-db-cli CONFIG_DB hgetall 'DSCP_TO_FC_MAP|AZURE'

# orchagent ログ確認
grep -i "dscp_to_fc\|dscp.*fc" /var/log/swss/orchagent.log | tail -20
```

---

## 失敗パターンサマリ

| # | 操作 | 失敗ケース | task_status | retry | ログ |
|---|------|-----------|-------------|-------|------|
| 1 | SET | DSCP 値 <0 または >63 | `task_invalid_entry` | なし（erase） | `SWSS_LOG_ERROR` |
| 2 | SET | FC 値が範囲外 / FC 非対応 ASIC | `task_invalid_entry` | なし（erase） | `SWSS_LOG_ERROR` |
| 3 | SET | 非整数文字列（dscp or fc フィールド） | `task_invalid_entry` | なし（erase） | `SWSS_LOG_ERROR` |
| 4 | SET | SAI create 失敗 | `task_failed` | なし（erase） | `SWSS_LOG_ERROR` |
| 5 | SET | SAI modify 失敗 | `task_failed` | なし（erase） | `SWSS_LOG_ERROR` |
| 6 | SET | `m_pendingRemove` 中 | `task_need_retry` | あり（無制限） | `SWSS_LOG_NOTICE` |
| 7 | DEL | 未登録オブジェクト | `task_invalid_entry` | なし（erase） | `SWSS_LOG_ERROR` |
| 8 | DEL | `PORT_QOS_MAP` 参照中 | `task_need_retry` + `m_pendingRemove=true` | あり（参照解除まで） | `SWSS_LOG_NOTICE` |
| 9 | DEL | SAI remove 失敗 | `task_failed` | なし（erase） | `SWSS_LOG_ERROR` |

---

## ページ反映方針

- `<!-- failure -->` ブロックを `<!-- cross-refs -->` ... `<!-- /cross-refs -->` の直後（`<!-- defaults -->` の直前）に挿入する。
- サマリ表 + 各パターンの散文を含める。
- 既存ブロック (`<!-- ordering -->`, `<!-- cross-refs -->`, `<!-- defaults -->`) は触らない。
