# route-cache-defaults.md — Phase A: APPL_STATE_DB ROUTE_TABLE コード由来デフォルト

調査日: 2026-05-15
対象テーブル: APPL_STATE_DB `ROUTE_TABLE`（テーブル名定数: `APP_ROUTE_TABLE_NAME = "ROUTE_TABLE"`）

調査対象ファイル:
- `sonic-swss/orchagent/routeorch.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d
- `sonic-swss/orchagent/response_publisher.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d
- `sonic-swss/orchagent/response_publisher.h` @ 4305596156d70e9797e8a881b3d19b46de0bce0d
- `sonic-swss/orchagent/routeorch.h` @ 4305596156d70e9797e8a881b3d19b46de0bce0d
- `sonic-swss/fpmsyncd/fpmsyncd.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d
- `sonic-swss/fpmsyncd/routesync.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d
- `sonic-swss-common/common/schema.h` @ 158de8d3463ff4b841653f6d57190bb142b80d9c

---

## 1. テーブル概要

APPL_STATE_DB `ROUTE_TABLE` は APPL_DB `ROUTE_TABLE` の「確定状態キャッシュ」。
`orchagent` の `RouteOrch` が SAI 経路プログラム成功後に `ResponsePublisher::publish()` 経由で書き込む。
Consumer（購読者）は `fpmsyncd` で、route offload 通知を受けて FRR zebra にフィードバックする。

APPL_DB `ROUTE_TABLE` と APPL_STATE_DB `ROUTE_TABLE` は **同じテーブル名・同じキー構造**だが、
格納 DB が異なる（DB インデックス 0 vs 14）。

```
schema.h:
  #define APPL_DB          0
  #define APPL_STATE_DB   14
  #define APP_ROUTE_TABLE_NAME  "ROUTE_TABLE"
```

---

## 2. 書き込みロジック — `RouteOrch::publishRouteState()`

ソース: `sonic-swss/orchagent/routeorch.cpp` lines 3185–3202

```cpp
void RouteOrch::publishRouteState(const RouteBulkContext& ctx, const ReturnCode& status)
{
    std::vector<FieldValueTuple> fvs;

    /* Leave the fvs empty if the operation type is "DEL".
     * An empty fvs makes ResponsePublisher::publish() remove the state entry from APPL_STATE_DB
     */
    if (ctx.is_set)
    {
        fvs.emplace_back("protocol", ctx.protocol);
    }

    const bool replace = false;

    m_publisher.publish(APP_ROUTE_TABLE_NAME, ctx.key, fvs, status, replace);
}
```

呼ばれるタイミング:
- SET 操作: routeorch.cpp L923, L1050, L1090, L2729, L2970
- DEL 操作: routeorch.cpp L3192（fvs が空 → エントリ削除）

---

## 3. `ResponsePublisher::publish()` によるフィールド追加

ソース: `sonic-swss/orchagent/response_publisher.cpp` lines 96–150

```cpp
void ResponsePublisher::publish(
    const std::string &table, const std::string &key,
    const std::vector<FieldValueTuple> &intent_attrs, const ReturnCode &status,
    bool replace)
{
    std::vector<FieldValueTuple> state_attrs;
    if (status.ok())
    {
        state_attrs = intent_attrs;  // intent_attrs を state_attrs としてそのまま使用
    }
    publish(table, key, intent_attrs, status, state_attrs, replace);
}
```

2 引数版 `publish()` では:
- ステータスが OK の場合 → `intent_attrs`（= `fvs`）をそのまま APPL_STATE_DB に書き込む
- ステータスが error の場合 → state_attrs が空となり DB 書き込みをスキップ

通知チャネル (`APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL`) には `err_str` が先頭フィールドとして追加される:

```cpp
// response_publisher.cpp:102
swss::FieldValueTuple err_str("err_str", PrependedComponent(status) + status.message());
intent_attrs_copy.insert(intent_attrs_copy.begin(), err_str);
```

---

## 4. APPL_STATE_DB ROUTE_TABLE フィールド別 コード由来デフォルト

### 4-1. `protocol` フィールド

**コード由来デフォルト**: `""` (空文字列)

```cpp
// routeorch.h RouteBulkContext 構造体 (line 157-160)
RouteBulkContext(const std::string& key, bool is_set)
    : key(key), excp_intfs_flag(false), using_temp_nhg(false), is_set(is_set),
      fallback_to_default_route(false), retry_cst(DUMMY_CONSTRAINT)
{
}
```

`protocol` メンバーは宣言のみで初期値を明示しないため、`std::string` のデフォルトコンストラクタにより `""` となる。

フィールドの設定条件:
```cpp
// routeorch.cpp:785-788
if (fvField(i) == "protocol" && fvValue(i) != "")
{
    ctx.protocol = fvValue(i);
}
```

APPL_DB の `ROUTE_TABLE` エントリに `protocol` が存在しない or 空の場合、`ctx.protocol = ""`。
その場合 APPL_STATE_DB には `protocol=""` として書き込まれる（空文字列フィールド）。

**重要**: `m_publisher.m_directDbWrite = true`（routeorch.cpp:58）のため、
`ResponsePublisher::writeToDBInternal()` は `applStateTable.set(key, attrs)` を直接実行し、
既存エントリとのマージや NULL フィルタリングを行わない。

### 4-2. `err_str` フィールド

**コード由来デフォルト**: APPL_STATE_DB には書き込まれない（通知チャネル専用）

`err_str` は `NotificationProducer` の通知メッセージにのみ付与される。
APPL_STATE_DB の実エントリ（`state_attrs`）には含まれない。

成功時の通知値: `"SWSS_RC_SUCCESS"`  
SAI エラー時: `"[SAI] " + status.message()`  
Orchagent エラー時: `"[OrchAgent] " + status.message()`

---

## 5. SET vs DEL 動作の違い

| 操作 | fvs の内容 | APPL_STATE_DB への書き込み |
|------|-----------|--------------------------|
| SET (is_set=true) | `[("protocol", ctx.protocol)]` | エントリを SET（成功時のみ） |
| DEL (is_set=false) | `[]`（空） | エントリを DEL（成功時のみ） |

`ResponsePublisher` の書き込み条件（response_publisher.cpp:129-133）:
```cpp
if (m_enable_db_write_and_notify &&
     ((intent_attrs.size() && state_attrs.size()) ||
     (status.ok() && !intent_attrs.size()))) {
        writeToDB(table, key, state_attrs, intent_attrs.size() ? SET_COMMAND : DEL_COMMAND, replace);
}
```

- `intent_attrs.size() > 0` かつ `state_attrs.size() > 0` → SET コマンドで書き込み
- `intent_attrs.size() == 0` かつ `status.ok()` → DEL コマンドでエントリ削除

---

## 6. fpmsyncd の消費ロジック — `onRouteResponse()`

ソース: `sonic-swss/fpmsyncd/routesync.cpp` lines 3165–3265

`fpmsyncd` は `APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL` を Listen し、通知を受信すると `onRouteResponse()` を呼び出す。

**route suppression が有効な場合のみ動作** (`isSuppressionEnabled()` が true の場合):

```cpp
// routesync.cpp:3174-3177
if (!isSuppressionEnabled())
{
    return;
}
```

フィールド処理ロジック:
```cpp
for (const auto& fieldValue: fieldValues)
{
    if (field == "err_str")
        isSuccessReply = (value == "SWSS_RC_SUCCESS");
    else if (field == "protocol")
        isSetOperation = true;  // protocol フィールドがあれば SET 操作とみなす
        protocol = value;
}
```

`protocol` フィールドの不在は DEL 操作の識別に使用される。
`err_str != "SWSS_RC_SUCCESS"` の場合は offload 通知をスキップ。
`protocol` が空文字列の場合も offload 通知をスキップ（L3224-3229）。

---

## 7. Warm Restart 時の動作

ソース: `sonic-swss/fpmsyncd/routesync.cpp` lines 3291–3312

Warm restart 完了後、`onWarmStartEnd()` で `markRoutesOffloaded()` が呼ばれる。
これは APPL_STATE_DB の全 ROUTE_TABLE エントリを読み取り、zebra に offload 通知を一括送信する。

```cpp
void RouteSync::markRoutesOffloaded(swss::DBConnector& db)
{
    sendOffloadReply(db, APP_ROUTE_TABLE_NAME);
}
```

---

## 8. フィールドまとめ

| フィールド | コード由来デフォルト | 書込み元 | 書込み条件 |
|-----------|-------------------|---------|-----------|
| `protocol` | `""` (空文字列) | `RouteOrch::publishRouteState()` | SET 操作時のみ。DEL 時はエントリ削除 |
| `err_str` | ― (APPL_STATE_DB 非書込み) | 通知チャネル専用 | 全操作で通知チャネルに送信 |

---

## 9. 注意点・発見した特性

1. **`m_directDbWrite = true` による直接書き込み**: routeorch の `ResponsePublisher` インスタンスは `m_directDbWrite = true` で初期化されるため、既存エントリのマージや NULL フィルタリングが行われない（`applStateTable.set(key, attrs)` を直接実行）。

2. **`replace = false`**: `publishRouteState()` は `replace = false` で publish を呼ぶ。これは `writeToDBInternal()` で `del + set` ではなく単純 `set` を使うことを意味する（ただし `m_directDbWrite=true` のため `replace` 引数は実質無効）。

3. **`protocol=""` の扱い**: `fpmsyncd` の `onRouteResponse()` は `protocol` フィールドが存在しない場合に DEL 操作とみなす。`protocol=""` は「フィールドあり = SET 操作」だが、続く L3224 で protocol が空文字列の場合は offload 通知をスキップする。

4. **SAI 操作失敗時は書き込まれない**: `ResponsePublisher` は `status.ok()` の場合のみ APPL_STATE_DB に書き込む。SAI エラー時はエントリが残ったままになる可能性がある。

5. **Buffered + directDbWrite の組み合わせ**: `m_publisher.setBuffered(true)` が設定されているが、`m_directDbWrite = true` の場合は `applStateTable.set()` 直接実行のため buffering は通知チャネルにのみ影響する。
