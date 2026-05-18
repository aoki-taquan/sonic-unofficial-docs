# ROUTE_TABLE (STATE_DB / APPL_STATE_DB) — Phase B 書込み順依存スキャンノート

対象テーブル: `STATE_DB ROUTE_TABLE` / `APPL_STATE_DB ROUTE_TABLE`
Consumer: `orchagent RouteOrch` (`sonic-swss/orchagent/routeorch.cpp`)
スキャン範囲: L609-611 (allPortsReady), L126-130 (コンストラクタ), L2700-2703 (addRoute 末尾), L2856 (removeRoute 末尾), L3185-3202 (publishRouteState), L920-923 (bulk publish)

---

## 検出した順序依存

### 1. allPortsReady() — RouteOrch 全処理の前提条件

`routeorch.cpp:609-611` — `RouteOrch::doTask()` の先頭で `gPortsOrch->allPortsReady()` を確認し、
false の場合は即 `return` して全処理を停止する。ポート初期化完了前は APPL_DB からの
ROUTE_TABLE イベントを処理しないため、STATE_DB / APPL_STATE_DB への書き込みも発生しない。

```cpp
// routeorch.cpp:609-611
if (!gPortsOrch->allPortsReady())
{
    return;
}
```

**影響**: 起動直後は APPL_DB に ROUTE_TABLE エントリが存在しても STATE_DB への `state` 書き込みや
APPL_STATE_DB への `protocol`/`err_str` 書き込みは allPortsReady になるまで遅延する。

evidence: `routeorch.cpp:609-611`

---

### 2. SAI route 操作成功 → STATE_DB 書き込み (updateDefRouteState)

STATE_DB `ROUTE_TABLE` への `state=ok` / `state=na` の書き込みは、SAI route entry の
作成/削除が成功した後に `updateDefRouteState()` が呼ばれることによって行われる。

**ADD パス** (`routeorch.cpp:2700-2703`):
```cpp
if (ipPrefix.isDefaultRoute())
{
    updateDefRouteState(ipPrefix.to_string(), true);
}
```
SAI `sai_route_api->create_route_entry()` が成功した後（バルク送信完了後）に呼ばれる。
SAI が失敗した場合は `updateDefRouteState` は呼ばれず STATE_DB は更新されない。

**DEL パス** (`routeorch.cpp:2856`):
```cpp
updateDefRouteState(ipPrefix.to_string());  // add=false → state="na"
```
SAI set packet_action to DROP が成功した後に呼ばれる。

**順序**: SAI route 操作成功 → `updateDefRouteState()` → STATE_DB 書き込み。
SAI 失敗時は STATE_DB への書き込みは行われない（デフォルト経路の場合）。

evidence: `routeorch.cpp:2700-2703`, `routeorch.cpp:2856`

---

### 3. SAI route 操作（成否問わず）→ APPL_STATE_DB 書き込み (publishRouteState)

APPL_STATE_DB `ROUTE_TABLE` への書き込みは `publishRouteState()` が担い、SAI 操作の
成否に関わらず呼ばれる（バルク操作のレスポンスチャンネルへの通知）。

```cpp
// routeorch.cpp:3185-3202
void RouteOrch::publishRouteState(const RouteBulkContext& ctx, const ReturnCode& status)
{
    std::vector<FieldValueTuple> fvs;
    if (ctx.is_set)
    {
        fvs.emplace_back("protocol", ctx.protocol);
    }
    m_publisher.publish(APP_ROUTE_TABLE_NAME, ctx.key, fvs, status, replace);
}
```

- SET 成功: `protocol` + `err_str=SWSS_RC_SUCCESS` を APPL_STATE_DB に書き込む
- SET 失敗: `err_str=[SAI] <エラー>` を書き込む（APPL_STATE_DB にエントリ自体は残る）
- DEL: `fvs` が空 → ResponsePublisher がエントリを APPL_STATE_DB から削除

**順序**: SAI バルク操作完了 → `publishRouteState()` → APPL_STATE_DB 書き込み。
APPL_STATE_DB への書き込みは SAI 操作失敗時も発生する（STATE_DB とは異なる点）。

evidence: `routeorch.cpp:3185-3202`, `routeorch.cpp:2729`, `routeorch.cpp:2970`, `routeorch.cpp:920-923`

---

### 4. コンストラクタ初期化 — STATE_DB への `state=na` 書き込み

`routeorch.cpp:126-130, 155-156` — `RouteOrch` コンストラクタで両デフォルト経路に
`state=na` を書き込む（SAI への drop route 作成と同時）。

```cpp
// routeorch.cpp:126-130
m_stateDb = shared_ptr<DBConnector>(new DBConnector("STATE_DB", 0));
m_stateDefaultRouteTb = unique_ptr<swss::Table>(new Table(m_stateDb.get(), STATE_ROUTE_TABLE_NAME));

IpPrefix default_ip_prefix("0.0.0.0/0");
updateDefRouteState("0.0.0.0/0");  // state=na (add=false)
```

このコンストラクタ初期化は `allPortsReady()` チェックより前に実行されるため、
orchagent 起動直後から `STATE_DB ROUTE_TABLE|0.0.0.0/0 state=na` が存在する。

evidence: `routeorch.cpp:126-130`, `routeorch.cpp:155-156`

---

## 順序依存サマリ

| # | 依存関係 | 種別 | 違反時の挙動 |
|---|----------|------|------------|
| 1 | `allPortsReady()=true` → STATE_DB / APPL_STATE_DB への ROUTE 処理結果書き込み | 強制先行（false なら doTask が即 return） | ポート初期化完了まで STATE/APPL_STATE への動的書き込みなし |
| 2 | SAI `create_route_entry()` 成功 → `updateDefRouteState()` 呼び出し | 成功時のみ（SAI 失敗時は STATE_DB 未更新） | STATE_DB の state が古い値のままになる（デフォルト経路） |
| 3 | SAI バルク操作完了 → `publishRouteState()` 呼び出し | 成否問わず（失敗 err_str も書き込む） | APPL_STATE_DB の err_str が更新されない |
| 4 | RouteOrch コンストラクタ → STATE_DB `state=na` 書き込み | 起動時 1 回（allPortsReady 不要） | orchagent 起動直後から state=na が存在する |
