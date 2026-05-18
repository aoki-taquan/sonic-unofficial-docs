# VOQ_INBAND_INTERFACE — Phase F 副作用調査ノート

調査日: 2026-05-18
対象ファイル:
- sonic-swss/orchagent/intfsorch.cpp
- sonic-swss/orchagent/portsorch.cpp
- sonic-swss/orchagent/neighorch.cpp
- sonic-swss/cfgmgr/nbrmgr.cpp

## 主要副作用

### 副作用 #1: portsorch m_inbandPortName セット

`setVoqInbandIntf()` (portsorch.cpp:11110-11137):
- 単一キー SET で `inband_type` フィールドがある場合、`IntfsOrch::doTask()` が `gPortsOrch->setVoqInbandIntf(alias, inband_type)` を呼ぶ
- `m_inbandPortName = alias` を代入 (portsorch.cpp:11134)
- 以降 `isInbandPort(alias)` が true を返すようになる

### 副作用 #2/#3: CHASSIS_APP_DB SYSTEM_INTERFACE_TABLE

`voqSyncAddIntf()` / `voqSyncDelIntf()` (intfsorch.cpp:1672-1747):
- `addRouterIntfs()` 成功後に `voqSyncAddIntf()` を呼ぶ (intfsorch.cpp:1314-1318)
- ローカルポートのシステムポートエイリアスを key として `oper_status` を書き込む
- `removeRouterIntfs()` 成功後に `voqSyncDelIntf()` を呼ぶ (intfsorch.cpp:1367-1371)
- リモートポートは `SAI_SYSTEM_PORT_TYPE_REMOTE` チェックでスキップ

### 副作用 #4/#5: SAI ネイバー + CHASSIS_APP_DB SYSTEM_NEIGH_TABLE

`addInbandNeighbor()` (neighorch.cpp:2281-2351):
- IP プレフィクスロウ処理で `isInbandPort()` が true のとき `gNeighOrch->addInbandNeighbor()` を呼ぶ (intfsorch.cpp:586-592)
- SAI `sai_neighbor_api->create_neighbor_entry` でネイバーを作成
  - `SAI_NEIGHBOR_ENTRY_ATTR_NO_HOST_ROUTE = true` でホストルートを抑制 (neighorch.cpp:2314-2316)
- `voqSyncAddNeigh()` で CHASSIS_APP_DB `SYSTEM_NEIGH_TABLE` へ同期 (neighorch.cpp:2347-2348)

### 副作用 #6: カーネルネイバー + カーネルルート (nbrmgrd)

`doStateSystemNeighTask()` (nbrmgr.cpp:406-521):
- `getVoqInbandInterfaceName()` が `VOQ_INBAND_INTERFACE` テーブルから inband IF 名を取得 (nbrmgr.cpp:524-549)
- `addKernelNeigh()`: `ip neigh add <addr> dev <inband-if>` でカーネルネイバー登録
- `addKernelRoute()`: IPv4 は `ip route add <addr>/32 dev <inband-if>`、IPv6 は `ip -6 route add <addr>/128 dev <inband-if> metric 256` (nbrmgr.cpp:552-575)

## 注意点

- CHASSIS_APP_DB 書き込み (副作用 #2-5) は VOQ chassis 環境 (`isChassisDbInUse()` or `gMySwitchType == "voq"`) のみ
- `nbrmgrd` は STATE_DB `SYSTEM_NEIGH_TABLE` の SET/DEL をトリガーとして動作するが、その処理に `VOQ_INBAND_INTERFACE` テーブルを参照する
- inband ネイバーの `NO_HOST_ROUTE` は routing loop 防止のための重要なフラグ
