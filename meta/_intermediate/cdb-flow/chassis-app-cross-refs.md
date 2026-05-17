# CHASSIS_APP_DB — Phase C 暗黙参照テーブル スキャンノート

対象テーブル群: `SYSTEM_INTERFACE` / `SYSTEM_NEIGH` / `SYSTEM_LAG_TABLE` / `SYSTEM_LAG_MEMBER_TABLE` / `BGP_DEVICE_GLOBAL|STATE`  
Consumer: `intfsorch` / `neighorch` / `portsorch` (sonic-swss orchagent), `bgpcfgd` (ChassisAppDbMgr / DeviceGlobalCfgMgr)  
スキャン範囲: `main.cpp:278-730`, `intfsorch.cpp:41-110,1672-1773`, `portsorch.cpp:1087-1092,7941-8040,10864-10870,11139-11205`, `neighorch.cpp:2595-2660`, `managers_chassis_app_db.py`, `managers_device_global.py`

---

## 検出した暗黙参照 (leafref 以外の runtime 参照)

### 1. DEVICE_METADATA.localhost.switch_type → CHASSIS_APP_DB 全テーブル (ゲート依存)

- `main.cpp:657,725`: orchagent 起動時に `getCfgSwitchType()` で `DEVICE_METADATA.localhost.switch_type` を読み取り `gMySwitchType` にセット。
- `switch_type == "voq"` かつ `isChassisAppDbPresent()` (= `/etc/sonic/database_config.json` に `CHASSIS_APP_DB` キーが存在) の場合のみ `gMultiAsicVoq = true` が立つ。
- `gMultiAsicVoq = false` の場合、すべての `voqSync*()` 関数は即時 return し CHASSIS_APP_DB には一切書き込まない。
- **依存方向**: CONFIG_DB.DEVICE_METADATA → CHASSIS_APP_DB 全テーブル (one-time gate at startup)
- **証跡**: `main.cpp:694-730`

### 2. DEVICE_METADATA.localhost.switch_id → SYSTEM_LAG_TABLE.switch_id (VoQ switch ID)

- `main.cpp:305-313`: `DEVICE_METADATA.localhost.switch_id` から `gVoqMySwitchId` を初期化。
- `portsorch.cpp:11141-11148`: `voqSyncAddLag()` は `lag.m_system_lag_info.switch_id != gVoqMySwitchId` の場合スキップ。
- `intfsorch.cpp:1681-1684`: `voqSyncAddIntf()` も同様に LAG の場合 `switch_id != gVoqMySwitchId` でスキップ。
- **依存方向**: CONFIG_DB.DEVICE_METADATA.localhost.switch_id → CHASSIS_APP_DB.SYSTEM_LAG_TABLE.switch_id フィールド値
- **証跡**: `main.cpp:305-313`, `portsorch.cpp:11141-11148`

### 3. APPL_DB.APP_SYSTEM_PORT_TABLE → SYSTEM_INTERFACE / SYSTEM_LAG_TABLE 書き込みトリガ

- `portsorch.cpp:10864-10870`: `addSystemPorts()` は `APPL_DB.APP_SYSTEM_PORT_TABLE` を読み込み `m_portList` にシステムポートを登録する。
- この登録が完了しないと `voqSyncAddIntf()` 内の `gPortsOrch->getPort()` が失敗し SYSTEM_INTERFACE への書き込みがスキップされる。
- `APP_SYSTEM_PORT_TABLE` は `portsyncd` が `PORT|PortInitDone` を通知した後に完成する。
- **依存方向**: APPL_DB.APP_SYSTEM_PORT_TABLE → CHASSIS_APP_DB.SYSTEM_INTERFACE 書き込み可否 (PortInitDone 後)
- **証跡**: `portsorch.cpp:10864-10870`, `intfsorch.cpp:1676-1681`

### 4. CONFIG_DB.SYSTEM_PORT → SYSTEM_LAG_TABLE.lag_id 割り当て範囲

- `lagids.lua:15-16`: LAG ID の割り当て範囲 `SYSTEM_LAG_ID_START` / `SYSTEM_LAG_ID_END` は初期化スクリプト (`lagids.lua`) が書き込む。この値は `CONFIG_DB.SYSTEM_PORT` のシステムポート数から計算される。
- フリーリストが初期化されていない状態で `lagIdAdd()` が呼ばれると `LAG_ID_ALLOCATOR_ERROR_TABLE_FULL (-1)` を返し addLag が失敗する。
- **依存方向**: CONFIG_DB.SYSTEM_PORT (暗黙的に計算) → CHASSIS_APP_DB.SYSTEM_LAG_ID_START / SYSTEM_LAG_ID_END (初期化スクリプト経由)
- **証跡**: `portsorch.cpp:7974-7983`, `lagids.lua:15-16,41-44`

### 5. CONFIG_DB.BGP_DEVICE_GLOBAL.tsa_enabled → BGP_DEVICE_GLOBAL|STATE.tsa_enabled (LC 優先ガード)

- `managers_chassis_app_db.py:20`: `ChassisAppDbMgr.__init__()` が `CONFIG_DB.BGP_DEVICE_GLOBAL.tsa_enabled` に `subscribe()` して `self.lc_tsa` を更新。
- `managers_chassis_app_db.py:40-44`: supervisor からの `BGP_DEVICE_GLOBAL|STATE.tsa_enabled` SET 受信時、`self.lc_tsa == "false"` でない限り `isolate_unisolate_device()` を呼ばない。
- LC 側の `CONFIG_DB.BGP_DEVICE_GLOBAL.tsa_enabled == "true"` が supervisor の CHASSIS_APP_DB 書き込みより優先される（LC TSA が supervisor TSA を上書きさせない）。
- **依存方向**: CONFIG_DB.BGP_DEVICE_GLOBAL.tsa_enabled → CHASSIS_APP_DB.BGP_DEVICE_GLOBAL|STATE 適用可否 (runtime guard)
- **証跡**: `managers_chassis_app_db.py:17-44`

### 6. CHASSIS_APP_DB.SYSTEM_LAG_TABLE → CHASSIS_APP_DB.SYSTEM_LAG_MEMBER_TABLE (LAG 先行必須)

- `portsorch.cpp:11183-11186`: `voqSyncAddLagMember()` は `lag.m_system_lag_info.switch_id != gVoqMySwitchId` でスキップ。LAG 自体が `voqSyncAddLag()` 済みでなければ `switch_id` が正しく設定されない。
- `SYSTEM_LAG_MEMBER_TABLE` は `SYSTEM_LAG_TABLE` に対応する LAG が登録された後にのみ書き込まれる。
- **依存方向**: CHASSIS_APP_DB.SYSTEM_LAG_TABLE (先行) → CHASSIS_APP_DB.SYSTEM_LAG_MEMBER_TABLE
- **証跡**: `portsorch.cpp:11179-11193`, `portsorch.cpp:6354-6357`

### 7. CHASSIS_STATE_DB.CHASSIS_MODULE_TABLE → CHASSIS_APP_DB クリーンアップトリガ

- `chassisd:593-658` (`_cleanup_chassis_app_db()`): モジュールが down (oper_status 変化) してから `CHASSIS_DB_CLEANUP_MODULE_DOWN_PERIOD = 30` 分後に実行。
- クリーンアップはモジュール名をキーに SYSTEM_NEIGH / SYSTEM_INTERFACE / SYSTEM_LAG_MEMBER_TABLE / SYSTEM_LAG_TABLE の各エントリをパターン削除する。
- CHASSIS_STATE_DB は CHASSIS_APP_DB への書き込みではなく DEL トリガとして機能する。
- **依存方向**: CHASSIS_STATE_DB.CHASSIS_MODULE_TABLE (oper_status 変化) → CHASSIS_APP_DB 全テーブル DEL 操作
- **証跡**: `chassisd:593-658,89-90`

---

## 依存関係のまとめ

| # | 依存方向 | 参照元 | 参照先テーブル | 依存内容 | 証跡 |
|---|----------|--------|--------------|---------|------|
| 1 | CONFIG_DB → CHASSIS_APP_DB (全体ゲート) | `DEVICE_METADATA.localhost.switch_type` | CHASSIS_APP_DB 全テーブル | `switch_type != "voq"` または DB config 不在時は書き込み一切なし | `main.cpp:694-730` |
| 2 | CONFIG_DB → SYSTEM_LAG_TABLE | `DEVICE_METADATA.localhost.switch_id` | `SYSTEM_LAG_TABLE.switch_id` 値 | ローカル LAG のみ書き込む判定に使用 | `main.cpp:305-313` |
| 3 | APPL_DB → CHASSIS_APP_DB (書き込みトリガ) | `APP_SYSTEM_PORT_TABLE` (PortInitDone 後) | `SYSTEM_INTERFACE` | ポートリスト未完成時は書き込みスキップ | `portsorch.cpp:10864-10870` |
| 4 | CONFIG_DB → CHASSIS_APP_DB (初期化) | `SYSTEM_PORT` (暗黙) | `SYSTEM_LAG_ID_START/END` | LAG ID 割り当て範囲の初期化 | `lagids.lua:15-16` |
| 5 | CONFIG_DB → CHASSIS_APP_DB (適用ガード) | `BGP_DEVICE_GLOBAL.tsa_enabled` (LC 側) | `BGP_DEVICE_GLOBAL\|STATE` | LC TSA が "true" の場合 supervisor TSA 適用をブロック | `managers_chassis_app_db.py:40-44` |
| 6 | CHASSIS_APP_DB 内 (LAG → LAG_MEMBER) | `SYSTEM_LAG_TABLE` | `SYSTEM_LAG_MEMBER_TABLE` | LAG 登録前に LAG_MEMBER 書き込み不可 | `portsorch.cpp:11179-11193` |
| 7 | CHASSIS_STATE_DB → CHASSIS_APP_DB (DEL) | `CHASSIS_MODULE_TABLE` (oper_status) | CHASSIS_APP_DB 全テーブル | モジュール down 30 分後にクリーンアップ | `chassisd:593-658` |
