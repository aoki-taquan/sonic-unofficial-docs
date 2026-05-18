# fabric-port — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/fabric-port.md` Phase C 追加分。
本ページの主題は **CONFIG_DB の `FABRIC_PORT` テーブル**であり、`fabricmgrd`（`FabricMgr`）が CONFIG_DB を購読し APPL_DB に中継、`FabricPortsOrch` が APPL_DB を購読して SAI に反映する。
ここでの「暗黙参照」とは、`FABRIC_PORT` エントリの処理において暗黙的に参照・依存する**他テーブル**および**外部情報源**を指す。
`sonic-swss/cfgmgr/fabricmgr.cpp` / `orchagent/fabricportsorch.cpp` の全行を精読して暗黙依存を網羅した。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-swss/cfgmgr/fabricmgr.cpp` | `FabricMgr::doTask()` — CONFIG_DB FABRIC_PORT を購読し APPL_DB に中継 |
| `sonic-swss/orchagent/fabricportsorch.cpp` | `FabricPortsOrch` コンストラクタ / `doFabricPortTask()` / `updateFabricDebugCounters()` / `updateFabricPortState()` / `getFabricPortList()` |
| `sonic-swss/orchagent/fabricportsorch.h` | ハードコード定数、`m_getFabricPortListDone` フラグ定義 |
| `sonic-swss-common/common/schema.h` | `APP_FABRIC_PORT_TABLE_NAME` / `COUNTERS_FABRIC_PORT_NAME_MAP` / `COUNTERS_FABRIC_QUEUE_NAME_MAP` |
| `sonic-swss/orchagent/orchdaemon.cpp` | `APP_FABRIC_MONITOR_PORT_TABLE_NAME = "FABRIC_PORT_TABLE"` / `APP_FABRIC_MONITOR_DATA_TABLE_NAME = "FABRIC_MONITOR_TABLE"` 定義 |

## YANG leafref

`FABRIC_PORT` の YANG モデル（`sonic-fabric-port.yang`）には他テーブルへの leafref は定義されていない。全依存が実装レベルの暗黙参照。

## 暗黙参照 (実装レベル)

### 1. CONFIG_DB `FABRIC_MONITOR` — `monState` ゲート

- **参照先テーブル**: `CONFIG_DB FABRIC_MONITOR` → `APPL_DB FABRIC_MONITOR_TABLE`
- **参照方向**: 読み取り（`fabricmgrd` → APPL_DB → `FabricPortsOrch`）
- **参照フィールド**: `monState`（`"enable"` / `"disable"`）
- **条件**: 常時。`doFabricPortTask()` 冒頭で `checkFabricPortMonState()` を呼び出す
- **意味**: `APPL_DB FABRIC_MONITOR_TABLE|FABRIC_MONITOR_DATA.monState == "enable"` でなければ `doFabricPortTask()` が即 return し、`FABRIC_PORT` の `isolateStatus` 変更は SAI に一切反映されない。`FABRIC_MONITOR.monState` が `FABRIC_PORT` の実効性を支配する暗黙依存。
- **evidence**: `fabricportsorch.cpp:135-157` (`checkFabricPortMonState`)、`fabricportsorch.cpp:1394-1399` (`doFabricPortTask` 冒頭ガード)

### 2. APPL_DB `FABRIC_MONITOR_TABLE` — モニタリング閾値

- **参照先テーブル**: `APPL_DB FABRIC_MONITOR_TABLE`（`= "FABRIC_MONITOR_TABLE"`）
- **参照方向**: 読み取り（`m_applMonitorConstTable->get("FABRIC_MONITOR_DATA", constValues)`）
- **参照フィールド**: `monErrThreshCrcCells`, `monErrThreshRxCells`, `monPollThreshIsolation`, `monPollThreshRecovery`
- **条件**: `updateFabricDebugCounters()` の毎ポーリング時（12 秒間隔）
- **意味**: `FABRIC_MONITOR` テーブルで定義された閾値が自動 isolate / unisolate の判定に使用される。これらのフィールドが APPL_DB に存在しない場合、ハードコードデフォルト値（`FEC_ISOLATE_POLLS=2`、`FEC_UNISOLATE_POLLS=8`、`ERROR_RATE_CRC_CELLS_CFG=1`、`ERROR_RATE_RX_CELLS_CFG=61035156`）が代わりに使われる。
- **evidence**: `fabricportsorch.cpp:434-483` (`updateFabricDebugCounters` 冒頭の constValues ループ)

### 3. STATE_DB `FABRIC_PORT_TABLE` — `forceUnisolateStatus` 差分比較

- **参照先テーブル**: `STATE_DB FABRIC_PORT_TABLE`（`= APP_FABRIC_PORT_TABLE_NAME`）
- **参照方向**: 読み取り + 書き込み（`m_stateTable->get(state_key, values)` / `updateStateDbTable(...)`）
- **参照フィールド**: `FORCE_UN_ISOLATE`、`CONFIG_ISOLATED`、`ISOLATED`、`AUTO_ISOLATED`、`PRM_ISOLATED`、`POLL_WITH_ERRORS` 等
- **条件**: `doFabricPortTask()` で `isolateStatus=False` かつ `forceUnisolateStatus` を含む SET を受信したとき
- **意味**: `FORCE_UN_ISOLATE` フィールドとの比較で force unisolate を実行するかを決定する。STATE_DB エントリが存在しない場合はデフォルト 0 と比較するため、`forceUnisolateStatus=0` で SET しても force unisolate が実行されない（差分なし）。
- **evidence**: `fabricportsorch.cpp:1496-1542` (`doFabricPortTask` 内 force unisolate 処理)

### 4. COUNTERS_DB `COUNTERS_TABLE` / `COUNTERS_FABRIC_PORT_NAME_MAP` — ポートカウンタ

- **参照先テーブル**: `COUNTERS_DB COUNTERS_TABLE`、`COUNTERS_FABRIC_PORT_NAME_MAP`、`COUNTERS_FABRIC_QUEUE_NAME_MAP`
- **参照方向**: 読み取り（`m_fabricCounterTable->get(sai_serialize_object_id(port), fieldValues)`）
- **条件**: `updateFabricDebugCounters()` 毎ポーリング時
- **意味**: FlexCounter が収集した SAI 統計（`SAI_PORT_STAT_IF_IN_ERRORS`、`SAI_PORT_STAT_IF_IN_FABRIC_DATA_UNITS`、`SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES`）を取得し、CRC エラー率・FEC エラー率を計算して自動 isolate 判定に使用する。COUNTERS_DB にデータがない場合はエラーなし扱いとなり、意図しない unisolate が発生する可能性がある。
- **evidence**: `fabricportsorch.cpp:500-520` (`updateFabricDebugCounters` カウンタ読み取り部)

### 5. SAI switch attribute — fabric ポートリスト

- **参照先**: SAI `SAI_SWITCH_ATTR_NUMBER_OF_FABRIC_PORTS` / `SAI_SWITCH_ATTR_FABRIC_PORT_LIST`
- **参照方向**: SAI クエリ（起動時 + ポーリング再試行）
- **条件**: `getFabricPortList()` — コンストラクタ時および 30 秒ポーリングで `m_getFabricPortListDone=false` のとき
- **意味**: SAI からファブリックポートのオブジェクト ID リストを取得し `m_fabricLanePortMap`（lane → SAI port OID）を構築する。この初期化が完了するまで（`m_getFabricPortListDone=true`）、`updateFabricPortState()` / `updateFabricDebugCounters()` / `generateQueueStats()` はすべてスキップされる。FABRIC_PORT CONFIG_DB エントリが存在しても、SAI 初期化完了前は状態更新が行われない。
- **evidence**: `fabricportsorch.cpp:159-228` (`getFabricPortList`)、`fabricportsorch.cpp:1562-1576` (timer ハンドラ内の `m_getFabricPortListDone` チェック)

### 6. `gMySwitchType` — VOQ / fabric スイッチ種別

- **参照先**: グローバル変数 `gMySwitchType`（`DEVICE_METADATA|localhost.switch_type` 由来）
- **参照方向**: 読み取り（起動時）
- **参照箇所**: コンストラクタ内の `switch_drop_counter_manager` 作成条件
- **条件**: `(gMySwitchType == "voq") || (gMySwitchType == "fabric")` のとき
- **意味**: スイッチ種別が `"voq"` または `"fabric"` の場合のみ、`SWITCH_DEBUG_COUNTER_FLEX_COUNTER_GROUP` の FlexCounter を作成し switch レベルドロップカウンタを収集する。それ以外の種別（通常 ToR 等）ではこのカウンタは作成されない。`FABRIC_PORT` テーブル自体も VOQ / fabric 専用であり、ToR 上での使用は想定されていない。
- **evidence**: `fabricportsorch.cpp:104-110` (コンストラクタ内 switch_drop_counter_manager 作成)

## 参照関係サマリ

```
CONFIG_DB FABRIC_PORT
  → fabricmgrd (FabricMgr::doTask)
  → APPL_DB FABRIC_PORT_TABLE   (= APP_FABRIC_PORT_TABLE_NAME)
  → FabricPortsOrch::doFabricPortTask()

暗黙参照 (FabricPortsOrch 側):
  ├─ [ゲート]  APPL_DB FABRIC_MONITOR_TABLE.monState == "enable"
  │                  (false の間 doFabricPortTask は early return、SAI 変更なし)
  ├─ [閾値]   APPL_DB FABRIC_MONITOR_TABLE — monErrThreshCrcCells / monPollThreshIsolation 等
  │                  (欠落時はハードコードデフォルト使用)
  ├─ [比較]   STATE_DB FABRIC_PORT_TABLE.FORCE_UN_ISOLATE
  │                  (forceUnisolateStatus 差分比較に使用)
  ├─ [カウンタ] COUNTERS_DB COUNTERS_TABLE — SAI_PORT_STAT_* (CRC/FEC エラー率計算)
  ├─ [初期化] SAI SAI_SWITCH_ATTR_FABRIC_PORT_LIST (m_getFabricPortListDone フラグ)
  └─ [分岐]   gMySwitchType (voq/fabric: switch drop counter 収集有無)
```

## evidence

- `fabricmgr.cpp`: L23-104 (`FabricMgr::doTask` — フィールドを APPL_DB に中継)
- `fabricportsorch.cpp`: L80-133 (コンストラクタ、DB 接続と FlexCounter 初期化), L135-157 (`checkFabricPortMonState`), L159-228 (`getFabricPortList`), L420-483 (`updateFabricDebugCounters` 閾値読み取り), L500-520 (COUNTERS_DB 読み取り), L1394-1484 (`doFabricPortTask` — monState ゲート + 3 フィールド完全性チェック), L1496-1542 (force unisolate 処理 + STATE_DB 読み書き)
- `schema.h`: `APP_FABRIC_PORT_TABLE_NAME = "FABRIC_PORT_TABLE"`, `COUNTERS_FABRIC_PORT_NAME_MAP`, `COUNTERS_FABRIC_QUEUE_NAME_MAP`
- `orchdaemon.cpp`: L26-27 (`APP_FABRIC_MONITOR_PORT_TABLE_NAME = "FABRIC_PORT_TABLE"`, `APP_FABRIC_MONITOR_DATA_TABLE_NAME = "FABRIC_MONITOR_TABLE"`)
