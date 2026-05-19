# QUEUE_COUNTER_CAPABILITIES — SET/DEL 副次 DB 書込み調査 (Phase F)

調査対象: `sonic-swss/orchagent/portsorch.cpp` @ master  
関数: `PortsOrch::initCounterCapabilities(sai_object_id_t switchId)` (portsorch.cpp:1850-1967)

## 副次書込み概要

`initCounterCapabilities()` は orchagent 起動時に 1 回だけ呼ばれ、`QUEUE_COUNTER_CAPABILITIES` への書込みと同一関数内で `PORT_COUNTER_CAPABILITIES`（STATE_DB の別テーブル）にも書込む。2 テーブルへの書込みは不可分に実施される。

## STATE_DB への副次書込み

| 操作 | 対象 DB / テーブル | キー | 条件 |
|------|-----------------|------|------|
| SET `isSupported=false` (初期化) | STATE_DB / `PORT_COUNTER_CAPABILITIES` | `WRED_ECN_PORT_WRED_GREEN_DROP_COUNTER` | 常に（orsorch.cpp:1876） |
| SET `isSupported=false` (初期化) | STATE_DB / `PORT_COUNTER_CAPABILITIES` | `WRED_ECN_PORT_WRED_YELLOW_DROP_COUNTER` | 常に（portsorch.cpp:1877） |
| SET `isSupported=false` (初期化) | STATE_DB / `PORT_COUNTER_CAPABILITIES` | `WRED_ECN_PORT_WRED_RED_DROP_COUNTER` | 常に（portsorch.cpp:1878） |
| SET `isSupported=false` (初期化) | STATE_DB / `PORT_COUNTER_CAPABILITIES` | `WRED_ECN_PORT_WRED_TOTAL_DROP_COUNTER` | 常に（portsorch.cpp:1879） |
| SET `isSupported=true` | STATE_DB / `PORT_COUNTER_CAPABILITIES` | `WRED_ECN_PORT_WRED_GREEN_DROP_COUNTER` | SAI_OBJECT_TYPE_PORT クエリ成功時、SAI_PORT_STAT_GREEN_WRED_DROPPED_PACKETS 確認時（portsorch.cpp:1943） |
| SET `isSupported=true` | STATE_DB / `PORT_COUNTER_CAPABILITIES` | `WRED_ECN_PORT_WRED_YELLOW_DROP_COUNTER` | SAI_OBJECT_TYPE_PORT クエリ成功時、SAI_PORT_STAT_YELLOW_WRED_DROPPED_PACKETS 確認時（portsorch.cpp:1948） |
| SET `isSupported=true` | STATE_DB / `PORT_COUNTER_CAPABILITIES` | `WRED_ECN_PORT_WRED_RED_DROP_COUNTER` | SAI_OBJECT_TYPE_PORT クエリ成功時、SAI_PORT_STAT_RED_WRED_DROPPED_PACKETS 確認時（portsorch.cpp:1953） |
| SET `isSupported=true` | STATE_DB / `PORT_COUNTER_CAPABILITIES` | `WRED_ECN_PORT_WRED_TOTAL_DROP_COUNTER` | SAI_OBJECT_TYPE_PORT クエリ成功時、SAI_PORT_STAT_WRED_DROPPED_PACKETS 確認時（portsorch.cpp:1958） |

## ポイント

- **不可分 2 テーブル書込み**: `QUEUE_COUNTER_CAPABILITIES` と `PORT_COUNTER_CAPABILITIES` は同一 `initCounterCapabilities()` 呼び出し内で書き込まれる。一方が書かれれば他方も書かれる。ただし SAI クエリは `SAI_OBJECT_TYPE_QUEUE` と `SAI_OBJECT_TYPE_PORT` の 2 回独立して実行されるため、一方のクエリが失敗しても他方の書込みには影響しない。
- **portstat.py の依存**: `sonic-utilities/utilities_common/portstat.py` の `__init__` は `PORT_COUNTER_CAPABILITIES|*` エントリの `isSupported` を参照して、COUNTERS_DB から取得するポートカウンタ列を絞り込む（portstat.py:297-312）。`QUEUE_COUNTER_CAPABILITIES` を書き込む orchagent が停止中は `PORT_COUNTER_CAPABILITIES` も未書込みのため、portstat の WRED 列が N/A 表示となる。
- **DEL 操作なし**: `initCounterCapabilities()` は SET 専用。既存エントリの DEL は行わない。orchagent 再起動時は上書き SET のみで、古いエントリが残留しても問題ない（値は同一または更新値）。

## 参照元

- `sonic-swss/orchagent/portsorch.cpp:1850-1967` — `initCounterCapabilities()` 実装  
  <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/portsorch.cpp>
- `sonic-utilities/utilities_common/portstat.py:297-312` — `PORT_COUNTER_CAPABILITIES` 参照箇所  
  <https://github.com/sonic-net/sonic-utilities/blob/master/utilities_common/portstat.py>
