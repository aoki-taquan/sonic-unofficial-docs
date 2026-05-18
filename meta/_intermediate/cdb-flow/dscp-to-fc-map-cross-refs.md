# DSCP_TO_FC_MAP — 暗黙参照テーブル調査 (Phase C)

## 調査対象

- `sonic-swss/orchagent/qosorch.cpp` (全 handlers)
- `sonic-swss/orchagent/cbf/nhgmaporch.cpp` (getMaxNumFcs)
- `sonic-swss/orchagent/qosorch.h` (type_map, field_name 定数)

## 検出された暗黙参照

### 1. PORT_QOS_MAP (CONFIG_DB)

- **参照方向**: 被参照（`PORT_QOS_MAP.dscp_to_fc_map` フィールドが `DSCP_TO_FC_MAP` マップ名を leafref）
- **条件**: `PORT_QOS_MAP` の `dscp_to_fc_map` フィールド SET 時
- **参照元**: `qosorch.cpp:111` — `qos_to_ref_table_map` にて `dscp_to_fc_field_name → CFG_DSCP_TO_FC_MAP_TABLE_NAME` のマッピング登録
- **意味**: `PORT_QOS_MAP.dscp_to_fc_map` が DSCP_TO_FC_MAP への参照を持つ。DEL 時に参照カウンタが 0 になるまで保留 (`m_pendingRemove=true`)

### 2. SAI switch — `SAI_SWITCH_ATTR_MAX_NUMBER_OF_FORWARDING_CLASSES`

- **参照方向**: SAI query（間接依存）
- **条件**: `DscpToFcMapHandler::convertFieldValuesToAttributes()` 呼び出し時（エントリごとに毎回 `getMaxNumFcs()` を呼ぶが内部は static キャッシュ）
- **参照元**: `qosorch.cpp:1043`; `nhgmaporch.cpp:299-325`
- **意味**: FC 上限値をランタイムで SAI から取得。FC 非対応 ASIC では `max_num_fcs=0` → 全エントリ reject。初回クエリ後は static キャッシュで固定（orchagent 再起動まで変化しない）

### 3. EXP_TO_FC_MAP (CONFIG_DB)

- **参照方向**: 同族テーブル（共通 `m_qos_maps` 型マップを共有）
- **条件**: `QosOrch` 初期化時に `m_qos_maps` に両テーブルを登録 (`qosorch.cpp:93`)
- **参照元**: `qosorch.cpp:93, 112` — `m_qos_maps[CFG_EXP_TO_FC_MAP_TABLE_NAME]` / `qos_to_ref_table_map` 登録
- **意味**: DSCP_TO_FC_MAP と EXP_TO_FC_MAP は同一の `processWorkItem()` フレームワーク (`QosMapHandler`) を経由。EXP_TO_FC_MAP も CBF 設定の一部として PORT_QOS_MAP に参照される。両マップの参照カウンタは独立管理

### 4. NhgMapOrch (CBF next-hop group)

- **参照方向**: 間接依存（FC 値の range 制約）
- **条件**: `DscpToFcMapHandler` が FC 値を validate する際に `NhgMapOrch::getMaxNumFcs()` を参照
- **参照元**: `qosorch.cpp:6` (`#include "cbf/nhgmaporch.h"`); `qosorch.cpp:1043`
- **意味**: FC 値は next-hop group map の FC インデックスと対応するため、最大 FC 数の制約は NhgMapOrch が管理する SAI capability に依存

## 参照なし

- CONFIG_DB の他テーブル（DEVICE_METADATA, PORT, BUFFER 系等）は参照なし
- APPL_DB / STATE_DB への暗黙参照なし（qosorch は CONFIG_DB から直接 SAI へ）
- FLEX_COUNTER_DB への参照なし

## evidence

- `qosorch.cpp:80-93` — `m_qos_maps` 初期化（CFG_DSCP_TO_FC_MAP_TABLE_NAME を含む）
- `qosorch.cpp:111` — `qos_to_ref_table_map` での dscp_to_fc → PORT_QOS_MAP 逆参照登録
- `qosorch.cpp:1039-1094` — `convertFieldValuesToAttributes` (FC range チェック)
- `nhgmaporch.cpp:299-325` — `getMaxNumFcs()` (SAI switch query + static cache)
