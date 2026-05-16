# HEARTBEAT フィールド暗黙デフォルト調査メモ

調査日: 2026-05-15  
対象テーブル: CONFIG_DB `HEARTBEAT`

## 調査対象ファイル

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-heartbeat.yang`
- `sonic-buildimage/src/sonic-eventd/src/eventd.cpp`
- `sonic-buildimage/src/sonic-eventd/src/eventd.h`
- `sonic-buildimage/src/system-health/health_checker/config.py`
- `sonic-host-services/scripts/hostcfgd` (heartbeat handler は不在)

---

## YANG schema-level デフォルト

`sonic-heartbeat.yang` には `default` 宣言が**存在する**:

```yang
leaf heartbeat_interval {
    type uint32;            // ms 単位
    default "10000";        // 10 秒
}

leaf alert_interval {
    type uint32;            // ms 単位
    default "60000";        // 60 秒
}
```

→ YANG validator 経由 (sonic-mgmt-common / sonic-cfggen YANG モード) で書き込んだ場合、これらの値が暗黙適用される。直接 `sonic-db-cli` で書き込む場合は YANG default は注入されない。

---

## コード由来デフォルト (eventd 内部 heartbeat)

> **注意**: eventd.cpp 側の `interval` は **CONFIG_DB の HEARTBEAT テーブルとは別経路**で、`event_service` の GLOBAL_OPTION_HEARTBEAT (JSON RPC) から設定される。HEARTBEAT テーブルそのものとはスキーマ単位が異なる (秒 vs ミリ秒) ため、本ページ "値依存挙動マトリクス" に既述の通り混同に注意。本節は eventd 側のコード由来デフォルトを列挙する。

### `HEARTBEAT_INTERVAL_SECS` (eventd 初期 interval)

**コード由来デフォルト**: `2` 秒

```cpp
// eventd.cpp:43
#define HEARTBEAT_INTERVAL_SECS 2  /* Default: 2 seconds */
```

`stats_collector` コンストラクタで明示的に呼ばれる:

```cpp
// eventd.cpp:130
set_heartbeat_interval(HEARTBEAT_INTERVAL_SECS);
```

→ `event_service` 経由で GLOBAL_OPTION_HEARTBEAT を上書きしない限り、eventd は 2 秒間隔で heartbeat イベントを publish する。

### `STATS_HEARTBEAT_MIN` (量子化ステップ)

**コード由来デフォルト**: `300` ms

```cpp
// eventd.h:24
#define STATS_HEARTBEAT_MIN 300
```

`set_heartbeat_interval()` は受け取った秒数を `STATS_HEARTBEAT_MIN` (300ms) 単位に切り上げ量子化する:

```cpp
// eventd.cpp:145
(((val * 1000) + STATS_HEARTBEAT_MIN - 1) / STATS_HEARTBEAT_MIN);
```

→ 任意の正値も 300ms ステップに丸められる。指定値と実周期が常に厳密一致しない。

### `m_pause_heartbeat` (pause フラグ)

**コード由来デフォルト**: `false` (atomic bool)

```cpp
// eventd.cpp:127
m_shutdown(false), m_pause_heartbeat(false), m_heartbeats_published(0),
```

→ 起動時は pause されず、稼働中に `heartbeat_ctrl(true)` 呼び出しでのみ停止する。CONFIG_DB に suppress に相当するフィールドは存在しない。

### `val = -1` / `val = 0` の特殊扱い

`set_heartbeat_interval()`:

| 入力値 | 内部挙動 |
|--------|----------|
| `-1` | `interval_count_to_set = 0` → `m_heartbeats_interval_cnt = 0` で publish ループ無効化 (eventd.cpp:152-154) |
| `< -1` | invalid; syslog 記録後リターン |
| `0` | `(0 * 1000 + 299) / 300 = 0` → 同上の 0 量子化に丸まる |
| 正値 | 300ms 量子化 |

---

## system-health 側のデフォルト (関連参考)

`system-health/health_checker/config.py:12-13`:

```python
# Default system health check interval
DEFAULT_INTERVAL = 60
```

`Config.update_config()` で SYSTEM_HEALTH テーブルの `polling_interval` を `DEFAULT_INTERVAL` (60 秒) に fallback (config.py:71)。これは **SYSTEM_HEALTH テーブル**側のデフォルトであり、HEARTBEAT テーブルとは別。HEARTBEAT テーブル自体を読む process monitor が `system-health` 内に明示処理は無く、heartbeat 検査は eventd JSON RPC 経由 / `service_checker` 側の sd_watchdog 経由で行われる。

---

## hostcfgd 側

`sonic-host-services/scripts/hostcfgd` には `HEARTBEAT` テーブルの handler は**存在しない** (`grep -i heartbeat` 0 件)。すなわち CONFIG_DB → hostcfgd 経由のランタイム反映パスは無く、HEARTBEAT テーブルは現状参照されるコンシューマが限定的 (eventd は GLOBAL_OPTION JSON RPC 経由でのみ interval を受ける)。

---

## 要約表

| フィールド | YANG default | コード由来デフォルト | 発生源 |
|-----------|--------------|---------------------|--------|
| `heartbeat_interval` | **`10000`** ms | `10000` ms (YANG default) / eventd 内部経路は `2` 秒 (eventd.cpp:43 `HEARTBEAT_INTERVAL_SECS`) | `sonic-heartbeat.yang:38` |
| `alert_interval` | **`60000`** ms | `60000` ms (YANG default) | `sonic-heartbeat.yang:44` |
| (eventd 内部 `interval`) | n/a | `2` 秒、`STATS_HEARTBEAT_MIN = 300` ms 量子化 | `eventd.cpp:43`, `eventd.h:24` |
| (eventd `m_pause_heartbeat`) | n/a | `false` | `eventd.cpp:127` |

---

## 証拠リンク

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-heartbeat.yang` (`heartbeat_interval` default 10000 / `alert_interval` default 60000)
- `sonic-buildimage/src/sonic-eventd/src/eventd.cpp:43` — `HEARTBEAT_INTERVAL_SECS = 2`
- `sonic-buildimage/src/sonic-eventd/src/eventd.cpp:127-130` — `m_pause_heartbeat(false)` / `set_heartbeat_interval(HEARTBEAT_INTERVAL_SECS)`
- `sonic-buildimage/src/sonic-eventd/src/eventd.cpp:139-161` — `set_heartbeat_interval()` 量子化ロジック
- `sonic-buildimage/src/sonic-eventd/src/eventd.h:24` — `STATS_HEARTBEAT_MIN = 300`
- `sonic-buildimage/src/system-health/health_checker/config.py:12-13` — `DEFAULT_INTERVAL = 60` (関連だが SYSTEM_HEALTH 側)
- `sonic-host-services/scripts/hostcfgd` — HEARTBEAT handler 不在
