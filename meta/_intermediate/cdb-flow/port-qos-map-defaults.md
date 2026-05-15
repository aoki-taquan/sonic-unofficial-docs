# PORT_QOS_MAP — Phase A: コード由来の暗黙デフォルト調査

調査日: 2026-05-14  
対象ページ: `docs/reference/config-db/port-qos-map.md`

## 調査方法

1. `grep PORT_QOS_MAP` でソース特定 (1 回)
2. 以降は LSP 相当の全行精読:
   - `sonic-swss/orchagent/qosorch.cpp` (handlePortQosMapTable, 2046-2224 行)
   - `sonic-buildimage/files/build_templates/qos_config.j2` (414-484 行)
   - `sonic-utilities/scripts/db_migrator.py` (700-715 行)
   - `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-port-qos-map.yang` (全行)

## フィールド別 暗黙デフォルト

### 共通前提

YANG に `default` 文なし。全フィールド optional。エントリが存在しない場合、QosOrch は何も SAI へ設定しない (SAI の初期値が適用される)。

### `tc_to_pg_map` / `tc_to_queue_map` / `pfc_to_queue_map` / `pfc_to_pg_map` / `dscp_to_tc_map` / `tc_to_dscp_map` / `dot1p_to_tc_map` / `scheduler`

- **YANG default**: なし (optional leafref)
- **ランタイムデフォルト**: フィールド未設定時 → `resolveFieldRefValue` が呼ばれない → SAI 属性未変更 → **SAI 側の初期値 (通常は SAI_NULL_OBJECT_ID = map なし)** が維持される
- **DEL 時**: `SAI_NULL_OBJECT_ID` を set (明示的にクリア)
- **ビルド時デフォルト** (`qos_config.j2`):
  - `dscp_to_tc_map`: `"AZURE"` (backend/storage device は `dot1p_to_tc_map: "AZURE"` に変わる)
  - `tc_to_queue_map`: `"AZURE"` (uplink DualToR 等は `"AZURE_UPLINK"`)
  - `tc_to_pg_map`: `"AZURE"` (DPC port は `"AZURE_DPC"`)
  - `pfc_to_queue_map`: `"AZURE"` (SERVICE port には付与しない)
  - `pfc_to_pg_map`: `"AZURE"` (対応 ASIC のみ; DualToR uplink は `"AZURE_DUALTOR"`)
  - `tc_to_dscp_map`: 付与なし (j2 テンプレート内に記述なし)
  - `dot1p_to_tc_map`: backend/storage device のみ `"AZURE"`
  - `scheduler`: 付与なし

### `pfc_enable`

- **YANG default**: なし (optional string pattern `([0-7](,[0-7])*)?`)
- **ランタイムデフォルト**: フィールド未設定 → `pfc_enable` ローカル変数が `0` のまま → `if (pfc_enable || old_pfc_enable)` で false なら `setPortPfc` 未呼び出し → **ポートの現状 PFC bitmap が維持される**
- **ビルド時デフォルト** (`qos_config.j2`):
  - 通常ポート: `LOSSLESS_TC` join (典型値 `"3,4"`)
  - DualToR uplink / extra_queues ポート: `"2,3,4,6"`
  - DPC ポートおよび SERVICE ポート: 付与なし

### `pfcwd_sw_enable`

- **YANG default**: なし (optional string pattern `([0-7](,[0-7])*)?`)
- **ランタイムデフォルト**: フィールド未設定 → `pfcwd_sw_enable` 変数が `0` → `setPortPfcWatchdogStatus(..., 0)` が **無条件に呼ばれる** (line 2224)。すなわち PFC watchdog は **常に 0 (全無効) にリセットされる** — フィールドを明示しないと watchdog がクリアされる副作用あり
- **ビルド時デフォルト** (`qos_config.j2`):
  - 通常ポート (non-DPC, non-SERVICE): `LOSSLESS_TC` join (典型値 `"3,4"`)
  - DPC / SERVICE ポート: 付与なし

### `global` エントリの `dscp_to_tc_map` (db_migrator)

- `migrate_port_qos_map_global()` が Broadcom ASIC 限定で `PORT_QOS_MAP|global` に `dscp_to_tc_map` を自動挿入 (既存の場合はスキップ)
- 挿入値: `DSCP_TO_TC_MAP` テーブルの最初のキー (典型: `"AZURE"`)

## 重要な非自明動作

1. `pfcwd_sw_enable` は **フィールド未設定でも常に 0 として SAI/ポーツOrch に渡される**。これは `pfc_enable` の挙動 (条件付きスキップ) と非対称。
2. DEL 操作は全 map を `SAI_NULL_OBJECT_ID` にリセット + `setPortPfc(0)` を呼ぶが、`setPortPfcWatchdogStatus` は呼ばれない。
3. ビルド時デフォルト名 `"AZURE"` はハードコード文字列であり、その map が CONFIG_DB に存在しなければ QosOrch は `task_need_retry` を返す。

## 証跡

| 証跡 | ファイル:行 |
|------|-----------|
| pfc_enable/pfcwd_sw_enable 初期化 | qosorch.cpp:2113-2114 |
| pfc_enable 条件付き適用 | qosorch.cpp:2213-2220 |
| pfcwd_sw_enable 無条件 set | qosorch.cpp:2224 |
| ビルド時デフォルト値 | qos_config.j2:432-480 |
| db_migrator global 挿入 | db_migrator.py:711-714 |
