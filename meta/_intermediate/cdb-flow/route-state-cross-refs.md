# route-state cross-refs (Phase C) — 調査メモ

## 対象テーブル
- STATE_DB `ROUTE_TABLE` (デフォルト経路 state=ok/na)
- APPL_STATE_DB `ROUTE_TABLE` (protocol + err_str)

## 書込み主体
- `orchagent` (`RouteOrch`) — routeorch.cpp

## 読み取り主体（cross-ref）

### STATE_DB `ROUTE_TABLE`

#### sonic-linkmgrd (MuxManager / DbInterface)
- ファイル: `sonic-linkmgrd/src/DbInterface.cpp:1835`
- `SubscriberStateTable stateDbRouteTable(stateDbPtr.get(), STATE_ROUTE_TABLE_NAME)`
- `processDefaultRouteStateNotification()` で `0.0.0.0/0` / `::/0` の `state` フィールドを読む
- `MuxManager::addOrUpdateDefaultRouteState()` へ渡し、デュアルTOR (MUX) のリンクプローバー制御に使用
- `state=ok` → リンクプローバー再起動、`state=na` → リンクプローバー停止

### APPL_STATE_DB `ROUTE_TABLE`

#### fpmsyncd (RouteSync::onRouteResponse)
- ファイル: `sonic-swss/fpmsyncd/fpmsyncd.cpp:78-116`
- チャンネル名: `APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL`
- `NotificationConsumer` で購読 → `RouteSync::onRouteResponse()` 呼び出し
- `err_str=SWSS_RC_SUCCESS` かつ `protocol` フィールドあり → FRR zebra へ offload フラグ (RTM_F_OFFLOAD) を netlink 経由で通知
- BGP suppress / BGP error-handling feature が有効時のみ実際の動作が発生 (`isSuppressionEnabled()`)
- ファイル: `sonic-swss/fpmsyncd/routesync.cpp:3165-3220`

#### route_check.py (自動修復スクリプト)
- ファイル: `sonic-utilities/scripts/route_check.py:767-773`
- `APPL_STATE_DB` の `APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL` に `NotificationProducer` で送信
- APPL_STATE_DB 未反映経路を検出した際、手動で `SWSS_RC_SUCCESS` 応答を送ることで offload フラグ送信を強制する自動修復ロジック

## 依存グラフ (Phase C 要約)
```
STATE_DB[ROUTE_TABLE|0.0.0.0/0 state=ok/na]
  → sonic-linkmgrd DbInterface (SubscriberStateTable) → MuxManager::addOrUpdateDefaultRouteState()
    → LinkManagerStateMachine::handleDefaultRouteState() → リンクプローバー 停止/再起動

APPL_STATE_DB[ROUTE_TABLE:<prefix> protocol + err_str]
  → fpmsyncd (NotificationConsumer APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL)
    → RouteSync::onRouteResponse() → FRR zebra へ RTM_F_OFFLOAD 通知 (BGP suppress 有効時)
  → route_check.py (NotificationProducer 送信側) — 自動修復時に応答を注入
```
