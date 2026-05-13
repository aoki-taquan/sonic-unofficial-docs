# SWITCH_TRIMMING — 値依存挙動調査メモ

## ソース

- `sonic-trimming.yang` (sonic-buildimage@9ea932ec)
- `orchagent/switchorch.cpp` (SwitchOrch trimming 拡張)

## フィールド値の型

- `size`: uint32（バイト単位、制約範囲なし）
- `dscp_value`: union — uint8 (0..63) または文字列 `"from-tc"`
- `tc_value`: uint8（制約範囲なし）
- `queue_index`: union — uint8 または文字列 `"dynamic"`

## 値依存挙動

| フィールド | 値 | 挙動 |
|-----------|-----|-----|
| `dscp_value` | `from-tc` | `tc_value` を使い DSCP_TO_TC マッピング逆引きで DSCP を導出。`tc_value` 必須 |
| `dscp_value` | 0..63 (数値) | 指定値をそのままトリミング後パケットの DSCP に設定 |
| `queue_index` | `dynamic` | `dscp_value` から queue を導出 |
| `queue_index` | 0..255 (数値) | 指定インデックスのキューへ送出 |
| `dscp_value=from-tc` + `queue_index=dynamic` | 組み合わせ | YANG は禁止しないが導出元が循環し得るため非推奨 |
| 任意 | DEL | 拒否 (`operation is not supported`) |

## enum なし明示

- `dscp_value` / `queue_index` は enum 型ではなく union 型（数値 + 固定文字列）。
