# console-port — Phase C cross-refs 調査メモ

## 調査対象

- `sonic-utilities/consutil/lib.py`
- `sonic-utilities/config/console.py`

## 参照関係

### CONSOLE_PORT → CONSOLE_SWITCH (intra-group)

`consutil/lib.py:91` で `CONSOLE_SWITCH|console_mgmt` の `enabled` / `default_escape_char` を読み取る。
`CONSOLE_PORT` エントリの利用は常に `CONSOLE_SWITCH` の有効化フラグ確認を伴う。

### CONSOLE_PORT → STATE_DB.CONSOLE_PORT (bidirectional)

- **書き込み方向**: `ConsolePortState` クラス (lib.py:374-380) が接続確立時に `STATE_DB|CONSOLE_PORT|<line>` に `state`, `pid`, `start_time` を書き込む。
- **読み取り方向**: `LinksDb._get_all_ports()` (lib.py:120) が `state_db.get_all(STATE_DB, "CONSOLE_PORT|<k>")` で現在の接続状態を取得し、`show console` 表示に使う。

### 参照なし（外部テーブル）

- `DEVICE_METADATA`, `FEATURE`, `AAA` への参照は存在しない（consutil は独自の `CONSOLE_SWITCH.enabled` チェックのみ）。

## 結論

`CONSOLE_PORT` の暗黙テーブル参照は以下の 2 本:
1. `CONSOLE_SWITCH|console_mgmt` — enabled ガードと default_escape_char 取得
2. `STATE_DB.CONSOLE_PORT|<line>` — 双方向: 接続状態の書き込み + show 時の読み取り
