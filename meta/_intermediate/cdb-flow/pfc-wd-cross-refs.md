# PFC_WD 暗黙参照テーブル調査ノート (Phase C)

## 調査ソース

- `sonic-swss/orchagent/pfcwdorch.cpp`
- `sonic-swss/orchagent/qosorch.cpp`
- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-pfcwd.yang`
- `sonic-utilities/pfcwd/main.py`

## 参照テーブル一覧

### 1. `PORT` テーブル (YANG leafref + 実装参照)

- **経路**: YANG: `leafref { path "/port:sonic-port/port:PORT/port:PORT_LIST/port:name" }` (sonic-pfcwd.yang:37-38)
- **実装**: `pfcwdorch.cpp:193` — `gPortsOrch->getPort(key, port)` で PORT が存在するか確認。存在しない場合 `task_invalid_entry`。
- **実装**: `pfcwdorch.cpp:199-203` — `port.m_type != Port::PHY` 時 `task_invalid_entry`（物理ポートのみ有効）。
- **実装**: `pfcwdorch.cpp:68-71` — `gPortsOrch->allPortsReady()` が false なら全タスクを保留（PORT 初期化完了待ち）。

### 2. `PORT_QOS_MAP` テーブル (実装参照)

- **経路**: `pfcwdorch.cpp:533-555` — `gPortsOrch->getPortPfcWatchdogStatus(port.m_port_id, &pfcMask)` で PFC lossless TC bitmask を取得。
- bitmask は `qosorch.cpp:2136-2155` で `PORT_QOS_MAP` の `pfcwd_sw_enable` フィールド処理時に `setPortPfcWatchdogStatus()` で設定される。
- `pfcMask == 0` の場合: `startWdOnPort()` が "No lossless TC found on port" を LOG_NOTICE して実質 WD 無効のまま返す (`pfcwdorch.cpp:551-555`)。

### 3. `DEVICE_METADATA|localhost` (間接参照: pfcwd CLI)

- **経路**: `pfcwd/main.py:409` — `start_default()` が `default_pfcwd_status` を参照し、`enable` でなければ PFC_WD の自動書き込みをスキップ。
- orchagent が直接参照するわけではなく CLI 経由。

### 4. `DEVICE_NEIGHBOR` (間接参照: pfcwd CLI)

- **経路**: `pfcwd/main.py:415` — `start_default()` が active_ports を `DEVICE_NEIGHBOR.keys()` から取得して対象ポートを決定。

### 5. APPL_DB `PFC_WD_TABLE_INSTORM` (書き込み先)

- **経路**: `pfcwdorch.cpp:688,998-1058` — storm 検出時 `m_applDb->hset(key, queue_index, "PFC_WD_IN_STORM")` を書き込み。warm-reboot 復旧目的。

### 6. FLEX_COUNTER_DB `PFC_WD` グループ

- **経路**: `pfcwdorch.cpp:560,587,593` — `m_pfcwdFlexCounterManager->setCounterIdList(...)` でポート・キューの FlexCounter エントリを登録。
- `PFC_WD_FLEX_COUNTER_GROUP = "PFC_WD"` (pfcwdorch.h:16)。

## 参照の特徴

- PORT は YANG leafref として **スキーマ検証段階**で強制（GLOBAL キーは leafref 対象外）。
- PORT_QOS_MAP の PFC 有効化は **暗黙依存**（YANG に明示なし）。pfcMask=0 でも task_failed にはならず、WD が実質無効になるだけ。
- DEVICE_METADATA / DEVICE_NEIGHBOR 参照は pfcwd CLI (`start_default`) のみ。orchagent 本体は参照しない。
