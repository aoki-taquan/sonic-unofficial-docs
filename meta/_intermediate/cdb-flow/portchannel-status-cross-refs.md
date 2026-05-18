# portchannel-status — Phase C 暗黙参照テーブル (cross-refs) 調査メモ

調査対象: `APPL_DB LAG_TABLE` (portchannel-status.md)  
調査日: 2026-05-18  
調査ソース:
- sonic-swss/teamsyncd/teamsync.cpp (ref:4305596156d70e9797e8a881b3d19b46de0bce0d)
- sonic-swss/cfgmgr/teammgr.cpp (ref:4305596156d70e9797e8a881b3d19b46de0bce0d)
- sonic-swss/orchagent/portsorch.cpp (ref:4305596156d70e9797e8a881b3d19b46de0bce0d)
- sonic-swss/cfgmgr/intfmgr.cpp (ref:4305596156d70e9797e8a881b3d19b46de0bce0d)

## 参照テーブル一覧

### 1. CONFIG_DB PORTCHANNEL → APPL_DB LAG_TABLE (teammgrd が書込み)

`teammgrd` は `CFG_LAG_TABLE_NAME` (CONFIG_DB `PORTCHANNEL`) を watch し、
変更をトリガーに `APP_LAG_TABLE_NAME` (APPL_DB `LAG_TABLE`) へ書き込む。
- teammgr.cpp:33 m_cfgLagTable / m_appLagTable 初期化
- teammgr.cpp:157 CFG_LAG_TABLE_NAME 受信 → doLagTask

### 2. CONFIG_DB PORTCHANNEL_MEMBER → LAG 処理 (teammgrd が読込み)

`teammgrd` は `CFG_LAG_MEMBER_TABLE_NAME` も購読し、
`isLagStateOk()` チェック後に LAG メンバーを処理する。
- teammgr.cpp:34 m_cfgLagMemberTable
- teammgrd:421, 518 m_cfgLagMemberTable.getKeys()

### 3. STATE_DB LAG_TABLE → intfmgrd が参照

`intfmgrd` は `STATE_LAG_TABLE_NAME` を `Consumer` として購読し、
LAG の `state: ok` が書かれると LAG インタフェースの設定を適用する。
- intfmgr.cpp:51-52 STATE_LAG_TABLE_NAME subscriber
- intfmgr.cpp:1183-1184 STATE_PORT_TABLE_NAME / STATE_LAG_TABLE_NAME の統合処理

### 4. COUNTERS_DB COUNTERS_LAG_NAME_MAP (orchagent が書込み)

`portsorch` は LAG SAI オブジェクト作成時に `COUNTERS_LAG_NAME_MAP` へ
`<lag_alias>` → `<sai_oid>` のマッピングを書き込む。
- portsorch.cpp:762 m_counterLagTable = COUNTERS_LAG_NAME_MAP
- portsorch.cpp:8022 addLag() で set
- portsorch.cpp:8095 removeLag() で hdel

### 5. IntfsOrch (orchagent 内) — MTU 伝播

doLagTask() で mtu フィールドを更新すると、LAG に RIF (Router Interface) が
存在する場合は `gIntfsOrch->setRouterIntfsMtu(l)` で RIF MTU も更新される。
- portsorch.cpp:6163

### 6. VoQ 環境: CHASSIS_APP_DB CHASSIS_APP_LAG_TABLE_NAME

VoQ モード (`gMySwitchType == "voq"`) では、`addLag()` / `removeLag()` が
`voqSyncAddLag()` / `voqSyncDelLag()` を呼び `CHASSIS_APP_DB` の
`CHASSIS_APP_LAG_TABLE_NAME` へも同期書き込みする。
- portsorch.cpp:8037-8039, 8114-8116

### 7. ポートイベント: SUBJECT_TYPE_PORT_CHANGE 通知

`addLag()` / `removeLag()` は `notify(SUBJECT_TYPE_PORT_CHANGE, ...)` で
orchagent 内の他 Orch (VXLAN Orch 等) に LAG 追加/削除を通知する。
- portsorch.cpp:8024-8025 (addLag), 8090-8091 (removeLag)
