# APPL_DB PORT_TABLE 暗黙参照スキャン (Phase C)

`docs/reference/config-db/appl-port-table.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-swss/orchagent/portsorch.cpp` (ref `4305596156d70e9797e8a881b3d19b46de0bce0d`)。
`PortsOrch` が APPL_DB の `PORT_TABLE` を購読・書き戻す際に間接的に読み出す関連テーブル / Orch / DB を列挙する。

## スキャン手順

```
grep -nE 'getPort\(|gBufferOrch|m_systemPortTable|m_gearboxTable|getSystemPorts|addSystemPorts|isGearboxEnabled|gIntfsOrch->isLocalSystemPortIntf|generateQueueMap|generatePriorityGroupMap' \
    .cache/sonic-sources/sonic-swss/orchagent/portsorch.cpp
```

`PortsOrch::doPortTask()` から派生する各処理（admin/mtu/AN/FEC/speed 等の SAI 反映、queue/PG マップ生成、SystemPort 列挙、Gearbox 拡張）を追い、APPL_DB `PORT_TABLE` 単独では完結しない参照を抽出した。

## 検出された暗黙参照

### CONFIG_DB `PORT` テーブル（buffer ready ゲート）

| 参照先 | 参照方向 | 条件 | evidence |
|---|---|---|---|
| `gBufferOrch->isPortReady(alias)` 経由の CONFIG_DB `BUFFER_PG` / `BUFFER_QUEUE` 設定有無 | gate (前提条件チェック) — 必須 | APPL_DB `PORT_TABLE` SET の処理時、buffer 設定が未到達なら `m_pendingPortSet` に保留し再試行 | `portsorch.cpp:4779-4790` |
| `gBufferOrch` (extern) | Orch 間呼び出し（参照のみ） | port SET を SAI に反映する前段の依存解決 | `portsorch.cpp:62` |

### APPL_DB `QUEUE_TABLE` / queue OID 解決

| 参照先 | 参照方向 | 条件 | evidence |
|---|---|---|---|
| Port struct `port.m_queue_ids[]` / `getQueueTypeAndIndex()` | SAI から取得した queue OID リストの解決 | port 初期化後に SAI `SAI_PORT_ATTR_QOS_QUEUE_LIST` で取得した OID を保持し、`generateQueueMapPerPort()` で COUNTERS_DB queue マップを構築 | `portsorch.cpp:3626, 8391-8446` |
| `addQueueFlexCountersPerPortPerQueueIndex()` | flex counter 動的登録 | VoQ スイッチ（`gMySwitchType == "voq"`）または通常 queue/watermark counter 群が有効な場合 | `portsorch.cpp:8505-8515, 4213-4242` |
| COUNTERS_DB `COUNTERS_QUEUE_NAME_MAP` / `QUEUE_PORT_MAP` / `QUEUE_INDEX_MAP` / `QUEUE_TYPE_MAP` | 副次書込（cross-refs 観点ではこの map を介して queue を解決） | port 単位 queue マップ初期化時 | `portsorch.cpp:8446-8520` |

### APPL_DB Priority Group (PG) / `m_pgPortTable` / `m_pgIndexTable`

| 参照先 | 参照方向 | 条件 | evidence |
|---|---|---|---|
| Port struct `port.m_priority_group_ids[]` | SAI `SAI_PORT_ATTR_PRIORITY_GROUP_LIST` から取得した OID 列を解決 | `generatePriorityGroupMapPerPort()` で PG マップを構築する前提 | `portsorch.cpp:8858-8884` |
| COUNTERS_DB `COUNTERS_PG_NAME_MAP` / `PG_PORT_MAP` / `PG_INDEX_MAP` | 名前・port・index の解決マップ | port 初期化時に PG counter が有効な場合 | `portsorch.cpp:786-787, 8822-8884` |
| FLEX_COUNTER_DB `PG_WATERMARK_STAT_COUNTER` / `PG_DROP_STAT_COUNTER` | flex counter 動的登録 | `getPgWatermarkCountersState()` 等が真のとき | `portsorch.cpp:872-892, 3988-3995` |

### CONFIG_DB `BUFFER_*` 経由の間接参照

| 参照先 | 参照方向 | 条件 | evidence |
|---|---|---|---|
| APPL_DB `BUFFER_PG_TABLE` / `BUFFER_QUEUE_TABLE` の port-ready 状態 | `BufferOrch::isPortReady()` 経由 — 必須ゲート | buffer 反映完了まで port SET は保留される（`m_pendingPortSet`） | `portsorch.cpp:4779-4790` |
| STATE_DB `BUFFER_MAX_PARAM_TABLE:<alias>` | side-effect 書込（cross-refs 観点では参照元の port 構成に依存） | `addPort()` / `deInitPort()` 経由で port の max_headroom_size / max_priority_groups / max_queues を書く | `portsorch.cpp:790, addPort/deInitPort` |

### `_GEARBOX_TABLE` (APPL_DB 内 internal key)

| 参照先 | 参照方向 | 条件 | evidence |
|---|---|---|---|
| APPL_DB `_GEARBOX_TABLE` (key prefix で隔離) | `GearboxUtils::isGearboxEnabled()` 経由で読み出し | platform に gearbox 定義が存在する場合のみ。`m_gearboxPhyMap` / `m_gearboxInterfaceMap` / `m_gearboxLaneMap` / `m_gearboxPortMap` を構築 | `portsorch.cpp:775, 10374-10390` |
| `m_gearboxTable->hset("phy:<id>:ports:<index>", speed_attr, ...)` | 書込（参照後の更新） | gearbox 環境で SAI 速度設定後に gearbox table へ反映 | `portsorch.cpp:3421-3422` |
| APPL_DB `PORT_TABLE:<alias>` の `system_oper_status` / `line_oper_status` | gearbox 環境のみ書き戻し | `updateGearboxPortOperStatus()` 経由（Phase F side-effect で既出） | `portsorch.cpp:11220-11260` |

### APPL_DB `SYSTEM_PORT_TABLE`

| 参照先 | 参照方向 | 条件 | evidence |
|---|---|---|---|
| APPL_DB `SYSTEM_PORT_TABLE` (`APP_SYSTEM_PORT_TABLE_NAME`) | `m_systemPortTable->get(alias, fv)` で読み出し | VoQ チャシス構成（`gMySwitchType != "dpu"`）。SystemPort 列挙時に各 sysport の config を取得 | `portsorch.cpp:772, 10766, 11029-11038` |
| `getSystemPorts()` / `addSystemPorts()` | 初期化時に SAI `SAI_SWITCH_ATTR_SYSTEM_PORT_LIST` を読み、APPL_DB `SYSTEM_PORT_TABLE` と突合 | VoQ チャシスのみ。物理 PORT 初期化完了後に呼び出される | `portsorch.cpp:1047, 4620, 10766-10864` |
| `gIntfsOrch->isLocalSystemPortIntf(alias)` | local sysport 判定 | VoQ チャシスで oper speed 書き戻しを STATE_DB に振り分ける際に参照 | `portsorch.cpp:9839` |
| COUNTERS_DB `COUNTERS_SYSTEM_PORT_NAME_MAP` | 副次書込（参照観点では sysport name の解決） | sysport 初期化時 | `portsorch.cpp:761` |

### CONFIG_DB `PORT` テーブル（PortConfigDone / PortInitDone ゲート）

| 参照先 | 参照方向 | 条件 | evidence |
|---|---|---|---|
| portsyncd 由来 `PortConfigDone` / `PortInitDone` notification | gate | `m_initDone` / `m_portConfigState` が揃うまで APPL_DB `PORT_TABLE` の通常 SET 処理は走らない | `portsorch.cpp:4620, 1238 (getPortConfigState)` |
| CONFIG_DB `PORT\|<alias>` (Direction A 入力) | portsyncd 中継後の APPL_DB エントリで処理 | `PortsOrch` は APPL_DB `PORT_TABLE` consumer。CONFIG_DB の `PORT` を直接 subscribe しない | `portsorch.cpp:Consumer setup, portsyncd/portsyncd.cpp` |

## 共依存テーブル（Direction A の構成材料）

`PortsOrch` は APPL_DB `PORT_TABLE` を購読する。CONFIG_DB `PORT` は `portsyncd` 経由で APPL_DB に転写されるため、`PortsOrch` から CONFIG_DB を直接読むことはない（warm-reboot 時の `Table` 経由読み出しを除く）。

| テーブル | 役割 | evidence |
|---|---|---|
| CONFIG_DB `PORT` | portsyncd の入力 → APPL_DB `PORT_TABLE` 出力 | `portsyncd/portsyncd.cpp:196-208` |
| CONFIG_DB `BUFFER_PG` / `BUFFER_QUEUE` | `bufferorch` の port-ready 判定の前提（CONFIG_DB 段階） | `bufferorch.cpp:113-141` |
| CONFIG_DB `DEVICE_METADATA.localhost.switch_type` | VoQ / dpu 判定 | `portsorch.cpp:gMySwitchType 参照箇所` |

> CONFIG_DB 側のこれらテーブルは APPL_DB 段では暗黙参照に含めない。Direction A 入力として `portsyncd` / `buffermgrd` の cross-refs で扱う。

## 検証コマンド

```bash
grep -nE 'gBufferOrch->isPortReady|m_systemPortTable->|m_gearboxTable->|getSystemPorts|addSystemPorts|isGearboxEnabled|generateQueueMapPerPort|generatePriorityGroupMapPerPort' \
    .cache/sonic-sources/sonic-swss/orchagent/portsorch.cpp

grep -n 'isLocalSystemPortIntf\|gMySwitchType' \
    .cache/sonic-sources/sonic-swss/orchagent/portsorch.cpp
```

このスキャン結果から派生して `docs/reference/config-db/appl-port-table.md` の `<!-- cross-refs -->` ブロックを生成する。
