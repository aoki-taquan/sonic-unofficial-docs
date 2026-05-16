# NAT_BINDINGS — Phase F 副次 DB 書込

調査日: 2026-05-16
ソース: `sonic-swss/orchagent/natorch.cpp` (NatOrch)
対象ページ: `docs/reference/config-db/nat-bindings.md`

---

## 概要

`NAT_BINDINGS` エントリを CONFIG_DB に書込むと、`natmgrd` が ACL + pool 整合性を確認したうえで
iptables ルールを設定し APPL_DB に NAT エントリを書込む。これを `orchagent / NatOrch` が消費して
ASIC_DB (SAI nat_entry) へ反映する。副次的に COUNTERS_DB および CRM カウンタが更新される。

---

## 1. ASIC_DB — SAI nat_entry 書込

`NatOrch` が `sai_nat_api` 経由でハードウェアに NAT エントリを書込む。syncd が ASIC_DB を介して ASIC ドライバへ転送する。

### SAI オブジェクト種別と書込関数

| 関数 | SAI nat_type | CRM カウンタ | ソース行 |
|------|-------------|-------------|---------|
| `addHwSnatEntry()` | `SAI_NAT_TYPE_SOURCE_NAT` | `CRM_SNAT_ENTRY +1` | `natorch.cpp:1274-1340` |
| `addHwSnapt Entry()` | `SAI_NAT_TYPE_SOURCE_NAT` (ポート付き) | `CRM_SNAT_ENTRY +1` | `natorch.cpp:1434-1510` |
| `addHwTwiceNatEntry()` | `SAI_NAT_TYPE_DOUBLE_NAT` | — | `natorch.cpp:1346-1440` |
| `addHwDnatPoolEntry()` | `SAI_NAT_TYPE_DESTINATION_NAT_POOL` | `CRM_DNAT_ENTRY +1` | `natorch.cpp:1783-1820` |
| `enableNatFeature()` — `SAI_SWITCH_ATTR_NAT_ENABLE=true` | switch 属性 | — | `natorch.cpp:2555-2560` |

### sai_nat_entry_t フィールド構成

```
sai_nat_entry_t.vr_id     = gVirtualRouterId
sai_nat_entry_t.switch_id = gSwitchId
sai_nat_entry_t.nat_type  = SAI_NAT_TYPE_SOURCE_NAT / SAI_NAT_TYPE_DOUBLE_NAT / ...
sai_nat_entry_t.data.key.src_ip / dst_ip (+ mask)
```

**SAI NAT エントリ属性 (SNAT)**:
- `SAI_NAT_ENTRY_ATTR_SRC_IP`: 変換後 (pool) IP アドレス
- `SAI_NAT_ENTRY_ATTR_SRC_IP_MASK`: マスク (通常 255.255.255.255)
- `SAI_NAT_ENTRY_ATTR_ENABLE_PACKET_COUNT = true`
- `SAI_NAT_ENTRY_ATTR_ENABLE_BYTE_COUNT = true`

NAPT (ポート変換あり) の場合は追加で:
- `SAI_NAT_ENTRY_ATTR_L4_SRC_PORT`: 変換後ポート番号

Twice NAT エントリは `SAI_NAT_TYPE_DOUBLE_NAT` で `SRC_IP` + `DST_IP` 両方を設定。

### 書込条件

1. `isNatEnabled()` が true (NAT_GLOBAL.admin_mode=enabled) であること。
2. dynamic SNAT の場合: `totalSnatEntries < maxAllowedSNatEntries` (SAI `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` 返値)。上限到達時は `"AGEOUT-SINGLE-NAT"` 通知を送り、最古エントリをエージアウトして空きを確保する。
3. DNAT で nexthop tracking 有効時: nexthop 解決後に `addHwDnatEntry()` を呼び出す (NH 解決キャッシュ経由)。

---

## 2. COUNTERS_DB — グローバル + per-entry カウンタ

`NatOrch` が SNAT/DNAT エントリの増減ごとに COUNTERS_DB を更新する。

### グローバルカウンタ (COUNTERS_GLOBAL_NAT|Values)

| フィールド | 更新タイミング |
|-----------|-------------|
| `SNAT_ENTRIES` | SNAT エントリ追加/削除時に `updateSnatCounters()` が書込 |
| `DNAT_ENTRIES` | DNAT エントリ追加/削除時に `updateDnatCounters()` が書込 |
| `DYNAMIC_NAT_ENTRIES` | Dynamic SNAT エントリ数変化時 |
| `DYNAMIC_NAPT_ENTRIES` | Dynamic SNAPT エントリ数変化時 |

ソース: `natorch.cpp:4569-4590`

### per-entry カウンタ (COUNTERS_NAT|<global_ip>)

| テーブル | キー | フィールド | 更新周期 |
|---------|-----|----------|---------|
| `COUNTERS_NAT` | `<global_ip>` | `NAT_TRANSLATIONS_PKTS`, `NAT_TRANSLATIONS_BYTES` | NAT hitbit タイマー (5秒周期) |
| `COUNTERS_NAPT` | `<proto>:<ip>:<port>` | 同上 | 同上 |
| `COUNTERS_TWICE_NAT` | `<src_ip>:<dst_ip>` | 同上 | 同上 |
| `COUNTERS_TWICE_NAPT` | `<proto>:<src_ip>:<src_port>:<dst_ip>:<dst_port>` | 同上 | 同上 |

ソース: `natorch.cpp:51-56, 4060, 4067`

---

## 3. CRM (Critical Resource Management) カウンタ更新

SAI エントリ追加/削除時に `gCrmOrch` のカウンタを増減する。

| 操作 | CRM リソース | ソース行 |
|------|------------|---------|
| SNAT エントリ追加 | `incCrmResUsedCounter(CRM_SNAT_ENTRY)` | `natorch.cpp:1325, 1496` |
| SNAT エントリ削除 | `decCrmResUsedCounter(CRM_SNAT_ENTRY)` | `natorch.cpp:1647, 1736` |
| DNAT エントリ追加 | `incCrmResUsedCounter(CRM_DNAT_ENTRY)` | `natorch.cpp:791, 874` |
| DNAT エントリ削除 | `decCrmResUsedCounter(CRM_DNAT_ENTRY)` | `natorch.cpp:944, 1132` |

CRM カウンタは `show crm resources all` で参照可能。

---

## 4. STATE_DB — 書込なし

`NatOrch` および `NatMgr` はともに STATE_DB への書込を行わない。  
STATE_DB の `STATE_PORT_TABLE` / `STATE_LAG_TABLE` / `STATE_VLAN_TABLE` / `STATE_INTERFACE_TABLE` は
**読み取り専用** (L3 インタフェース readiness ガード用)。

---

## 書込タイミングまとめ

```
NAT_BINDINGS SET (CONFIG_DB)
  └─ natmgrd (NatMgr::doNatBindingTask)
       ├─ m_natBindingInfo キャッシュ更新
       ├─ iptables ルール設定 (kernel netfilter)
       └─ APPL_DB APP_NAT_TABLE / APP_NAT_DNAT_POOL_TABLE SET
            └─ orchagent (NatOrch::doNatTableTask / doDnatPoolTableTask)
                 ├─ addNatEntry() → addHwSnatEntry()
                 │     ├─ sai_nat_api->create_nat_entry(SAI_NAT_TYPE_SOURCE_NAT) → syncd → ASIC_DB
                 │     ├─ gCrmOrch->incCrmResUsedCounter(CRM_SNAT_ENTRY)
                 │     └─ updateSnatCounters() → COUNTERS_DB COUNTERS_GLOBAL_NAT|Values.SNAT_ENTRIES
                 ├─ addHwDnatPoolEntry()
                 │     ├─ sai_nat_api->create_nat_entry(SAI_NAT_TYPE_DESTINATION_NAT_POOL) → syncd → ASIC_DB
                 │     └─ gCrmOrch->incCrmResUsedCounter(CRM_DNAT_ENTRY)
                 └─ NAT hitbit タイマー (5秒)
                       └─ sai_nat_api->get_nat_entry_attribute() → COUNTERS_DB COUNTERS_NAT|<ip>
```

---

## 証跡サマリ

| 書込先 | テーブル/オブジェクト | コンポーネント | evidence |
|-------|------------------|-------------|---------|
| ASIC_DB (SAI_NAT_TYPE_SOURCE_NAT) | SAI nat_entry | NatOrch | `natorch.cpp:1302-1326` |
| ASIC_DB (SAI_NAT_TYPE_DESTINATION_NAT_POOL) | SAI nat_entry | NatOrch | `natorch.cpp:1783-1805` |
| ASIC_DB (SAI_NAT_TYPE_DOUBLE_NAT) | SAI nat_entry (Twice NAT) | NatOrch | `natorch.cpp:1379-1413` |
| COUNTERS_DB `COUNTERS_GLOBAL_NAT` | `SNAT_ENTRIES`, `DNAT_ENTRIES` | NatOrch | `natorch.cpp:4569-4590` |
| COUNTERS_DB `COUNTERS_NAT` | `NAT_TRANSLATIONS_PKTS/BYTES` | NatOrch | `natorch.cpp:4060` |
| CRM カウンタ (内部) | `CRM_SNAT_ENTRY`, `CRM_DNAT_ENTRY` | NatOrch | `natorch.cpp:1325, 791` |
| STATE_DB | — | — | 書込なし |
