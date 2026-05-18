# DOT1P_TO_PG_MAP (2 段マッピング経路) 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/dot1p-to-pg-map.md` Phase D `<!-- failure -->` ブロック。

## 調査対象ソース

- `sonic-swss/orchagent/qosorch.cpp` (`Dot1pToTcMapHandler`, `handlePortQosMapTable`, `handleQosMap`)
- `sonic-swss/orchagent/qosorch.h` (フィールド名定数)

スキャン範囲:
- `Dot1pToTcMapHandler::addQosItem()` / `removeQosItem()` (qosorch.cpp:360-427)
- `QosOrch::handleQosMap()` (qosorch.cpp:100-200 相当)
- `QosOrch::handlePortQosMapTable()` (qosorch.cpp:2046-2156)

---

## DOT1P_TO_PG_MAP 自体への書き込み — 無視

`DOT1P_TO_PG_MAP` テーブルは `m_qos_maps` 初期化リストに登録されていないため、
このキー名で CONFIG_DB に書き込んでも `qosorch` はイベントとして受信せず無視する。
エラーログは発生しない（Consumer 登録がないため通知が届かない）。

---

## DOT1P_TO_TC_MAP 経路の失敗パス

### 1. `dot1p` 値の変換失敗 → `task_failed`

`Dot1pToTcMapHandler::addQosItem()` (qosorch.cpp:360-427) は dot1p 文字列を `stoi()` で変換する。
`stoi()` は例外処理ガードなしで呼ばれるため、非数値文字列が来ると `std::invalid_argument` が
`handleQosMap` の呼び出し元まで伝播し `task_failed` を返す。

- ログ: なし（例外が外側でキャッチされた場合のみスタックログが記録される）
- 効果: `task_failed` → エントリ削除。**retry なし。rollback なし。**

### 2. SAI `sai_qos_map_api->create_qos_map` 失敗 → `task_failed`

`Dot1pToTcMapHandler` が SAI `SAI_QOS_MAP_TYPE_DOT1P_TO_TC` オブジェクト生成に失敗した場合、
`handleSaiCreateStatus()` を経由して `task_failed` または `task_need_retry` が返る。

- ログ: `SWSS_LOG_ERROR` + SAI ステータスコード
- 効果: SAI 種別により retry / 永続失敗に分岐

### 3. DEL 時に PORT_QOS_MAP から参照中 → `pending_remove` ロック (`task_need_retry`)

`handleQosMap()` (qosorch.cpp:181-186 相当):

```cpp
if (isObjectBeingReferenced(...))
{
    m_pendingRemove = true;
    return task_process_status::task_need_retry;
}
```

`PORT_QOS_MAP.<port>.dot1p_to_tc_map` から参照されている間は `DOT1P_TO_TC_MAP` の DEL が
ブロックされる。参照ポートの `dot1p_to_tc_map` フィールドを先に除去する必要がある。

- ログ: なし（`task_need_retry` はログなしで再キュー）
- 効果: 参照解除後の次 doTask() サイクルで DEL が再実行される

### 4. `pending_remove` 中の SET ブロック (`task_need_retry`)

DEL の pending_remove フラグが立っている間に同エントリへの SET が来ると即 `task_need_retry` を返す。
ロールバック・入れ替えシナリオ（旧マップ DEL → 新マップ SET）では、旧マップへの参照を
全ポートから除去するまで SET も実行できない（qosorch.cpp:136-139 相当）。

---

## PORT_QOS_MAP 適用経路の失敗パス

### 5. 存在しないポート名 → スキップ (`task_success`)

`handlePortQosMapTable()` は `gPortsOrch->getPort(port_name, port)` が失敗した場合、
`SWSS_LOG_ERROR "Port with alias: ... not found"` を出力して `continue` でスキップする。
（DSCP 経路の qosorch.cpp:2068 と同一パターン）

- ログ: `SWSS_LOG_ERROR "Port with alias: ... not found"`
- 効果: 対象ポートへの適用はスキップ、エントリ全体は削除（`task_success` 扱い）

### 6. `resolveFieldRefValue` 失敗 → `task_need_retry` または `task_failed`

`dot1p_to_tc_map` / `tc_to_pg_map` フィールドの参照解決:

- `not_resolved`（マップ未作成）: `task_need_retry` → 自動再キュー（上限なし）
- その他内部エラー: `SWSS_LOG_ERROR "Failed to resolve field ..."` → `task_failed`

(evidence: qosorch.cpp:2077-2083, qosorch.cpp:2122-2126)

### 7. SAI `set_port_attribute` 失敗 → `task_failed` (handleSaiSetStatus 依存)

`SAI_PORT_ATTR_QOS_DOT1P_TO_TC_MAP` または `SAI_PORT_ATTR_QOS_TC_TO_PRIORITY_GROUP_MAP` の
set_port_attribute が失敗した場合、`handleSaiSetStatus()` を経由して retry / 永続失敗に分岐する。
複数属性を順番に適用するため、途中で失敗すると**部分適用**が残る可能性がある。

- ログ: `SWSS_LOG_ERROR "Failed to set port attribute: ..."` + SAI エラーコード
- 効果: `task_failed` → エントリ削除。適用済み属性は rollback されない。

---

## retry / recovery メカニズム

| ステータス | 挙動 |
|---|---|
| `task_success` | エントリを `m_toSync` から削除（完了） |
| `task_need_retry` | エントリを `m_toSync` に残す。次の doTask() で再処理 |
| `task_invalid_entry` | エントリを `m_toSync` から削除（永続エラー、syslog のみ） |
| `task_failed` | エントリを `m_toSync` から削除（永続エラー、syslog のみ） |

QosOrch は失敗時に STATE_DB / ERROR_TABLE への書き込みを行わない。
反映状況の確認は `sonic-db-cli ASIC_DB hgetall` が必要。
