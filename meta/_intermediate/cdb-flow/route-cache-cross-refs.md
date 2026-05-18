# route-cache-cross-refs.md — Phase C: APPL_STATE_DB ROUTE_TABLE 暗黙参照テーブルスキャン

調査日: 2026-05-18
対象テーブル: APPL_STATE_DB `ROUTE_TABLE`（route offload cache）
Writer: `orchagent RouteOrch::publishRouteState()` → `ResponsePublisher::publish()`
Consumer: `fpmsyncd RouteSync::onRouteResponse()`、`route_check.py`
スキャン範囲: routeorch.cpp L57-58, L127, L192, L294, L706-716, L2729, L2970, L3185-3202; response_publisher.cpp L96-220; fpmsyncd.cpp L78-302; routesync.cpp L3160-3310; sonic-utilities/scripts/route_check.py L755-778

---

## 検出した暗黙参照

### 1. APPL_DB ROUTE_TABLE（書き込みトリガ兼キー源泉）

- **参照先**: APPL_DB `ROUTE_TABLE`
- **方向**: 読み取り（`ConsumerStateTable` 購読） → APPL_STATE_DB `ROUTE_TABLE` への書き込みトリガ
- **参照元**: `routeorch.cpp:192`（`createRetryCache(APP_ROUTE_TABLE_NAME)`）、`routeorch.cpp:622`（dispatch: `APP_ROUTE_TABLE_NAME`）
- **意味**: APPL_DB `ROUTE_TABLE` に経路が SET されると `RouteOrch::doTask()` が起動し、SAI プログラミング成功後に APPL_STATE_DB `ROUTE_TABLE` の同一キーに `protocol` フィールドを書き込む。DEL 時は APPL_STATE_DB の同一キーエントリを削除する。APPL_STATE_DB のキー構造は APPL_DB と同一（`ROUTE_TABLE:<prefix>` または `ROUTE_TABLE:<vrf>:<prefix>`）。

evidence: `routeorch.cpp:622`, `routeorch.cpp:3201`

---

### 2. CONFIG_DB VRF（VRF 経路の先行依存）

- **参照先**: CONFIG_DB `VRF` テーブル（`VRFOrch` 管理）
- **方向**: 読み取り（`m_vrfOrch->isVRFexists(vrf_name)`、`m_vrfOrch->getVRFid(vrf_name)`）
- **参照元**: `routeorch.cpp:706-716`（`Vrf<name>:` プレフィックスキーの解決）
- **意味**: key が `Vrf<name>:<prefix>` 形式の VRF 経路を処理する際、`isVRFexists()` で VRF SAI オブジェクトが存在するかを確認する。未登録の場合は `it++; continue` で後回しになり、APPL_STATE_DB への書き込みは行われない。VRF が存在しない間は当該経路は APPL_STATE_DB に一切出現しない。
- **ブロッキング**: VRF SAI 未登録の間は対象 VRF 経路の APPL_STATE_DB エントリが書かれない。VRF を先に CONFIG_DB で作成・処理完了させること。

evidence: `routeorch.cpp:706-716`

---

### 3. CONFIG_DB DEVICE_METADATA|localhost.suppress-fib-pending（suppression 機能スイッチ）

- **参照先**: CONFIG_DB `DEVICE_METADATA|localhost` の `suppress-fib-pending` フィールド
- **方向**: 読み取り（`fpmsyncd.cpp:113`）、動的変更監視（`fpmsyncd.cpp:278-297`）
- **参照元**: `fpmsyncd.cpp:83`（`deviceMetadataTable`）、`fpmsyncd.cpp:113`（起動時読み取り）、`fpmsyncd.cpp:278`（`SubscriberStateTable` 購読で動的変更追従）
- **意味**: fpmsyncd が APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL を購読して FRR zebra へ offload 通知を送るかどうかを制御する。`suppress-fib-pending = "enabled"` の場合のみ `NotificationConsumer` を生成し `sync.setSuppressionEnabled(true)` を呼ぶ。APPL_STATE_DB への書き込み自体は suppression 設定に関わらず RouteOrch が行うが、fpmsyncd 側の offload 通知フローはこのフィールドに依存する。
- **動的変更**: runtime に `suppress-fib-pending` が変更された場合も `SubscriberStateTable` 経由で検知し、有効→無効の切り替え時に `markRoutesOffloaded()` を一括実行して FRR が持つ全経路の offload フラグを復元する（fpmsyncd.cpp:293-297）。

evidence: `fpmsyncd.cpp:82-83, 112-118, 278-297`

---

### 4. ResponsePublisher 内部（APPL_STATE_DB への書き込み経路）

- **参照先**: `APPL_STATE_DB ROUTE_TABLE`（ResponsePublisher 書き先）
- **方向**: 書き込み（`ResponsePublisher::writeToDB()`）
- **参照元**: `response_publisher.cpp:152-168`（`writeToDB()`）、`routeorch.cpp:57-58`（`m_publisher.m_directDbWrite = true`）
- **意味**: `RouteOrch` の `m_publisher` は `m_directDbWrite = true` で初期化される。`ResponsePublisher::publish()` は SAI 成功かつ SET 操作の場合のみ `applStateTable.set(key, attrs)` を呼んで APPL_STATE_DB へ書き込む。SAI 失敗時は RESPONSE_CHANNEL 通知は行うが APPL_STATE_DB の書き込みはスキップする。
- **条件ガード**: `response_publisher.cpp:129-133` の `m_enable_db_write_and_notify && (intent_attrs.size() && state_attrs.size()) || (status.ok() && !intent_attrs.size())` で制御。

evidence: `response_publisher.cpp:129-148, 152-168`

---

### 5. fpmsyncd / RouteSync（RESPONSE_CHANNEL 購読 consumer）

- **参照先**: `APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL`（通知チャネル）、`APPL_STATE_DB ROUTE_TABLE`（Warm Restart 時読み出し）
- **方向**: 読み取り（購読）
- **参照元**: `fpmsyncd.cpp:78`（チャネル名定義）、`routesync.cpp:3165-3265`（`onRouteResponse()`）、`routesync.cpp:3290-3310`（`markRoutesOffloaded()`）
- **意味**: fpmsyncd は RESPONSE_CHANNEL 経由で SAI プログラミング結果を受け取り、成功した経路について FRR zebra に RTM_NEWROUTE（offload フラグ付き）を送信する。Warm Restart 完了時 (`onWarmStartEnd()`) は APPL_STATE_DB ROUTE_TABLE の全エントリを走査して一括 offload 通知を送る。
- **方向**: APPL_STATE_DB は RouteOrch（書き手）と fpmsyncd（Warm Restart 読み手）の両方に参照される。

evidence: `fpmsyncd.cpp:78`, `routesync.cpp:3165-3310`

---

### 6. route_check.py（APPL_STATE_DB ROUTE_TABLE 読み出し + RESPONSE_CHANNEL 注入）

- **参照先**: `APPL_STATE_DB`、`APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL`
- **方向**: 読み取り（整合確認）、書き込み（RESPONSE_CHANNEL 注入）
- **参照元**: `scripts/route_check.py:767-771`（`mitigate_installed_not_offloaded_frr_routes()`）
- **意味**: `route_check.py` は APPL_DB ROUTE_TABLE と ASIC_DB・FRR の経路整合を確認する。FRR に存在するが offload フラグが立っていない経路を検出した場合、`mitigate_installed_not_offloaded_frr_routes()` が `NotificationProducer` で APPL_STATE_DB から `APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL` に `SWSS_RC_SUCCESS` を注入して fpmsyncd に offload 通知を再送させる。APPL_STATE_DB を直接書き換えるのではなく RESPONSE_CHANNEL を経由してフローを再起動する。

evidence: `scripts/route_check.py:767-771`

---

## 参照関係サマリ

| 参照先テーブル / リソース | 参照方向 | 条件 | 参照元 evidence |
|--------------------------|---------|------|----------------|
| `APPL_DB ROUTE_TABLE` | 読み取り（書き込みトリガ） | 常時 | `routeorch.cpp:192, 622` |
| `CONFIG_DB VRF` | 読み取り（VRF SAI OID 解決） | VRF 経路（key が `Vrf<name>:` プレフィックス）のみ | `routeorch.cpp:706-716` |
| `CONFIG_DB DEVICE_METADATA\|localhost.suppress-fib-pending` | 読み取り（suppression 機能スイッチ） | fpmsyncd 起動時 + 動的変更監視 | `fpmsyncd.cpp:82-118, 278-297` |
| `ResponsePublisher`（APPL_STATE_DB 書き手） | 書き込み | SAI 成功かつ SET 操作のみ | `response_publisher.cpp:129-148` |
| `fpmsyncd RouteSync`（RESPONSE_CHANNEL 購読） | 読み取り（offload 通知先） | suppression 有効時 + Warm Restart | `routesync.cpp:3165-3310` |
| `route_check.py`（APPL_STATE_DB 読み + RESPONSE_CHANNEL 注入） | 読み取り + 書き込み（recovery） | 整合チェック実行時 | `route_check.py:767-771` |
