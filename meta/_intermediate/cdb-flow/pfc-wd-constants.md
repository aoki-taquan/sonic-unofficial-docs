# PFC_WD — Phase E ハードコード定数スキャンノート

対象テーブル: `PFC_WD`
Consumer: `orchagent` / `PfcWdOrch` / `PfcWdSwOrch` (`sonic-swss/orchagent/pfcwdorch.cpp`)
スキャン範囲: `pfcwdorch.cpp:1-30`, `orchdaemon.cpp:24`, `sonic-swss-common/common/schema.h:284-320`

---

## フィールド名マクロ（`sonic-swss/orchagent/pfcwdorch.cpp:14-29`）

| マクロ | 値 | evidence |
|--------|----|----------|
| `PFC_WD_GLOBAL` | `"GLOBAL"` | `pfcwdorch.cpp:14` |
| `PFC_WD_ACTION` | `"action"` | `pfcwdorch.cpp:15` |
| `PFC_WD_DETECTION_TIME` | `"detection_time"` | `pfcwdorch.cpp:16` |
| `PFC_WD_RESTORATION_TIME` | `"restoration_time"` | `pfcwdorch.cpp:17` |
| `PFC_STAT_HISTORY` | `"pfc_stat_history"` | `pfcwdorch.cpp:18` |
| `BIG_RED_SWITCH_FIELD` | `"BIG_RED_SWITCH"` | `pfcwdorch.cpp:19` |
| `PFC_WD_IN_STORM` | `"storm"` | `pfcwdorch.cpp:20` |

## 数値定数（`pfcwdorch.cpp:22-29`）

| マクロ | 値 | 用途 |
|--------|----|------|
| `PFC_WD_DETECTION_TIME_MAX` | `5000` ms | `detection_time` 上限（YANG range と一致） |
| `PFC_WD_DETECTION_TIME_MIN` | `100` ms | `detection_time` 下限 |
| `PFC_WD_RESTORATION_TIME_MAX` | `60000` ms | `restoration_time` 上限 |
| `PFC_WD_RESTORATION_TIME_MIN` | `100` ms | `restoration_time` 下限 |
| `PFC_WD_POLL_TIMEOUT` | `5000` ms | Consumer ポーリングタイムアウト |
| `PFC_WD_TC_MAX` | `8` | サポートする最大 TC (Traffic Class) 数 |
| `COUNTER_CHECK_POLL_TIMEOUT_SEC` | `1` 秒 | カウンタチェック周期 |

## ポーリング初期値（`sonic-swss/orchagent/orchdaemon.cpp:24`）

| マクロ | 値 | 用途 |
|--------|----|------|
| `PFC_WD_POLL_MSECS` | `100` ms | orchagent 起動時のデフォルトポーリング間隔（`PFC_WD|GLOBAL` の `POLL_INTERVAL` で上書き可） |

## テーブル名マクロ（`sonic-swss-common/common/schema.h`）

| マクロ | 値 | evidence |
|--------|----|----------|
| `APP_PFC_WD_TABLE_NAME` | `"PFC_WD_TABLE"` | `schema.h:53` |
| `PFC_WD_POLL_MSECS` | `100` | `schema.h:284`（orchdaemon.cpp:24 と同値） |
| `PFC_WD_STATE_TABLE` | `"PFC_WD_STATE_TABLE"` | `schema.h:296` |
| `PFC_WD_PORT_COUNTER_ID_LIST` | `"PORT_COUNTER_ID_LIST"` | `schema.h:297` |
| `PFC_WD_QUEUE_COUNTER_ID_LIST` | `"QUEUE_COUNTER_ID_LIST"` | `schema.h:298` |
| `PFC_WD_QUEUE_ATTR_ID_LIST` | `"QUEUE_ATTR_ID_LIST"` | `schema.h:299` |
| `POLL_INTERVAL_FIELD` | `"POLL_INTERVAL"` | `schema.h:320` |

## action 文字列マッピング（`pfcwdorch.cpp:147-169`）

```cpp
// pfcStrToAction (pfcwdorch.cpp:147-154)
{ "forward", PFC_WD_ACTION_FORWARD }
{ "drop",    PFC_WD_ACTION_DROP }
{ "alert",   PFC_WD_ACTION_ALERT }
// その他 → PFC_WD_ACTION_UNKNOWN

// pfcActionToStr (pfcwdorch.cpp:167-169)
{ PFC_WD_ACTION_FORWARD, "forward" }
{ PFC_WD_ACTION_DROP,    "drop" }
{ PFC_WD_ACTION_ALERT,   "alert" }
```

これらの文字列以外が `action` フィールドに設定されると `task_invalid_entry` 扱い。
