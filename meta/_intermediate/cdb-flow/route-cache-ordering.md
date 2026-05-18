# route-cache-ordering.md — Phase B: APPL_STATE_DB ROUTE_TABLE 書込み順依存スキャン

調査日: 2026-05-18
対象テーブル: APPL_STATE_DB `ROUTE_TABLE`（route offload cache）
Writer: `orchagent RouteOrch::publishRouteState()` → `ResponsePublisher::publish()`
Consumer: `fpmsyncd RouteSync::onRouteResponse()`
スキャン範囲: routeorch.cpp L57-58, L923, L1049-1090, L1231, L2729, L2970, L3185-3202; response_publisher.cpp L96-220; fpmsyncd.cpp L78-302; routesync.cpp L3160-3310

---

## 検出した順序依存・タイミング依存

### 1. APPL_DB ROUTE_TABLE SAI プログラミング成功 → APPL_STATE_DB 書き込み

APPL_STATE_DB ROUTE_TABLE へのエントリ書き込みは、`RouteOrch::publishRouteState()` が呼ばれた**後**であり、`publishRouteState()` は SAI `create_route_entry` または `set_route_entry_attribute` の成功（またはスキップ条件）確認後にのみ呼ばれる。

- `addRoutePost()` 末尾 (routeorch.cpp:L2729): SAI 操作後に無条件呼出し（成否は `status` 引数で伝搬）
- `removeRoutePost()` 末尾 (routeorch.cpp:L2970): 同上
- SAI 成功の場合のみ `ResponsePublisher` が APPL_STATE_DB にエントリを書き込む (response_publisher.cpp:L129-148)

**順序**: APPL_DB ROUTE_TABLE 書き込み → RouteOrch が SAI に反映 → SAI 成功 → APPL_STATE_DB ROUTE_TABLE 書き込み

APPL_DB ROUTE_TABLE に経路が存在しても SAI 失敗（例: リソース枯渇・SAI エラー）の場合、APPL_STATE_DB にエントリは**存在しない**。APPL_STATE_DB と APPL_DB の差分が SAI 失敗経路を意味する。

evidence: `routeorch.cpp:2729`, `routeorch.cpp:2970`, `response_publisher.cpp:129-148`

---

### 2. VRF 経路: VRF SAI 登録が先行必須

key が `Vrf<name>:<prefix>` 形式の VRF 経路は、`m_vrfOrch->isVRFexists(vrf_name)` が偽の間は `it++; continue` で後回しになる (routeorch.cpp:L711-714)。VRF SAI オブジェクト未登録の間は SAI プログラミング自体が行われないため、APPL_STATE_DB への書き込みも発生しない。

```cpp
// routeorch.cpp L711-714
if (!m_vrfOrch->isVRFexists(vrf_name))
{
    it++;
    continue;
}
```

**順序**: VRF SAI 登録（VRFOrch が CONFIG_DB|VRF を処理完了） → APPL_DB ROUTE_TABLE の VRF 経路 → SAI 成功 → APPL_STATE_DB ROUTE_TABLE

evidence: `routeorch.cpp:711-714`

---

### 3. flush() バッチ境界: 1 doTask() サイクル内での書込み順

`RouteOrch` は `ResponsePublisher` をバッファリングモード (`setBuffered(true)`) で使用し、`doTask()` の末尾で必ず `flush()` を呼ぶ (routeorch.cpp:L57, L1231)。

```cpp
// routeorch.cpp:57
m_publisher.setBuffered(true);
// routeorch.cpp:1231
m_publisher.flush();
```

これにより、同一 `doTask()` サイクル内で処理された複数経路の APPL_STATE_DB 書き込みは **flush 時点でまとめて Redis パイプラインに送出**される。個別経路の書き込み完了順序は flush 前の処理順序（`m_toSync` の内部順序）に従うが、consumer から見ると同一バッチの書き込みは「まとめて到着」するように見える。

**影響**: ひとつのバッチ内で複数経路の SET / DEL が混在した場合、SET 操作は前処理フェーズ（L1000-1200付近）で確定し、DEL 操作も同フェーズで処理される。すべての APPL_STATE_DB 変更は `flush()` 後にまとめて到達する。

evidence: `routeorch.cpp:57`, `routeorch.cpp:1231`

---

### 4. suppression 有効時のみ fpmsyncd が RESPONSE_CHANNEL を購読

APPL_STATE_DB への書き込み自体は suppression 設定に関係なく発生するが、`fpmsyncd` が `APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL` を通じて結果を受け取り FRR へ offload 通知を送るのは `suppress-fib-pending = enabled` の場合のみ。

```cpp
// fpmsyncd.cpp:L113-118
if (suppressionEnabledStr == "enabled")
{
    routeResponseChannel = std::make_unique<NotificationConsumer>(&applStateDb, routeResponseChannelName);
    sync.setSuppressionEnabled(true);
}
```

`isSuppressionEnabled()` が false の場合、`onRouteResponse()` は冒頭で即リターンする (routesync.cpp:L3174)。

**順序（suppression 有効時）**: APPL_STATE_DB ROUTE_TABLE 書き込み + RESPONSE_CHANNEL 通知 → fpmsyncd の `onRouteResponse()` → FRR zebra への RTM_NEWROUTE offload 送信

suppression 無効時: APPL_STATE_DB は書き込まれるが、fpmsyncd は通知を無視。FRR への offload フラグ反映は行われない。

evidence: `fpmsyncd.cpp:113-118`, `routesync.cpp:3174`

---

### 5. Warm Restart: APPL_STATE_DB 読み出し → offload 通知の後払い

Warm restart 完了時 (`onWarmStartEnd()`）、`markRoutesOffloaded()` が APPL_STATE_DB の全 ROUTE_TABLE エントリを走査して FRR zebra に RTM_NEWROUTE を一括送信する (routesync.cpp:L3298-3310)。

```cpp
// routesync.cpp:L3298-3310
void RouteSync::onWarmStartEnd(DBConnector& applStateDb)
{
    if (isSuppressionEnabled())
        markRoutesOffloaded(applStateDb);
    if (m_warmStartHelper.inProgress())
        m_warmStartHelper.reconcile();
}
```

**順序（Warm Restart）**: orchagent 再起動 → SAI 経路が ASIC に既存 → APPL_STATE_DB エントリが保持済み → fpmsyncd `onWarmStartEnd()` → APPL_STATE_DB 全エントリ読み出し → FRR offload 通知一括送信

この経路では通常フローとは逆に、APPL_STATE_DB が「既存状態」として先に存在し、その後 offload 通知が送られる。

evidence: `routesync.cpp:3298-3310`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | APPL_DB ROUTE_TABLE → SAI 成功 → APPL_STATE_DB 書き込み | 強制先行（SAI 失敗時はエントリ不在） | SAI 失敗経路は APPL_STATE_DB に存在しない点に注意 |
| 2 | VRF SAI 登録 → VRF 経路の APPL_STATE_DB 書き込み | 強制先行（isVRFexists false → 後回し） | VRF を先に作成 |
| 3 | doTask() flush() → APPL_STATE_DB 書き込みのまとめ到着 | バッチ境界（同サイクル内変更はまとめて送出） | consumer は同一バッチ変更の個別到着順を仮定しないこと |
| 4 | suppress-fib-pending 有効 → fpmsyncd が RESPONSE_CHANNEL 購読 | 機能有効時のみ | 無効時は APPL_STATE_DB 書き込みは発生するが offload 通知は行われない |
| 5 | Warm Restart: APPL_STATE_DB 既存 → onWarmStartEnd → offload 通知 | 後払い（通常フローとは逆順） | warm restart 完了後に offload フラグ復元が自動実行される |
