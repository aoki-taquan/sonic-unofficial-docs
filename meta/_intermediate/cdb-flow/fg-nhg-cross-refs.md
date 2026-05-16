# fg-nhg cross-refs 調査ログ (Phase C)

**調査日**: 2026-05-16
**調査者**: Claude (batch agent)
**調査対象**: `sonic-swss/orchagent/fgnhgorch.cpp` (2164行)

## 調査方針

`FG_NHG` / `FG_NHG_PREFIX` / `FG_NHG_MEMBER` テーブルを購読する `FgNhgOrch` が、
YANG leafref に現れない他テーブルを暗黙的に参照する箇所を全行調査。

## 発見した暗黙参照

### 1. APPL_DB:ROUTE_TABLE — 読み書き

```cpp
// fgnhgorch.cpp:32
m_routeTable(createProducerStateTable(appDb, APP_ROUTE_TABLE_NAME, m_zmqClient))

// fgnhgorch.cpp:1865 — FG_NHG_PREFIX SET 時に通常 ECMP 経路を削除
m_routeTable->del(ip_prefix.to_string());

// fgnhgorch.cpp:1877 — RouteOrch が削除完了後に FG 経路として再投入
m_routeTable->set(ip_prefix.to_string(), generateRouteTableFromNhgKey(addCache->second));

// fgnhgorch.cpp:1931, 1951 — FG_NHG_PREFIX DEL 時も同様のシーケンス
m_routeTable->del(ip_prefix.to_string());
m_routeTable->set(ip_prefix.to_string(), generateRouteTableFromNhgKey(delCache->second));
```

FG_NHG_PREFIX の SET/DEL に際し、既存の通常 ECMP 経路との「入れ替え」が必要なため
APPL_DB ROUTE_TABLE を直接操作する。FG 対象ルートは RouteOrch 経由でも
`gRouteOrch->getSyncdRouteNhgKey()` / `isRouteFineGrained()` が参照される (routeorch.cpp:2028)。

**影響**: APPL_DB への ProducerStateTable 書き込み権限が無い環境では FG 経路切替が
永久リトライになる。

### 2. NeighOrch (APPL_DB:NEIGH_TABLE) — 読み取り

```cpp
// fgnhgorch.cpp:28
m_neighOrch(neighOrch),

// fgnhgorch.cpp:1415
if (!m_neighOrch->hasNextHop(nhk))
{
    SWSS_LOG_NOTICE("Failed to get next hop %s:%s in neighorch", ...);
    continue;
}

// fgnhgorch.cpp:1459
sai_object_id_t nhid = m_neighOrch->getNextHopId(nhk);

// fgnhgorch.cpp:1479
m_neighOrch->increaseNextHopRefCount(nexthop);

// fgnhgorch.cpp:1547, 1554, 1601
m_neighOrch->increaseNextHopRefCount(nh);
m_neighOrch->decreaseNextHopRefCount(nh);
m_neighOrch->decreaseNextHopRefCount(nh);
```

nexthop が NeighOrch に未登録の場合はそのホップをスキップし、
登録済みになるまで FG グループメンバーとして機能しない。

### 3. PortsOrch (PORT / PORTCHANNEL) — link oper-state 監視

```cpp
// fgnhgorch.cpp:46
case SUBJECT_TYPE_PORT_OPER_STATE_CHANGE:

// fgnhgorch.cpp:1374
if (gPortsOrch->getPort(nhk.alias, p))

// fgnhgorch.cpp:1377
if (p.m_type == Port::PHY) { // PHY ポートのみ link 追跡
    fg_nh_info.link = p.m_alias;
    ...
}
```

PortsOrch の Observer パターンで PORT の oper-state 変化を受信し、
バンク再分配をトリガーする。YANG では `FG_NHG_MEMBER.link` が
PORT/PORTCHANNEL の union leafref だが、実装上は Port::PHY のみ追跡。

### 4. STATE_DB:STATE_FG_ROUTE_TABLE — warm-restart 用書き込み

```cpp
// fgnhgorch.cpp:31
m_stateWarmRestartRouteTable(stateDb, STATE_FG_ROUTE_TABLE_NAME),
```

warm-restart 時に FG ルート状態を保存・復旧するためのテーブル。
通常運用時はほぼ読み取りのみ。

### 5. VRFOrch — VRF refcount 管理

```cpp
// fgnhgorch.cpp:1326
m_vrfOrch->increaseVrfRefCount(vrf_id);
```

VRF 使用時に refcount を増減。デフォルト VRF (gVirtualRouterId) では
実質的に noop に近い。

## NEXTHOP / ROUTE 暗黙依存まとめ

| 依存対象 | 参照種別 | 未解決時の挙動 |
|---------|---------|--------------|
| APPL_DB ROUTE_TABLE | 読み書き | FG_NHG_PREFIX SET/DEL が永久 `return false` リトライ |
| NeighOrch (NEIGH_TABLE) | 読み取り | 未解決 nexthop はスキップ・FG グループメンバー化されない |
| PortsOrch (PORT/PORTCHANNEL) | Observer | link oper-state 連動が無効化 (リンクダウン時の自動除去なし) |
| STATE_DB STATE_FG_ROUTE_TABLE | 書き込み | warm-restart 時の状態復旧が失敗 |
| VRFOrch | 読み書き | VRF refcount 不整合 |

## 結論

YANG leafref は `FG_NHG_MEMBER.link` → PORT/PORTCHANNEL の union のみ。
しかし実装上は ROUTE_TABLE (APPL_DB) への直接書き込みと
NeighOrch を通じた nexthop 解決が不可欠であり、これらは YANG には現れない暗黙の必須依存関係。
