# CONSOLE_PORT / CONSOLE_SWITCH 値依存挙動分析

## enum フィールド
1. `flow_control`: `"0"` / `"1"` (string boolean)
2. `enabled` (CONSOLE_SWITCH): `yes` / `no`

## 値依存挙動

### CONSOLE_SWITCH.enabled
- `yes`: console switch サービスが起動し、consutil / picocom 経由でのシリアル接続が有効になる。
- `no` (既定): console switch 機能が無効。ポート設定が存在しても接続不能。

### CONSOLE_PORT.flow_control
- `"1"`: picocom 起動時にハードウェアフロー制御 (RTS/CTS) を有効化。
- `"0"`: フロー制御なし（多くの console 接続はこちら）。

### CONSOLE_PORT.escape_char vs CONSOLE_SWITCH.default_escape_char
- ポート個別の `escape_char` が設定されている場合、`default_escape_char` を上書きする。
- 未設定の場合はグローバル default (`default_escape_char`) が使われる。

## ソース
- YANG: `sonic-console.yang`
- `consutil` (sonic-utilities)
