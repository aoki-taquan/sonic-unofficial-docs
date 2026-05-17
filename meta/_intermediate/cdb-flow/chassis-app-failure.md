# CHASSIS_APP_DB — Phase D 失敗挙動スキャンノート

対象テーブル群: `SYSTEM_INTERFACE`, `SYSTEM_NEIGH`, `SYSTEM_LAG_TABLE`, `SYSTEM_LAG_MEMBER_TABLE`, `BGP_DEVICE_GLOBAL|STATE`
Consumer: `intfsorch`, `neighorch`, `portsorch` (orchagent), `bgpcfgd` (ChassisAppDbMgr)
スキャン範囲: `orchagent/intfsorch.cpp`, `orchagent/neighorch.cpp`, `orchagent/portsorch.cpp`, `orchagent/lagids.lua`, `bgpcfgd/managers_chassis_app_db.py`, `bgpcfgd/managers_device_global.py`

---

## 検出した失敗挙動

### 1. CHASSIS_APP_DB 未使用環境での全 voqSync* 呼び出しサイレントスキップ

- `gMultiAsicVoq == false` の場合、`voqSyncAddIntf()` / `voqSyncDelIntf()` / `voqSyncAddNeigh()` / `voqSyncDelNeigh()` / `voqSyncAddLag()` / `voqSyncDelLag()` / `voqSyncAddLagMember()` / `voqSyncDelLagMember()` はすべて即時 `return` する（エラーログなし）。
- 条件: `DEVICE_METADATA.localhost.switch_type != "voq"` または `/etc/sonic/database_config.json` に `CHASSIS_APP_DB` キーが存在しない
- 結果: CHASSIS_APP_DB への書き込みが一切行われない（silent skip）。エラーログ・アラートなし。
- Evidence: `main.cpp:725-730`, `intfsorch.cpp:1673-1675`

### 2. SYSTEM_INTERFACE: getPort() 失敗 → static skip（リトライなし）

- `voqSyncAddIntf()` 内で `gPortsOrch->getPort(alias, port)` が失敗した場合（ポートが `m_portList` に未登録）。
- 結果: `SWSS_LOG_ERROR("Port does not exist for %s!", alias.c_str())` を出力して即 `return`。task_need_retry を返さないため**永続的に書き込まれない**。
- 発生条件: PortInitDone 受信前にインタフェース追加イベントが到達した場合。
- Evidence: `intfsorch.cpp:1676-1681`

### 3. SYSTEM_NEIGH: encap_index == 0 → 書き込みスキップ + エラーログ

- `voqSyncAddNeigh()` 内で SAI `get_neighbor_entry_attribute(SAI_NEIGHBOR_ENTRY_ATTR_ENCAP_INDEX)` が失敗した場合。
  - SAI API 失敗: `SWSS_LOG_ERROR("Failed to get neighbor attribute for %s on %s, rv:%d", ...)` を出力して `return`。
  - `encap_index == 0`（無効値）: `SWSS_LOG_ERROR("Invalid neighbor encap_index for %s on %s", ...)` を出力して `return`。
- 結果: `SYSTEM_NEIGH` エントリが書き込まれない。task_need_retry を返さないため**リトライなし**。
- Evidence: `neighorch.cpp:2598-2612`

### 4. SYSTEM_LAG_TABLE: LAG ID フリーリスト枯渇 → addLag 失敗

- `LagIdAllocator::lagIdAdd()` が CHASSIS_APP_DB の Lua スクリプト (`lagids.lua`) を呼び出す。フリーリスト (`SYSTEM_LAG_IDS_FREE_LIST`) が空の場合、Lua スクリプトは `-1`（`LAG_ID_ALLOCATOR_ERROR_TABLE_FULL`）を返す。
- 結果: `portsorch.cpp:7981` で `SWSS_LOG_ERROR("Failed to allocate unique LAG id for local lag %s rv:%d", lag_alias.c_str(), spa_id)` を出力し、LAG 作成処理が中断される。SYSTEM_LAG_TABLE への書き込みは行われない。
- 発生条件: LAG ID 割り当て範囲（`SYSTEM_LAG_ID_START` ～ `SYSTEM_LAG_ID_END`）を超える LAG 数が作成された場合。`SYSTEM_LAG_ID_START`/`SYSTEM_LAG_ID_END` が未初期化（`redis.call("get", "SYSTEM_LAG_ID_START")` が nil）の場合も Lua エラーになる可能性がある。
- Evidence: `lagids.lua:60-62`, `portsorch.cpp:7977-7981`

### 5. SYSTEM_LAG_TABLE: SYSTEM_LAG_ID_START/END 未初期化 → Lua エラー

- `lagids.lua:15-16` で `tonumber(redis.call("get", "SYSTEM_LAG_ID_START"))` が `nil` を返す場合、Lua の `tonumber(nil)` は `nil` を返し、以降の数値比較で Lua エラーが発生する。
- 初期化スクリプト（orchagent 起動前に実行される外部スクリプト）がこれらの key を書き込む想定だが、スクリプトが実行されていない場合は LAG ID 割り当てが全て失敗する。
- Evidence: `lagids.lua:15-16`

### 6. BGP_DEVICE_GLOBAL|STATE: data が None の場合は set_handler が False を返す

- `ChassisAppDbMgr.set_handler(key, data)` が `data is None` の場合: `log_err("ChassisAppDbMgr:: data is None")` を出力し `return False`（再試行要求）。
- 発生条件: CHASSIS_APP_DB から `BGP_DEVICE_GLOBAL|STATE` イベントが届くが、フィールド値が空の場合。
- Evidence: `managers_chassis_app_db.py:36-38`

### 7. BGP_DEVICE_GLOBAL|STATE: tsa_enabled フィールドなし → set_handler が False を返す

- `data` dict に `"tsa_enabled"` キーが存在しない場合: `return False`（再試行要求）。実際には CHASSIS_APP_DB の `BGP_DEVICE_GLOBAL|STATE` エントリは `tsa_enabled` のみを持つため、このケースは通常発生しない。
- Evidence: `managers_chassis_app_db.py:40-46`

### 8. CHASSIS_APP_DB 接続失敗 (get_chassis_tsa_status)

- `managers_device_global.py` の `get_chassis_tsa_status()` は `SonicV2Connector` で CHASSIS_APP_DB に接続し `BGP_DEVICE_GLOBAL|STATE.tsa_enabled` を取得する。
- 接続失敗または例外発生時: `log_err("Got an exception {}".format(e))` を出力し `chassis_tsa_status = "false"` を返す（fallback）。
- 発生条件: `redis_chassis.server:6380` に接続できない（VoQ チャシスでない環境等）。
- Evidence: `managers_device_global.py:244-249`

### 9. SYSTEM_INTERFACE: リモートポート / 異なる switch_id の LAG → silent skip

- `voqSyncAddIntf()` でポートが `SAI_SYSTEM_PORT_TYPE_REMOTE` の場合、エラーログなしで `return`。
- LAG ポートで `m_system_lag_info.switch_id != gVoqMySwitchId` の場合もエラーログなしで `return`。
- 結果: リモートポート・リモート LAG のインタフェースは SYSTEM_INTERFACE に書き込まれない（設計通り、失敗ではない）。ただしデバッグ時に書き込みがスキップされているように見える点に注意。
- Evidence: `intfsorch.cpp:1689-1692`, `neighorch.cpp:2624-2627`

---

## 失敗挙動サマリ

| # | 失敗条件 | 検出箇所 | 結果 | ログ出力 |
|---|---------|----------|------|---------|
| 1 | `gMultiAsicVoq == false` | 全 voqSync* 関数 | 書き込み全スキップ（silent） | なし |
| 2 | `getPort()` 失敗（PortInitDone 前） | `intfsorch.cpp:1676-1681` | SYSTEM_INTERFACE 書き込みスキップ（リトライなし） | LOG_ERROR "Port does not exist for %s!" |
| 3 | SAI `encap_index` 取得失敗または `== 0` | `neighorch.cpp:2598-2612` | SYSTEM_NEIGH 書き込みスキップ（リトライなし） | LOG_ERROR |
| 4 | LAG ID フリーリスト枯渇 | `lagids.lua:60-62`, `portsorch.cpp:7977-7981` | LAG 作成中断、SYSTEM_LAG_TABLE 書き込みなし | LOG_ERROR "Failed to allocate unique LAG id..." |
| 5 | `SYSTEM_LAG_ID_START`/`END` 未初期化 | `lagids.lua:15-16` | Lua 数値演算エラー → LAG ID 割り当て失敗 | Redis Lua エラー |
| 6 | `data is None` | `managers_chassis_app_db.py:36-38` | `set_handler` が False を返す | log_err "data is None" |
| 7 | `tsa_enabled` キー不在 | `managers_chassis_app_db.py:40-46` | `set_handler` が False を返す | なし |
| 8 | CHASSIS_APP_DB 接続失敗 | `managers_device_global.py:244-249` | fallback `"false"` を返す | log_err "Got an exception {}" |
| 9 | リモートポート / 異なる switch_id LAG | `intfsorch.cpp`, `neighorch.cpp` | silent skip（設計通り） | なし |
