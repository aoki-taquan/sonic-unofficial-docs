# FG_NHG — Phase F 副次 DB 書込スキャン結果

対象ページ: `docs/reference/config-db/fg-nhg.md`
スキャン日: 2026-05-16
調査ソース: `sonic-swss/orchagent/fgnhgorch.cpp`

---

## 概要

`FgNhgOrch` は CONFIG_DB の `FG_NHG` / `FG_NHG_PREFIX` / `FG_NHG_MEMBER` を受けて、
ASIC_DB（SAI 経由）・STATE_DB・APPL_DB の 3 か所に書き込む。

---

## ASIC_DB 書込み（SAI 経由）

orchagent は直接 ASIC_DB には書き込まず、SAI API 呼び出しを通じて syncd が ASIC_DB へ反映する。

### create_next_hop_group (RouteOrch 経由)

- 呼び出し箇所: `createFineGrainedNextHopGroup()` L275
- SAI API: `gRouteOrch->createFineGrainedNextHopGroup(next_hop_group_id, nhg_attrs)`
- 属性:
  - `SAI_NEXT_HOP_GROUP_ATTR_TYPE = SAI_NEXT_HOP_GROUP_TYPE_FINE_GRAIN_ECMP`
  - `SAI_NEXT_HOP_GROUP_ATTR_CONFIGURED_SIZE = fgNhgEntry->configured_bucket_size`
- タイミング: `FG_NHG` SET → バケット配置計算 → NHG 生成

### create_next_hop_group_member (setNewNhgMembers)

- 呼び出し箇所: `setNewNhgMembers()` L1169–1194
- SAI API: `sai_next_hop_group_api->create_next_hop_group_member()`
- 属性:
  - `SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_GROUP_ID`
  - `SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_ID`
  - `SAI_NEXT_HOP_GROUP_MEMBER_ATTR_INDEX` (バケット位置)
- タイミング: FG NHG メンバ追加時（バンク単位でバケット再配分）
- CRM: `gCrmOrch->incCrmResUsedCounter(CRM_NEXTHOP_GROUP_MEMBER)` L1194

### set_next_hop_group_member_attribute (writeHashBucketChange)

- 呼び出し箇所: `writeHashBucketChange()` L238
- SAI API: `sai_next_hop_group_api->set_next_hop_group_member_attribute()`
- 属性: `SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_ID`（バケット先 OID 変更）
- タイミング: メンバ UP/DOWN 時のバンク内バケット再割り当て

### remove_next_hop_group_member (removeFineGrainedNextHopGroup)

- 呼び出し箇所: `removeFineGrainedNextHopGroup()` L327
- SAI API: `sai_next_hop_group_api->remove_next_hop_group_member()`
- CRM: `gCrmOrch->decCrmResUsedCounter(CRM_NEXTHOP_GROUP_MEMBER)` L338
- タイミング: NHG 削除時、エラーロールバック時

### set_route_entry_attribute (modifyRoutesNextHopId)

- 呼び出し箇所: `modifyRoutesNextHopId()` L363–375
- SAI API: `sai_route_api->set_route_entry_attribute()`
- 属性: `SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID`
- タイミング: FG ルートの next-hop group OID 切替時

---

## STATE_DB 書込み

テーブル名: `FG_ROUTE_TABLE`（`STATE_FG_ROUTE_TABLE_NAME` 定数）
接続: `m_stateWarmRestartRouteTable(stateDb, STATE_FG_ROUTE_TABLE_NAME)` L31

### setStateDbRouteEntry() — バケット割り当て記録

- 呼び出し箇所: `setStateDbRouteEntry()` L218–226
- 操作: `m_stateWarmRestartRouteTable.hset(key, field, value)`
- キー: `<ip_prefix>` (文字列)
- フィールド: `<bucket_index>` (uint32_t → 文字列変換)
- 値: `<nexthop_key>` (next-hop IP 文字列)
- 呼び出し元:
  - `writeHashBucketChange()` L253 — バケット再割り当て時
  - `setNewNhgMembers()` L1193 — 初期バケット配置時

### del() — ルート削除時のクリーンアップ

- 呼び出し箇所: L897, L1605, L140
- 操作: `m_stateWarmRestartRouteTable.del(key)`
- タイミング:
  - FG ルート削除完了時 (L897, L1605)
  - warm-restart 復旧完了後の一括クリーンアップ (L140)

### 目的

warm-restart 時にこのテーブルから各プレフィクスのバケット → next-hop マッピングを復元する。
通常運用時は書き込み専用（warm-restart 起動時に読み出し）。

---

## APPL_DB 書込み

テーブル名: `ROUTE_TABLE`（`APP_ROUTE_TABLE_NAME` 定数）
接続: `m_routeTable = createProducerStateTable(appDb, APP_ROUTE_TABLE_NAME, m_zmqClient)` L32

### FG_NHG_PREFIX SET — 通常ルート → FG ルート移行

1. 既存通常 ECMP ルートを削除: `m_routeTable->del(ip_prefix.to_string())` L1865
2. RouteOrch の削除完了を確認（`return false` ループ）L1869–1883
3. FG ルートとして再投入: `m_routeTable->set(ip_prefix.to_string(), ...)` L1877

### FG_NHG_PREFIX DEL — FG ルート → 通常ルート移行

1. FG ルートを削除: `m_routeTable->del(ip_prefix.to_string())` L1931
2. 通常 ECMP ルートとして再投入: `m_routeTable->set(ip_prefix.to_string(), ...)` L1951

### 注意点

APPL_DB:ROUTE_TABLE への書込権限がない状態では `doTaskFgNhgPrefix()` が永久に `return false`
でリトライし続ける。この書込は orchagent の正常動作の前提となる。

---

## スキャン証跡

| 操作 | ソース箇所 | DB | テーブル |
|---|---|---|---|
| SAI NHG 生成 | createFineGrainedNextHopGroup() L275 | ASIC_DB | ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP |
| SAI NHG メンバ生成 | setNewNhgMembers() L1169 | ASIC_DB | ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MEMBER |
| SAI NHG メンバ属性変更 | writeHashBucketChange() L238 | ASIC_DB | ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MEMBER |
| SAI NHG メンバ削除 | removeFineGrainedNextHopGroup() L327 | ASIC_DB | ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MEMBER |
| SAI ルート next-hop 更新 | modifyRoutesNextHopId() L363 | ASIC_DB | ASIC_STATE:SAI_OBJECT_TYPE_ROUTE_ENTRY |
| STATE_DB hset | setStateDbRouteEntry() L224 | STATE_DB | FG_ROUTE_TABLE |
| STATE_DB del | L897, L1605, L140 | STATE_DB | FG_ROUTE_TABLE |
| APPL_DB del | doTaskFgNhgPrefix() L1865, L1931 | APPL_DB | ROUTE_TABLE |
| APPL_DB set | doTaskFgNhgPrefix() L1877, L1951 | APPL_DB | ROUTE_TABLE |
| CRM inc | setNewNhgMembers() L1194 | COUNTERS_DB | CRM_NEXTHOP_GROUP_MEMBER |
| CRM dec | removeFineGrainedNextHopGroup() L338 | COUNTERS_DB | CRM_NEXTHOP_GROUP_MEMBER |
