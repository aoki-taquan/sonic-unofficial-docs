# DOT1P_TO_TC_MAP 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/dot1p-to-tc-map.md` Phase D `<!-- failure -->` ブロック。

## 調査対象ソース

- `sonic-swss/orchagent/qosorch.cpp` (`Dot1pToTcMapHandler`, `QosMapHandler::processWorkItem`)
- `sonic-swss/orchagent/qosorch.h`

スキャン範囲:
- `QosMapHandler::processWorkItem()` — SET / DEL 共通ディスパッチャ (qosorch.cpp:124-202)
- `Dot1pToTcMapHandler::convertFieldValuesToAttributes()` — フィールド変換 (qosorch.cpp:360-397)
- `Dot1pToTcMapHandler::addQosItem()` — SAI 新規作成 (qosorch.cpp:399-420)
- `QosMapHandler::modifyQosItem()` — SAI 更新 (qosorch.cpp:204-214)
- `QosMapHandler::removeQosItem()` — SAI 削除 (qosorch.cpp:216-227)

---

## SET 失敗パス

### 1. `pending_remove` 中の SET ブロック → `task_need_retry`

既存オブジェクトが `m_pendingRemove == true` の状態で SET が来ると即座に
`task_need_retry` を返す（qosorch.cpp:136-139）。
DEL の pending_remove フラグが解消されるまで、同名エントリへの SET は再試行待ちとなる。

- ログ: `"Entry %s %s is pending remove, need retry"` (SWSS_LOG_NOTICE)
- 効果: `task_need_retry` → m_toSync 残留、次の doTask() サイクルで再評価

### 2. `dot1p` / `tc` フィールド変換失敗 → エントリサイレント脱落

`Dot1pToTcMapHandler::convertFieldValuesToAttributes()` (qosorch.cpp:360-397) は
各エントリを `stoi(fvField(fv))` / `stoi(fvValue(fv))` で変換する。
変換に失敗しても `continue` でスキップするため `convertFieldValuesToAttributes()` は
`return true` を維持する。

- `std::invalid_argument` (非数値文字列): ログ `"Invalid dot1p to tc argument %s:%s to %s()"` (ERROR) → 該当エントリのみ脱落
- `std::out_of_range` (数値が型範囲超過): ログ `"Out of range dot1p to tc argument %s:%s to %s()"` (ERROR) → 該当エントリのみ脱落
- 効果: 呼び出し元 `processWorkItem()` には `true` が返り、残りの有効エントリで SAI マップを生成継続。**CONFIG_DB と SAI の内容が乖離する。**

### 3. SAI `sai_create_qos_map` 失敗 (新規作成) → `task_failed`

`Dot1pToTcMapHandler::addQosItem()` (qosorch.cpp:399-420) が
`sai_qos_map_api->create_qos_map()` を呼び出し、失敗時は `SAI_NULL_OBJECT_ID` を返す。
`processWorkItem()` はこれを受けて `task_failed` を返す。

- ログ: `"Failed to create dot1p_to_tc map. status: %s"` (SWSS_LOG_ERROR, qosorch.cpp:415)
- ログ: `"Failed to create [%s:%s]"` (SWSS_LOG_ERROR, qosorch.cpp:164)
- 効果: `task_failed` → m_toSync からエントリ削除。自動 retry なし。rollback なし。

### 4. SAI `set_qos_map_attribute` 失敗 (既存更新) → `task_failed`

`QosMapHandler::modifyQosItem()` (qosorch.cpp:204-214) が
`sai_qos_map_api->set_qos_map_attribute()` を呼び出し、失敗時は `false` を返す。
`processWorkItem()` はこれを受けて `task_failed` を返す。

- ログ: `"Failed to modify map. status:%d"` (SWSS_LOG_ERROR, qosorch.cpp:211)
- ログ: `"Failed to set [%s:%s]"` (SWSS_LOG_ERROR, qosorch.cpp:153)
- 効果: `task_failed` → m_toSync からエントリ削除。既存 SAI オブジェクトは変更前の状態に留まる（部分更新なし）。

---

## DEL 失敗パス

### 5. 存在しないオブジェクトへの DEL → `task_invalid_entry`

対象名が type_map に存在しない（SAI オブジェクト未作成または既に削除済み）場合、
`processWorkItem()` (qosorch.cpp:176-179) は `task_invalid_entry` を返す。

- ログ: `"Object with name:%s not found."` (SWSS_LOG_ERROR, qosorch.cpp:178)
- 効果: `task_invalid_entry` → m_toSync からエントリ削除。ノーオペレーション。

### 6. `PORT_QOS_MAP` から参照中の DEL → `pending_remove` ロック (`task_need_retry`)

`processWorkItem()` (qosorch.cpp:181-186) は `isObjectBeingReferenced()` で参照確認を行い、
参照中であれば `m_pendingRemove = true` をセットして `task_need_retry` を返す。

- ログ: `"Can't remove object %s due to being referenced (%s)"` (SWSS_LOG_NOTICE, qosorch.cpp:184)
- 効果: `task_need_retry` → m_toSync 残留。`PORT_QOS_MAP` の `dot1p_to_tc_map` フィールドを
  先に削除して参照を解除するまで DEL は実行されない。解除後の次 doTask() で自動 DEL 再実行。

### 7. SAI `remove_qos_map` 失敗 → `task_failed`

`QosMapHandler::removeQosItem()` (qosorch.cpp:216-227) が
`sai_qos_map_api->remove_qos_map()` を呼び出し、失敗時は `false` を返す。
`processWorkItem()` はこれを受けて `task_failed` を返す。

- ログ: `"Failed to remove map, status:%d"` (SWSS_LOG_ERROR, qosorch.cpp:223)
- ログ: `"Failed to remove QoS map. db name:%s sai object:%" PRIx64` (SWSS_LOG_ERROR, qosorch.cpp:190)
- 効果: `task_failed` → m_toSync からエントリ削除。SAI オブジェクトは残存（CONFIG_DB / SAI 乖離）。

---

## retry / recovery メカニズム

| ステータス | 挙動 |
|---|---|
| `task_success` | エントリを m_toSync から削除（完了） |
| `task_need_retry` | エントリを m_toSync に残す。次の doTask() で再処理 |
| `task_invalid_entry` | エントリを m_toSync から削除（永続エラー、syslog のみ） |
| `task_failed` | エントリを m_toSync から削除（永続エラー、syslog のみ） |

QosOrch は失敗時に STATE_DB / ERROR_TABLE への書き込みを行わない。
ASIC_DB への反映確認は `sonic-db-cli ASIC_DB hgetall 'ASIC_STATE:SAI_OBJECT_TYPE_QOS_MAP:*'` が必要。

---

## evidence

- `sonic-swss/orchagent/qosorch.cpp:124-202` (QosMapHandler::processWorkItem)
- `sonic-swss/orchagent/qosorch.cpp:360-397` (Dot1pToTcMapHandler::convertFieldValuesToAttributes)
- `sonic-swss/orchagent/qosorch.cpp:399-420` (Dot1pToTcMapHandler::addQosItem)
- `sonic-swss/orchagent/qosorch.cpp:204-227` (modifyQosItem / removeQosItem)
