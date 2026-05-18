# nat-app — Phase F: 副次 DB 書込スキャン

## 調査対象ソース

- `sonic-swss/orchagent/natorch.cpp` (NatOrch 主消費者)
- `sonic-swss/natsyncd/natsync.cpp` (NatSync: dynamic エントリ書込元)
- `sonic-swss/cfgmgr/natmgr.cpp` (NatMgr: static エントリ書込元)

## NatOrch が APPL_DB エントリ消費時に書き込む副次 DB

### 1. COUNTERS_DB — COUNTERS_NAT (per-entry)

`NatOrch::updateNatCounters()` (natorch.cpp:4049-4061) が NAT_TABLE 各エントリの統計をポーリング周期ごとに更新する。

キー: `<global_ip>` (NAT_TABLE), `<proto>:<global_ip>:<global_port>` (NAPT_TABLE), `<src_ip>:<dst_ip>` (TWICE_NAT), etc.
フィールド: `NAT_TRANSLATIONS_PKTS`, `NAT_TRANSLATIONS_BYTES`

テーブル名:
- `COUNTERS_NAT` (COUNTERS_NAT_TABLE, schema.h:260) — NAT_TABLE エントリ
- `COUNTERS_NAPT` (COUNTERS_NAPT_TABLE, schema.h:261) — NAPT_TABLE エントリ
- `COUNTERS_TWICE_NAT` (schema.h:262) — NAT_TWICE_TABLE エントリ
- `COUNTERS_TWICE_NAPT` (schema.h:263) — NAPT_TWICE_TABLE エントリ

### 2. COUNTERS_DB — COUNTERS_GLOBAL_NAT (aggregate counts)

`NatOrch::updateStaticNatCounters()` 他 (natorch.cpp:4481-4588) が各テーブルの合計エントリ数を `key="Values"` に書き込む。

フィールド (すべて int):
- `STATIC_NAT_ENTRIES`, `STATIC_NAPT_ENTRIES`, `STATIC_TWICE_NAT_ENTRIES`, `STATIC_TWICE_NAPT_ENTRIES`
- `DYNAMIC_NAT_ENTRIES`, `DYNAMIC_NAPT_ENTRIES`, `DYNAMIC_TWICE_NAT_ENTRIES`, `DYNAMIC_TWICE_NAPT_ENTRIES`
- `SNAT_ENTRIES`, `DNAT_ENTRIES`

### 3. SAI switch attribute (admin_mode → SAI_SWITCH_ATTR_NAT_ENABLE)

`NatOrch::enableNatFeature()` / `disableNatFeature()` (natorch.cpp:2534-2615) が `NAT_GLOBAL_TABLE.admin_mode` の変化に応じて `sai_switch_api->set_switch_attribute(gSwitchId, SAI_SWITCH_ATTR_NAT_ENABLE=true/false)` を呼ぶ。これは ASIC_DB 経由ではなく直接 SAI call。

### 4. APPL_DB — SETTIMEOUTNAT (notification channel)

`NatOrch` が `m_natTimeoutTimer` タイムアウト時に `NotificationProducer(appDb, "SETTIMEOUTNAT")` 経由でエージングアウト通知を送信 (natorch.cpp:1888, 2002, 2118, 2287, 3336-3501)。`natsyncd / NatSync` が同一 notification channel を購読し kernel conntrack エントリを削除する。APPL_DB NAT テーブルのエントリを間接的に削除するループになる。

### 5. RouteOrch nexthop 追跡 (DNAT)

`NatOrch::addDnatToNhCache()` / `removeDnatFromNhCache()` (natorch.cpp:408-560) が translated-ip (DNAT 先アドレス) に対して `m_routeOrch->attach(this, translatedIp)` を呼ぶ。ネクストホップ解決が変化したとき `RouteOrch` から `NatOrch::update()` コールバックが届き SAI 操作可否を再評価する。APPL_DB / COUNTERS_DB への書込みはない (純粋 in-process)。

## 検出されなかった副次書込

- STATE_DB への直接書込みなし (NatOrch は stateDb ポインタを受け取るが使用しない)
- FLEX_COUNTER_DB への書込みなし
- CONFIG_DB への書込みなし
- LOGLEVEL_DB への書込みなし

## Evidence

- `natorch.cpp:51-56` (COUNTERS_DB テーブル初期化)
- `natorch.cpp:4049-4134` (updateNatCounters / updateNaptCounters / updateTwiceNatCounters)
- `natorch.cpp:4481-4588` (updateStaticNatCounters … updateDnatCounters)
- `natorch.cpp:2534-2615` (enableNatFeature / disableNatFeature → SAI_SWITCH_ATTR_NAT_ENABLE)
- `natorch.cpp:137, 1888, 2002, 2118, 2287, 3336-3501` (SETTIMEOUTNAT notification)
- `natorch.cpp:408-560, 591-648` (routeOrch attach/detach for DNAT NH tracking)
- `sonic-swss-common/common/schema.h:260-264` (COUNTERS_NAT* table name defines)
