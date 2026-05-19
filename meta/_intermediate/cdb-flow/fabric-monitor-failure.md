# FABRIC_MONITOR テーブル — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-19 (q67-f-batch834)

対象ページ: `docs/reference/config-db/fabric-monitor.md`
対象テーブル: `CONFIG_DB.FABRIC_MONITOR`
Producer: `fabricmgrd` (`sonic-swss/cfgmgr/fabricmgr.cpp`)
Consumer: `FabricPortsOrch` (`sonic-swss/orchagent/fabricportsorch.cpp`)

スキャン範囲:
- `FabricMgr::doTask()` / `writeConfigToAppDb()` 全行
- `FabricPortsOrch::getFabricPortList()` L159-224
- `FabricPortsOrch::checkFabricPortMonState()` L135-157
- `FabricPortsOrch::updateFabricDebugCounters()` L424-963
- `FabricPortsOrch::updateFabricCapacity()` L1044-1232
- `FabricPortsOrch::doFabricPortTask()` L1394-1547
- `FabricPortsOrch::doTask(SelectableTimer&)` L1562-1615
- `FabricPortsOrch::isolateFabricLink()` L983-1003

---

## fabricmgrd の失敗経路

### SET 処理

| 失敗条件 | 発生箇所 | 結果 | ログ | evidence |
|---|---|---|---|---|
| 未知フィールド名 (known フィールド以外) | `FabricMgr::doTask()` L92-100 | `field_values` ベクタに追加 → `writeConfigToAppDb()` で APPL_DB に書き込まれる（フィールドが何であれ転送） | なし（スルー） | `fabricmgr.cpp:92-100` |
| key が `FABRIC_MONITOR_DATA` 以外 | `writeConfigToAppDb()` L112 | `m_appFabricPortTable` (APPL_DB `APP_FABRIC_MONITOR_PORT_TABLE_NAME`) に書き込み（`FABRIC_PORT` テーブル扱い） | `SWSS_LOG_INFO` | `fabricmgr.cpp:117-120` |
| APPL_DB `set()` 中に Redis 接続障害 | `writeConfigToAppDb()` | 例外伝播（catch なし）→ fabricmgrd プロセスクラッシュ | スタックトレースが syslog へ | `fabricmgr.cpp:108-124` |

fabricmgrd は `doTask()` 内で例外をキャッチしないため、Redis 障害や予期しない例外は fabricmgrd プロセス全体のクラッシュにつながる。CONFIG_DB の値は未変更のまま残る。

---

## FabricPortsOrch の失敗経路

### getFabricPortList() (起動時)

| 失敗条件 | 発生箇所 | 結果 | ログ | evidence |
|---|---|---|---|---|
| SAI `get_switch_attribute` (`SAI_SWITCH_ATTR_NUMBER_OF_FABRIC_PORTS`) が `SAI_STATUS_SUCCESS` 以外 | `getFabricPortList()` L173 | `handleSaiGetStatus()` 判定。`task_success` 以外は `FABRIC_PORT_ERROR` を返して early return。`m_getFabricPortListDone=false` のまま | `SWSS_LOG_ERROR` | `fabricportsorch.cpp:173-180` |
| SAI `get_switch_attribute` (`SAI_SWITCH_ATTR_FABRIC_PORT_LIST`) が `SAI_STATUS_SUCCESS` 以外 | `getFabricPortList()` L190-196 | `throw runtime_error("FabricPortsOrch get port list failure")` → orchagent プロセスクラッシュ | スタックトレース | `fabricportsorch.cpp:193-197` |
| SAI `get_port_attribute` (`SAI_PORT_ATTR_HW_LANE_LIST`) が `SAI_STATUS_SUCCESS` 以外 | `getFabricPortList()` L207-213 | `throw runtime_error("FabricPortsOrch get port lane failure")` → orchagent プロセスクラッシュ | スタックトレース | `fabricportsorch.cpp:210-213` |
| `m_fabricPortCount` == 0 (`SAI_SWITCH_ATTR_NUMBER_OF_FABRIC_PORTS` が 0 を返す) | `getFabricPortList()` L182 | `m_fabricPortCount=0`、ポートリストが空のまま `FABRIC_PORT_SUCCESS` を返す。`m_getFabricPortListDone=true` にはなるが監視対象ポートが 0 件 | `SWSS_LOG_NOTICE("Get 0 fabric ports")` | `fabricportsorch.cpp:182-183` |

### updateFabricDebugCounters() (ポーリング時)

| 失敗条件 | 発生箇所 | 結果 | ログ | evidence |
|---|---|---|---|---|
| APPL_DB `FABRIC_MONITOR_DATA` が存在しない | L444-448 | ハードコード定数 (`ERROR_RATE_CRC_CELLS_CFG=1` / `ERROR_RATE_RX_CELLS_CFG=61035156` / `ISOLATION_POLLS_CFG=1` / `RECOVERY_POLLS_CFG=8`) を使用して処理継続 | `SWSS_LOG_INFO("applConstKey ... default values not set")` | `fabricportsorch.cpp:444-448` |
| COUNTERS_DB にポートの統計エントリなし | L500-503 | `rxCells=0` / `crcErrors=0` / `codeErrors=0` のゼロ値で処理継続。エラーなしと判断され isolate は発生しない | `SWSS_LOG_INFO("no port <oid>")` | `fabricportsorch.cpp:500-503` |
| STATE_DB `FABRIC_PORT_TABLE|PORT<lane>` が存在しない | L619-624 | `return` で当該ポート以降の全ポーリング処理をスキップ（関数全体が early return） | `SWSS_LOG_INFO("No state infor for port <key>")` | `fabricportsorch.cpp:619-624` |
| APPL_DB `FABRIC_PORT_TABLE|Fabric<lane>` (`isolateStatus`) が存在しない | L590-593 | `cfgIsolated=0`（unisolated 扱い）で処理継続 | `SWSS_LOG_INFO("No app infor for port <key>")` | `fabricportsorch.cpp:590-593` |
| SAI `sai_port_api->set_port_attribute` (isolate) が失敗 | `isolateFabricLink()` L996-999 | エラーログのみ。STATE_DB への `ISOLATED` フラグ書き込みは実行済み → STATE_DB と SAI のハードウェア状態が乖離 | `SWSS_LOG_ERROR("Failed to set admin status")` | `fabricportsorch.cpp:996-999` |
| `m_fabricLanePortMap` にレーン番号が存在しない (`isolateFabricLink` 内) | `isolateFabricLink()` L990-993 | SAI 呼び出しをスキップ（silent skip）。アイソレートが実行されない | `SWSS_LOG_INFO("NOT find fabric lane <n>")` | `fabricportsorch.cpp:990-993` |

### updateFabricCapacity() (ポーリング時)

| 失敗条件 | 発生箇所 | 結果 | ログ | evidence |
|---|---|---|---|---|
| APPL_DB `FABRIC_MONITOR_DATA.monCapacityThreshWarn` が未設定 | L1058-1061 | `threshold=100` (ハードコードフォールバック) で警告判定を継続。YANG default `10` との乖離あり（`cdb-exceptions` ブロックに既記） | `SWSS_LOG_INFO("... default values not set")` | `fabricportsorch.cpp:1052,1059` |
| STATE_DB `FABRIC_PORT_TABLE|PORT<lane>` が存在しない | L1093-1098 | `return` で `updateFabricCapacity()` 全体が early return。STATE_DB `FABRIC_CAPACITY_DATA` が更新されない | `SWSS_LOG_INFO("No state infor for port <key>")` | `fabricportsorch.cpp:1093-1098` |

### doFabricPortTask() (APPL_DB イベント処理)

| 失敗条件 | 発生箇所 | 結果 | ログ | evidence |
|---|---|---|---|---|
| `monState=disable` (または APPL_DB 未設定) | `checkFabricPortMonState()` L1396 | `doFabricPortTask()` が early return。APPL_DB `APP_FABRIC_MONITOR_PORT_TABLE_NAME` イベントが処理されない | `SWSS_LOG_INFO("doFabricPortTask returns early due to feature disabled")` | `fabricportsorch.cpp:1396-1400` |
| `alias` / `lanes` / `isolateStatus` のいずれかが APPL_DB にも通知フィールドにも存在しない | `doFabricPortTask()` L1479-1485 | `consumer.m_toSync.erase()` して次エントリへ (silent skip)。ポートのアイソレート制御がスキップされる | `SWSS_LOG_INFO("NULL values, skipping <key>")` | `fabricportsorch.cpp:1479-1485` |

---

## 失敗挙動サマリ

| # | トリガー | 発生箇所 | 結果 | retry |
|---|---------|---------|------|-------|
| 1 | SAI ファブリックポートリスト取得失敗（恒久エラー） | `getFabricPortList()` | `runtime_error` → orchagent クラッシュ | 自動再起動（supervisord による） |
| 2 | SAI ファブリックポート数取得失敗 | `getFabricPortList()` | `FABRIC_PORT_ERROR` 返却・監視未開始 / 次 FABRIC_POLL (30 秒) で再試行 | 30 秒間隔で自動 retry |
| 3 | STATE_DB `FABRIC_PORT_TABLE` エントリ欠如 | `updateFabricDebugCounters()` / `updateFabricCapacity()` | 関数全体 early return・監視更新停止 | 次ポーリングで再試行 |
| 4 | COUNTERS_DB ポート統計エントリ欠如 | `updateFabricDebugCounters()` | ゼロ値でエラー無しとみなし処理継続 | — |
| 5 | SAI isolate set 失敗 | `isolateFabricLink()` | STATE_DB と SAI ハードウェア間で isolation 状態が乖離 | なし（次ポーリング変化まで再試行なし） |
| 6 | `monState=disable` / APPL_DB 未設定 | `doFabricPortTask()` / `updateFabricDebugCounters()` | 監視処理・ポート制御を全スキップ | — |
| 7 | Redis 接続障害（fabricmgrd 側） | `writeConfigToAppDb()` | fabricmgrd クラッシュ | supervisord 再起動 |

---

## ページ反映方針

- `<!-- failure -->` ブロックを `<!-- /ordering -->` と `<!-- cross-refs -->` の間に挿入する。
- 主要失敗パス（#1/#3/#5）を散文で補足する。
- retry メカニズムの有無を明示する。
