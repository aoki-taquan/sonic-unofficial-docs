# route-cache — Phase E ハードコード定数スキャンノート

対象テーブル: `APPL_STATE_DB ROUTE_TABLE`（route offload cache）
ファイル: `docs/reference/config-db/route-cache.md`
日付: 2026-05-18

スキャン対象ファイル:
- `sonic-swss/orchagent/routeorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/response_publisher.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/fpmsyncd/fpmsyncd.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/fpmsyncd/routesync.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss-common/common/schema.h` (ref: 158de8d3463ff4b841653f6d57190bb142b80d9c)

---

## 検出した定数一覧

### routeorch.cpp — ECMP 上限デフォルト

```cpp
// routeorch.cpp:37-38
#define DEFAULT_NUMBER_OF_ECMP_GROUPS   128
#define DEFAULT_MAX_ECMP_GROUP_SIZE     32
```

- `DEFAULT_NUMBER_OF_ECMP_GROUPS = 128`: SAI_SWITCH_ATTR_NUMBER_OF_ECMP_GROUPS 取得失敗時の m_maxNextHopGroupCount フォールバック値。
- `DEFAULT_MAX_ECMP_GROUP_SIZE = 32`: Mellanox プラットフォーム補正の除数。`platform` 環境変数に "mellanox" を含む場合に `m_maxNextHopGroupCount /= 32` される（routeorch.cpp:84-87）。

### routeorch.cpp — ResponsePublisher 設定定数

```cpp
// routeorch.cpp:57-58
m_publisher.setBuffered(true);
m_publisher.m_directDbWrite = true;
```

- `setBuffered(true)`: APPL_STATE_DB への書き込みと RESPONSE_CHANNEL 通知を doTask() 末尾の flush() まで Redis パイプラインにバッファリングする。
- `m_directDbWrite = true`: ResponsePublisher が既存エントリとのマージや NULL フィルタリングをスキップして `applStateTable.set()` を直接実行するモード。APPL_STATE_DB への書き込みは常にフルオーバーライトになる。

### response_publisher.cpp — エラー文字列プレフィクス

```cpp
// response_publisher.cpp:18-19
constexpr char *kOrchagentComponent = "[OrchAgent] ";
constexpr char *kSaiComponent = "[SAI] ";
```

通知チャネルの `err_str` フィールドのプレフィクス:
- SAI 由来エラー: `"[SAI] " + status.message()`
- Orchagent 由来エラー: `"[OrchAgent] " + status.message()`
- 成功: `"SWSS_RC_SUCCESS"`（ReturnCode のデフォルト `message()`）

### fpmsyncd.cpp — タイマー・フロー制御定数

```cpp
// fpmsyncd.cpp:24-28
#define INFINITE -1
#define FLUSH_TIMEOUT 500  // 500 milliseconds
static int gFlushTimeout = FLUSH_TIMEOUT;
#define SMALL_TRAFFIC 500
```

```cpp
// fpmsyncd.cpp:46, 51
const uint32_t DEFAULT_ROUTING_RESTART_INTERVAL = 120;
const uint32_t DEFAULT_EOIU_HOLD_INTERVAL = 3;
```

| 定数 | 値 | 単位 | 用途 |
|------|-----|------|------|
| `FLUSH_TIMEOUT` | `500` | ミリ秒 | FPM 受信後のバッファフラッシュ待機上限（fpmsyncd.cpp:350） |
| `SMALL_TRAFFIC` | `500` | メッセージ数/ラウンド | フラッシュ判定の閾値：pending が 500 件以下なら idle >= FLUSH_TIMEOUT 待ちにする（fpmsyncd.cpp:350） |
| `DEFAULT_ROUTING_RESTART_INTERVAL` | `120` | 秒 | warm restart タイマーのデフォルトインターバル（fpmsyncd.cpp:160） |
| `DEFAULT_EOIU_HOLD_INTERVAL` | `3` | 秒 | EOIU（End of Initial Update）受信後の hold インターバル（fpmsyncd.cpp:229） |

### schema.h — テーブル名・チャネル名定数

```cpp
// schema.h:47
#define APP_ROUTE_TABLE_NAME  "ROUTE_TABLE"
```

`APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL` は fpmsyncd.cpp:78 でランタイム文字列結合により生成:
```cpp
const auto routeResponseChannelName = std::string("APPL_DB_") + APP_ROUTE_TABLE_NAME + "_RESPONSE_CHANNEL";
// → "APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL"
```

### routesync.cpp — Warm Restart ハンドラ固定値

```cpp
// routesync.cpp:162
m_warmStartHelper(pipeline, m_routeTable.get(), APP_ROUTE_TABLE_NAME, "bgp", "bgp")
```

Warm Start Helper の `reconcileOp` パラメータは `"bgp"` 固定（第4・第5引数）。Warm restart 時の reconcile 判定に使われる。

```cpp
// routesync.cpp:3285
fieldValues.emplace_back("err_str", "SWSS_RC_SUCCESS");
```

`markRoutesOffloaded()` が RESPONSE_CHANNEL に注入する `err_str` は `"SWSS_RC_SUCCESS"` リテラル固定。

---

## まとめ

| 定数 | 値 | ファイル:行 | 用途 |
|------|-----|------------|------|
| `DEFAULT_NUMBER_OF_ECMP_GROUPS` | `128` | routeorch.cpp:37 | ECMP グループ数フォールバック |
| `DEFAULT_MAX_ECMP_GROUP_SIZE` | `32` | routeorch.cpp:38 | Mellanox 補正除数 |
| `m_directDbWrite` | `true` | routeorch.cpp:58 | APPL_STATE_DB フルオーバーライトモード |
| `FLUSH_TIMEOUT` | `500 ms` | fpmsyncd.cpp:25 | FPM バッファフラッシュ待機上限 |
| `SMALL_TRAFFIC` | `500` | fpmsyncd.cpp:28 | フラッシュ判定閾値 |
| `DEFAULT_ROUTING_RESTART_INTERVAL` | `120 s` | fpmsyncd.cpp:46 | warm restart タイマー |
| `DEFAULT_EOIU_HOLD_INTERVAL` | `3 s` | fpmsyncd.cpp:51 | EOIU hold インターバル |
| `"[SAI] "` | 文字列 | response_publisher.cpp:19 | SAI エラー err_str プレフィクス |
| `"[OrchAgent] "` | 文字列 | response_publisher.cpp:18 | Orchagent エラー err_str プレフィクス |
| `APP_ROUTE_TABLE_NAME` | `"ROUTE_TABLE"` | schema.h:47 | テーブル名定数 |
| `"SWSS_RC_SUCCESS"` | 文字列 | routesync.cpp:3285 | offload 成功通知の固定値 |
