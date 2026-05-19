# PBH_TABLE 暗黙参照テーブル調査 (Phase C)

## 調査ソース

| ファイル | 役割 |
|---|---|
| `sonic-swss/orchagent/pbhorch.cpp` | PbhOrch メイン処理（subscribe / SAI 反映） |
| `sonic-swss/orchagent/pbh/pbhmgr.cpp` | validateDependencies / incRefCount / decRefCount |
| `sonic-swss/orchagent/aclorch.cpp` | validateAddPorts / AclTable 実装 |
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-pbh.yang` | YANG leafref 定義 |

## 暗黙参照テーブル一覧

### 1. PORT（runtime 解決・YANG leafref あり）

- YANG: `PBH_TABLE.interface_list` は union leafref で `sonic-port/PORT/PORT_LIST/name` を参照（`sonic-pbh.yang:245-247`）
- 実行時: `createPbhTable()` (`pbhorch.cpp:266-272`) で `pbhTable.validateAddPorts(table.interface_list.value)` を呼ぶ。実装は `aclorch.cpp:2691-2721` で `gPortsOrch->getPort(itAlias, port)` を使用してポート名を動的解決する。
- 未充足時: `pendingPortSet` にエントリを追加し保留。`SUBJECT_TYPE_PORT_CHANGE` 通知で再バインドを試みる (`aclorch.cpp:2698-2703`)。

### 2. PORTCHANNEL（runtime 解決・YANG leafref あり）

- YANG: `PBH_TABLE.interface_list` は union leafref で `sonic-portchannel/PORTCHANNEL/PORTCHANNEL_LIST/name` も参照（`sonic-pbh.yang:248-251`）
- 実行時: 同じく `validateAddPorts()` 経由で LAG ポートを解決し `SAI_ACL_BIND_POINT_TYPE_LAG` を取得 (`aclorch.cpp:106`)。
- 未充足時: PORT と同様に `pendingPortSet` 保留 → PORT_CHANGE 通知で自動回復。

### 3. PortsOrch（必須・グローバル起動ゲート）

- `PbhOrch::doTask()` (`pbhorch.cpp:1808`) は `this->portsOrch->allPortsReady()` が false の間は即 return する。
- `PBH_TABLE` を含む全 PBH テーブルの処理が PortsOrch 完了まで完全ブロックされる。

### 4. AclOrch（必須・Orch 間依存）

- `createPbhTable()` の最終ステップ (`pbhorch.cpp:286`) で `this->aclOrch->addAclTable(pbhTable)` を呼ぶ。失敗時は ERROR ログ + `return false`。
- `updatePbhTable()` でも `this->aclOrch->updateAclTable()` を呼ぶ (`pbhorch.cpp:359`)。
- `removePbhTable()` では `this->aclOrch->removeAclTable()` を呼ぶ (`pbhorch.cpp:388`)。

### このテーブルを参照する側（被参照）

| 参照元テーブル | 参照フィールド | 参照タイミング | evidence |
|---|---|---|---|
| `PBH_RULE\|<table_name>\|<rule_name>` (CONFIG_DB) の `table_name` | YANG leafref + runtime 存在チェック | PBH_RULE SET 処理時。`validateDependencies()` (`pbhmgr.cpp:83-88`) で `tableMap.find(rule.table)` が false なら retry loop | `pbhmgr.cpp:83-88`, `pbhorch.cpp:929-968` |

## 双方向参照サマリ

| 参照先テーブル / リソース | YANG leafref | 実行時依存 | 未充足時の挙動 |
|---|:---:|:---:|---|
| `PORT` (CONFIG_DB) | ✅ | validateAddPorts() → gPortsOrch->getPort() | pendingPortSet 保留 → PORT_CHANGE 通知で自動回復 |
| `PORTCHANNEL` (CONFIG_DB) | ✅ | validateAddPorts() → gPortsOrch->getPort() | pendingPortSet 保留 → PORT_CHANGE 通知で自動回復 |
| PortsOrch（グローバルゲート） | ✗ | allPortsReady() ゲート | PBH_TABLE を含む全 PBH 処理がブロック（自動回復） |
| AclOrch（Orch 間） | ✗ | addAclTable() / updateAclTable() / removeAclTable() | ERROR ログ + return false（CONFIG_DB エントリは残存） |

## 書込み方向

`PBH_TABLE` は CONFIG_DB の **読み手（consumer）のみ**。書き手は `config pbh table add` CLI / `sonic-cfggen`。`PbhOrch` は `PBH_TABLE` のステータスを STATE_DB / APPL_DB に書き出さない（ステータステーブル未実装）。
