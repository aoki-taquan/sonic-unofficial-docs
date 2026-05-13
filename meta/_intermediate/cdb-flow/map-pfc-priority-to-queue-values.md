# 値依存挙動分析: MAP_PFC_PRIORITY_TO_QUEUE

## Phase 1: YANG フィールド全列挙

- `name` (string, key): マップ名 `[a-zA-Z0-9]([-a-zA-Z0-9_]{0,31})` 長さ 1..32
- `pfc_priority` (string, inner key): pattern `[0-7]?` — PFC priority 値
- `qindex` (string): pattern `[0-7]?` — egress queue index

## Phase 2: per-value explicit grep

- `pfc_to_queue_map_list.list[ind].key.prio = (uint8_t)stoi(fvField(*i))` — field 値が pfc_priority に対応
- `pfc_to_queue_map_list.list[ind].value.queue_index = (uint8_t)stoi(fvValue(*i))` — value が qindex に対応
- `qos_map_attr.value.s32 = SAI_QOS_MAP_TYPE_PFC_PRIORITY_TO_QUEUE` — SAI に渡す type

## Phase 3: 専用ファイル確認

- `sonic-swss/orchagent/qosorch.cpp`: `handlePfcToQueueTable` → `PfcToQueueHandler::processWorkItem` に委譲
- `qosorch.h`: `const string pfc_to_queue_map_name = "pfc_to_queue_map"`

## Phase 4: 複合条件

- `qindex` ≥ `m_maxNumTC` のとき queue_index 設定エラーとなる可能性 (YANG は 0-7 を保証するが HW 最大 TC 数依存)
- SAI `sai_qos_map_api->create_qos_map()` 失敗 → `SAI_NULL_OBJECT_ID` + `task_failed`

## Phase 5: 値依存挙動マトリクス

| フィールド | 値 | 挙動 |
|-----------|-----|------|
| `pfc_priority` | `0`..`7` | 対応 PFC priority の egress queue を一時停止対象とするマッピングを作成 |
| `pfc_priority` | `""` (空) | YANG pattern `[0-7]?` で許容されるが実運用では無効。QosOrch がスキップ |
| `qindex` | `0`..`7` | 対応 egress queue index を SAI `SAI_QOS_MAP_TYPE_PFC_PRIORITY_TO_QUEUE` に設定 |
| `qindex` | `""` (空) | YANG は許容するが `stoi()` 変換失敗 → `task_invalid_entry` |
| マップ名 `name` | 有効名 (1-32字) | orchagent が SAI qos_map object を作成し PORT_QOS_MAP.pfc_to_queue_map から参照可能に |
| マップ名 `name` | 不正名 | YANG バリデーション拒否 (pattern/length 違反) |

enum なし — `pfc_priority`/`qindex` は数値文字列のみ。
