# route-orch-event: Phase E — 埋め込み定数

## 調査対象

- `orchagent/routeorch.cpp`
- `orchagent/orchdaemon.cpp`
- `fpmsyncd/fpmsyncd.cpp`

## 検出された埋め込み定数

### routeorch.cpp

| 定数 | 値 | 用途 |
|------|-----|------|
| `DEFAULT_NUMBER_OF_ECMP_GROUPS` | `128` | SAI から ECMP グループ数を取得できない場合のフォールバック上限 |
| `DEFAULT_MAX_ECMP_GROUP_SIZE` | `32` | Mellanox プラットフォームで ECMP グループ数を再計算する際の除数 |

### orchdaemon.cpp

| 定数 | 値 | 用途 |
|------|-----|------|
| `routeorch_pri` | `5` | `APP_ROUTE_TABLE_NAME` / `APP_LABEL_ROUTE_TABLE_NAME` の Consumer 優先度 |
| `SELECT_TIMEOUT` | `1000` (ms) | OrchDaemon のセレクトループタイムアウト。`publishRouteState()` バッファが `flush()` なしで残留した場合の最大遅延 |
| `DEFAULT_MAX_BULK_SIZE` | `1000` | `gMaxBulkSize` の初期値。SAI バルク操作（`gRouteBulker`）の最大エントリ数 |
| VoQ ECMP 上限 | `128` | `gMySwitchType == "voq"` かつ SAI が返す `MAX_ECMP_MEMBER_COUNT >= 128` の場合に強制的に設定する VoQ 用上限値 |

### fpmsyncd.cpp

| 定数 | 値 | 用途 |
|------|-----|------|
| `routeResponseChannelName` | `"APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL"` | fpmsyncd が購読する Pub/Sub チャンネル名（`"APPL_DB_" + APP_ROUTE_TABLE_NAME + "_RESPONSE_CHANNEL"` として動的生成） |

## 備考

- `routeorch_pri = 5` は `portsorch_base_pri = 40` や `fgnhgorch_pri = 15` より低い値であり、RouteOrch は orchList の中で低優先度 Consumer として動作する
- `DEFAULT_NUMBER_OF_ECMP_GROUPS = 128` は SAI クエリ失敗時のみ使用される
- `DEFAULT_MAX_ECMP_GROUP_SIZE = 32` は Mellanox 固有のワークアラウンドであり、プラットフォーム文字列 `MLNX_PLATFORM_SUBSTRING` を含む環境でのみ適用される
- `SELECT_TIMEOUT = 1000 ms` は `m_publisher.flush()` が `doTask()` 内で確実に呼ばれる設計のため通常問題にならないが、`doTask()` が呼ばれずにタイムアウトした場合は最大 1 秒の追加遅延が発生する
