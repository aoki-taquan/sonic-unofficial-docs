# DASH_ROUTING_* テーブル — 失敗挙動調査 (Phase D)

調査対象: `dashrouteorch.cpp` / `dashorch.cpp`  
コミット: 4305596156d70e9797e8a881b3d19b46de0bce0d

---

## retry / failure パターン概要

`DashRouteOrch` / `DashOrch` はタスク処理に ZMQ ConsumerStateFull を使用し、
各ハンドラが `bool` (true=消費, false=リトライ) を返す。

### DASH_ROUTING_TYPE_TABLE (DashOrch::doTaskRoutingTypeTable)

| 失敗ケース | ログ | 戻り値 | retry |
|-----------|------|--------|-------|
| `routing_type` 文字列を ROUTING_TYPE_ enum に変換失敗 | SWSS_LOG_ERROR | true (消費・廃棄) | なし |
| 重複登録 (既存エントリあり) | SWSS_LOG_WARN | true (消費・廃棄, 既存維持) | なし |
| SAI `create_dash_routing_type` 失敗 | SWSS_LOG_ERROR | false | 自動リトライ |
| DEL: 存在しない routing_type | SWSS_LOG_WARN | true (消費) | なし |

### DASH_ROUTE_GROUP_TABLE (DashRouteOrch::addRouteGroup / removeRouteGroup)

| 失敗ケース | ログ | 戻り値 | retry |
|-----------|------|--------|-------|
| SAI `create_outbound_routing_group` 失敗 | SWSS_LOG_ERROR | false | 自動リトライ |
| DEL: グループが ENI にバインド中 (`isRouteGroupBound()=true`) | SWSS_LOG_WARN | false | ENI アンバインド後に再試行 |
| DEL: グループ未登録 | SWSS_LOG_WARN | true (消費) | なし |

### DASH_ROUTE_TABLE (DashRouteOrch::addOutboundRouting / removeOutboundRouting)

| 失敗ケース | ログ | 戻り値 | retry |
|-----------|------|--------|-------|
| `routing_type` が UNSPECIFIED かつ deprecated `action_type` も UNSPECIFIED | SWSS_LOG_WARN | false | 自動リトライ (永続滞留の可能性) |
| `route_group` 未登録 (`getRouteGroupOid()` = NULL_OID) | (なし / false return) | false | グループ登録まで自動リトライ |
| ルートグループが ENI にバインド済み (addOutboundRouting) | SWSS_LOG_WARN | **true** (消費・SAI 非書込) | なし (サイレント廃棄) |
| ルートグループが ENI にバインド済み (removeOutboundRouting) | SWSS_LOG_WARN | false | アンバインドまで保留 |
| `routing_type=vnet` で `vnet` 未登録 | SWSS_LOG_WARN | false | VNET 登録まで自動リトライ |
| `routing_type=vnet_direct` で `overlay_ip` 未設定 | SWSS_LOG_WARN | false | 自動リトライ |
| `tunnel` 指定で DashTunnelOrch に未登録 | SWSS_LOG_INFO | false | トンネル登録まで自動リトライ |
| bulk SAI `create_outbound_routing_entries` 部分失敗 | SWSS_LOG_ERROR (per-entry) | 失敗分 false | 失敗エントリのみリトライ |

**重要**: バインド中の addOutboundRouting は `return true` (消費) のためエントリが**サイレントに廃棄**される。
コントローラは ENI アンバインド後に再投入する必要がある。

### DASH_ROUTE_RULE_TABLE (DashRouteOrch::addInboundRouting / removeInboundRouting)

| 失敗ケース | ログ | 戻り値 | retry |
|-----------|------|--------|-------|
| ENI 未登録 (`dash_orch_->getEni()` = null) | SWSS_LOG_INFO | false | ENI 登録まで自動リトライ |
| `vnet` 指定で `gVnetNameToId` 未登録 | SWSS_LOG_WARN | false | VNET 登録まで自動リトライ |
| bulk SAI `create_inbound_routing_entries` 部分失敗 | SWSS_LOG_ERROR (per-entry) | 失敗分 false | 失敗エントリのみリトライ |
| DEL: ルール未登録 | SWSS_LOG_WARN | true (消費) | なし |

## 永続滞留リスク

`routing_type=UNSPECIFIED` かつ deprecated `action_type` も `UNSPECIFIED` のエントリは
`return false` が返り続ける。依存テーブルが揃っても解消しないため、コントローラ側で
正しい `routing_type` を設定した再投入が必要。

## STATE_DB / ERROR_DB への記録

DASH 系 Orch は失敗時に STATE_DB / ERROR_TABLE への書き込みを行わない。
失敗の確認には `swsslog` / `orchagent.log` を参照すること。
