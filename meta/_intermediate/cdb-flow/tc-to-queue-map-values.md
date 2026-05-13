# TC_TO_QUEUE_MAP — 値依存挙動調査メモ

## ソース

- `sonic-tc-queue-map.yang` (sonic-buildimage@9ea932ec)
- `sonic-swss/orchagent/qosorch.cpp` (QosOrch)

## フィールド値の型

- `tc` (key): `tc_type` (0..7 の uint8)
- `qindex`: string パターン `[0-9]?`（0〜9 の 1 桁数字または空）

## 値依存挙動

| フィールド | 値 | 挙動 |
|-----------|-----|-----|
| `tc` | 0..7 | 有効な Traffic Class インデックス |
| `qindex` | `"0"`..`"9"` | 対応する egress queue インデックスにマッピング |
| `qindex` | 空文字列 | `stoi()` 例外 → `task_invalid_entry`（エントリ破棄） |
| マップ全体 | PORT_QOS_MAP から参照中に DEL | DEL 保留 (`m_pendingRemove=true`)。参照解放まで待機 |
| マップ全体 | PORT_QOS_MAP 参照なし + DEL | SAI `remove_qos_map()` を即時呼び出し |

## enum なし明示

- `tc` / `qindex` は enum 型ではなく数値 / 文字列型。
- TC 範囲: 0〜7（SAI `SAI_QOS_MAP_TYPE_TC_TO_QUEUE` が 0〜7 を定義）。
- queue インデックス範囲: 0〜9（YANG pattern `[0-9]?` から 1 桁制限）。
