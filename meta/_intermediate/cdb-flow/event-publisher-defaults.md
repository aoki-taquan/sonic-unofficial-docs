# event-publisher / eventd — フィールドデフォルト調査メモ (Phase A)

調査日: 2026-05-14
対象: eventd が `/etc/sonic/init_cfg.json` の `"events"` キーから読む設定パラメータ

## 調査対象ファイル

- `sonic-swss-common/common/events_common.h` — キー定数定義
- `sonic-swss-common/common/events_common.cpp` — `cfg_default` マップ（ハードコードデフォルト）
- `sonic-buildimage/src/sonic-eventd/src/eventd.h` — `HEARTBEAT_INTERVAL_SECS`、`STATS_HEARTBEAT_MIN`、`MAX_CACHE_SIZE` 等の定数
- `sonic-buildimage/src/sonic-eventd/src/eventd.cpp` — `run_eventd_service()` / `stats_collector` 実装

---

## フィールド別 コード由来デフォルト

### `xsub_path`

**コード由来デフォルト**: `"tcp://127.0.0.1:5570"`

```cpp
// events_common.cpp:10
CFG_VAL(XSUB_END_KEY, "tcp://127.0.0.1:5570"),
```

eventd_proxy::run() が `zmq_bind(m_frontend, get_config(XSUB_END_KEY).c_str())` で利用。
パブリッシャー (events_init_publisher) が接続する ZMQ XSUB エンドポイント。

---

### `xpub_path`

**コード由来デフォルト**: `"tcp://127.0.0.1:5571"`

```cpp
// events_common.cpp:11
CFG_VAL(XPUB_END_KEY, "tcp://127.0.0.1:5571"),
```

サブスクライバー (events_init_subscriber) が接続する ZMQ XPUB エンドポイント。

---

### `req_rep_path`

**コード由来デフォルト**: `"tcp://127.0.0.1:5572"`

```cpp
// events_common.cpp:12
CFG_VAL(REQ_REP_END_KEY, "tcp://127.0.0.1:5572"),
```

eventd サービスへの REQ/REP 制御チャネル（キャッシュ操作・オプション取得）。

---

### `capture_path`

**コード由来デフォルト**: `"tcp://127.0.0.1:5573"`

```cpp
// events_common.cpp:13
CFG_VAL(CAPTURE_END_KEY, "tcp://127.0.0.1:5573"),
```

capture_service が接続する内部 PUB エンドポイント。キャッシュ収集に専用。

---

### `stats_upd_secs`

**コード由来デフォルト**: `"5"` (秒)

```cpp
// events_common.cpp:14
CFG_VAL(STATS_UPD_SECS, "5"),
```

stats_collector::run_writer() が COUNTERS_DB に書き込む間隔。実装上は 10ms ポーリングで `m_updated` フラグを確認し、更新があれば書き込む（この定数は文字列として保持されるが実際の sleep は 10ms）。

**注**: `STATS_UPD_SECS` は現在 `eventd.cpp` で直接 sleep に使われておらず、定数として保持のみ。実際の writer スレッドは 10ms 固定 sleep 後に `m_updated` フラグを確認する。

---

### `cache_max_cnt`

**コード由来デフォルト**: `""` → `MAX_CACHE_SIZE` = `MB(100) / EVT_SIZE_AVG` = **699050** (件)

```cpp
// events_common.cpp:15
CFG_VAL(CACHE_MAX_CNT, ""),
// eventd.cpp:31-33
#define MB(N) ((N) * 1024 * 1024)
#define EVT_SIZE_AVG 150
#define MAX_CACHE_SIZE (MB(100) / (EVT_SIZE_AVG))

// eventd.cpp:674
cache_max = get_config_data(string(CACHE_MAX_CNT), (int)MAX_CACHE_SIZE);
```

`CACHE_MAX_CNT` が空文字の場合、`get_config_data()` のテンプレートデフォルト `MAX_CACHE_SIZE = 699050` が使われる。
capture_service のベクタが 699050 件を超えると `CAP_STATE_LAST` モードに移行し、runtime_id ごとの最終イベントのみ保持。

---

### heartbeat_interval (GLOBAL_OPTION_HEARTBEAT)

**コード由来デフォルト**: `2` (秒)

```cpp
// eventd.cpp:43
#define HEARTBEAT_INTERVAL_SECS 2
// eventd.cpp:130
stats_collector::stats_collector() {
    set_heartbeat_interval(HEARTBEAT_INTERVAL_SECS);  // → 2秒
    ...
}
```

`process_options()` で `EVENT_OPTIONS` リクエストが来ると `stats->get_heartbeat_interval()` を返す。
`set_heartbeat_interval(-1)` で無効化可能。
最小分解能: `STATS_HEARTBEAT_MIN = 300` ms。

ハートビートは `sonic-events-eventd:heartbeat` タグで ZMQ Pub ソケットに発行される。
`EVENTD_PUBLISHER_SOURCE = "sonic-events-eventd"`、`EVENTD_HEARTBEAT_TAG = "heartbeat"`。

---

## 設定読み込みパス

```
/etc/sonic/init_cfg.json
  └── "events": {
        "xsub_path": ...,
        "xpub_path": ...,
        "req_rep_path": ...,
        "capture_path": ...,
        "stats_upd_secs": ...,
        "cache_max_cnt": ...
      }
```

`read_init_config()` (events_common.cpp:38-72):
1. `cfg_data = cfg_default` でデフォルト値を設定
2. `/etc/sonic/init_cfg.json` を開き `"events"` キーを検索
3. 各フィールドをファイルの値で上書き（ファイルにキーが無ければデフォルトのまま）

これは CONFIG_DB テーブルではなく、起動時ファイル設定。

---

## 要約表

| フィールド | コード由来デフォルト | 定義箇所 |
|-----------|-------------------|---------|
| `xsub_path` | `"tcp://127.0.0.1:5570"` | `events_common.cpp:10` |
| `xpub_path` | `"tcp://127.0.0.1:5571"` | `events_common.cpp:11` |
| `req_rep_path` | `"tcp://127.0.0.1:5572"` | `events_common.cpp:12` |
| `capture_path` | `"tcp://127.0.0.1:5573"` | `events_common.cpp:13` |
| `stats_upd_secs` | `"5"` (秒) | `events_common.cpp:14` |
| `cache_max_cnt` | `""` → 699050 件 | `events_common.cpp:15` + `eventd.cpp:31-33` |
| heartbeat interval | `2` 秒 | `eventd.cpp:43` + `eventd.cpp:130` |

---

## 特記事項

- `LINGER_TIMEOUT = 100` ms: ZMQ ソケット linger タイムアウト (`events_common.h:54`)
- `MAX_PUBLISHERS_COUNT = 1000`: 同時パブリッシャー上限 (`events_common.h:45`)
- `CACHE_DRAIN_IN_MILLISECS = 1000` ms: capture stop 時のドレイン待機 (`events_common.h:470`)
- `CAPTURE_SOCK_TIMEOUT = 800` ms: capture SUB ソケットの recv タイムアウト (`eventd.cpp:41`)
- `READ_SET_SIZE = 100`: `EVENT_CACHE_READ` 1回あたりの返却件数上限 (`eventd.cpp:36`)
