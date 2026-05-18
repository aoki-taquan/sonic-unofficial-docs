# CONFIG_DB 書込み順依存分析: HEARTBEAT (Phase B)

## 概要

`HEARTBEAT` テーブルは他の CONFIG_DB テーブルとの明示的な外部キー参照を持たない。エントリは `name` (プロセス名) 単位で独立しており、相互依存はない。

## 順序依存の検出

### 1. 起動前書込み推奨
- ソース: `eventd.cpp:130` `set_heartbeat_interval(HEARTBEAT_INTERVAL_SECS)`
- eventd は起動時にデフォルト値 (2 秒) を内部に持つ。CONFIG_DB エントリを起動前に書いておくと初回読み込みで反映される。起動後でも subscribe 通知で自動更新される。

### 2. フィールド同時書込み推奨
- `heartbeat_interval` と `alert_interval` は同一エントリ内のフィールドだが、片方だけ書くと中間状態で `alert_interval < heartbeat_interval` になりえる。
- HSET で複数フィールドを一括書込みすることで回避可能。

### 3. 各エントリは相互独立
- 複数の `HEARTBEAT|<name>` エントリ間に順序依存はない。
