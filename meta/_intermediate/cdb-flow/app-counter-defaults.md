# app-counter Phase A — implicit defaults (code-derived)

Generated: 2026-05-15
Target doc: docs/reference/config-db/app-counter.md

## 概要

`FLOW_COUNTER_ROUTE_PATTERN` (CONFIG_DB) と `FLEX_COUNTER_TABLE|FLOW_CNT_TRAP` / `FLEX_COUNTER_TABLE|FLOW_CNT_ROUTE` を通じてアプリケーションレベルのフローカウンタ（HostIf Trap / Route）を制御するフィールドのコード由来デフォルト分析。これらのカウンタは COUNTERS_DB に書き込まれる。

## Field-by-field analysis

### FLOW_COUNTER_ROUTE_PATTERN|<vrf>|<prefix> (CONFIG_DB)

| フィールド | 詳細 |
|-----------|------|
| `max_match_count` | ユーザーが設定しない場合は `ROUTE_PATTERN_DEFAULT_MAX_MATCH_COUNT = 30`（flowcounterrouteorch.cpp:25）がハードコードデフォルト。CLI の `--max` オプションでも `default=30` が指定されている（config/flow_counters.py:29）。 |
| キー形式 | `<prefix>` のみ（デフォルト VRF）または `<vrf_name>\|<prefix>` 形式。`PATTERN_SEPARATOR = "|"` で区切られる（flow_counter_util/route.py:25）。 |
| 対応 IP バージョン制限 | IPv4 パターンは同時に 1 件、IPv6 パターンは同時に 1 件のみ有効。超過分は CLI レベルで既存パターンを置換する（config/flow_counters.py:150-156）。ただし CONFIG_DB を直接編集すれば制限はなく、orchagent がすべて処理を試みる。 |

### FLEX_COUNTER_TABLE|FLOW_CNT_TRAP (CONFIG_DB) → HOSTIF_TRAP_FLOW_COUNTER グループ

| フィールド | 詳細 |
|-----------|------|
| `FLEX_COUNTER_STATUS` | 未設定時は `disable`（orchagent 起動時 `m_hostif_trap_counter_enabled = false`、flexcounterorch.h:66 相当）。`enable` を受信すると `gCoppOrch->enableFlowCounter()` が呼ばれ Trap カウンタが COUNTERS_DB に登録される。 |
| `POLL_INTERVAL` | `HOSTIF_TRAP_COUNTER_POLLING_INTERVAL_MS = 10000`（copporch.cpp:189）がハードコード初期値。CONFIG_DB の `POLL_INTERVAL` で上書き可能。`counterpoll show` は `FLOW_CNT_TRAP_STAT` の POLL_INTERVAL 未設定時に `"default (10000)"` を表示する（counterpoll/main.py:19）。 |
| Lua プラグイン登録 | `setFlexCounterGroupParameter(HOSTIF_TRAP_COUNTER_FLEX_COUNTER_GROUP, ..., FLOW_COUNTER_PLUGIN_FIELD, trapSha)` によって PPS 計算 Lua スクリプトが `FLEX_COUNTER_DB` に登録される（copporch.cpp:1389-1392）。プラグインは `POLL_INTERVAL` と同期して周期実行。 |

### FLEX_COUNTER_TABLE|FLOW_CNT_ROUTE (CONFIG_DB) → ROUTE_FLOW_COUNTER グループ

| フィールド | 詳細 |
|-----------|------|
| `FLEX_COUNTER_STATUS` | 未設定時は `disable`（`m_route_flow_counter_enabled = false`、flexcounterorch.h:75）。`enable` を受信すると `gFlowCounterRouteOrch->generateRouteFlowStats()` が呼ばれ、設定済みルートパターンにマッチする経路にカウンタが紐付けられる。 |
| `POLL_INTERVAL` | `ROUTE_FLOW_COUNTER_POLLING_INTERVAL_MS = 10000`（flowcounterrouteorch.cpp:26）がハードコード初期値。CONFIG_DB の `POLL_INTERVAL` で上書き可能。`counterpoll show` は `FLOW_CNT_ROUTE_STAT` 未設定時に `"default (10000)"` を表示（counterpoll/main.py:19）。 |
| SAI 能力チェック | `FLOW_CNT_ROUTE` は `FlowCounterHandler::queryRouteFlowCounterCapability()` が `SAI_ROUTE_ENTRY_ATTR_COUNTER_ID` の `set_implemented` を確認する（flow_counter_handler.cpp:53-61）。能力なし → `mRouteFlowCounterSupported = false` → `enable` を受信しても `generateRouteFlowStats()` は実行されない（flexcounterorch.cpp:324-334 の条件分岐）。 |

### COUNTERS_DB への書き込み経路（参考）

| エントリ | 書き込み元 |
|---------|-----------|
| `COUNTERS_TRAP_NAME_MAP` | copporch が Trap グループ初期化時に trap 名 → OID マップを書き込む（copporch.cpp:1456）。 |
| `COUNTERS:<trap_oid>` | syncd FlexCounter が `HOSTIF_TRAP_FLOW_COUNTER` グループの `FLOW_COUNTER_ID_LIST`（`SAI_COUNTER_STAT_PACKETS`, `SAI_COUNTER_STAT_BYTES`）を周期収集して書き込む。 |
| `COUNTERS_ROUTE_NAME_MAP` | flowcounterrouteorch が route 追加時にプレフィックス → OID マップを書き込む。 |
| `COUNTERS_ROUTE_TO_PATTERN_MAP` | flowcounterrouteorch がルートパターンへの対応付けを書き込む。 |
| `COUNTERS:<route_counter_oid>` | syncd FlexCounter が `ROUTE_FLOW_COUNTER` グループの `FLOW_COUNTER_ID_LIST`（`SAI_COUNTER_STAT_PACKETS`, `SAI_COUNTER_STAT_BYTES`）を周期収集して書き込む。 |

## 検出された discrepancy / 暗黙挙動まとめ

1. **SAI 能力依存の silent skip**: `FLOW_CNT_ROUTE` を `enable` にしてもプラットフォームが `SAI_ROUTE_ENTRY_ATTR_COUNTER_ID` をサポートしていない場合は何も起きない。`counterpoll show` では `enable` に見えるが実カウンタは存在しない。
2. **IPv4/IPv6 各 1 パターン制限は CLI のみ**: CONFIG_DB を直接編集すれば複数パターン登録可能。ただし orchagent は全パターンを処理する。
3. **`max_match_count` のデフォルト 30**: CLI も orchagent も同一の 30 を使用しているが、別々にハードコードされている（CLI 側は Python、orchagent 側は C++ の定数）。
4. **FLEX_COUNTER_UPD_INTERVAL = 1 秒のタイマー**: flowcounterrouteorch は COUNTERS_DB への書き込みを 1 秒タイマーで非同期に実施する（flowcounterrouteorch.cpp:21, 43-46）。`enable` 直後の数秒間はカウンタが COUNTERS_DB に存在しない場合がある。
