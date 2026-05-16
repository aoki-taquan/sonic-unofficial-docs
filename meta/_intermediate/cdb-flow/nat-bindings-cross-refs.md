# NAT_BINDINGS — Phase C: 暗黙参照テーブル分析 (cross-refs)

対象ドキュメント: `docs/reference/config-db/nat-bindings.md`
解析日: 2026-05-16
根拠ソース: `sonic-swss/orchagent/natorch.cpp`

---

## 目的

`NAT_BINDINGS` エントリが CONFIG_DB に書かれたとき、`NatOrch` が **暗黙的に**
参照・依存する他テーブルのキー / フィールドを `natorch.cpp` から抽出する。
YANG 定義や natmgr に明示された依存（NAT_POOL leafref、ACL_TABLE 購読）に加え、
orchagent 固有の暗黙依存を列挙する。

---

## 1. NAT_GLOBAL テーブル (admin_mode) — 有効化ガード

### 参照箇所

`NatOrch::isNatEnabled()` — `natorch.cpp:2345-2353`

```cpp
bool NatOrch::isNatEnabled(void)
{
    if (admin_mode == "enabled")
        return true;
    return false;
}
```

`NatOrch::addNatEntry()` — `natorch.cpp:1907-1914`

```cpp
if (!isNatEnabled())
{
    SWSS_LOG_WARN("NAT Feature is not yet enabled, skipped adding %s %s NAT entry ...",
                  entry.entry_type.c_str(), entry.nat_type.c_str(), ...);
    return true;
}
```

同じガードが `addHwDnatPoolEntry()` (L1789)、`addTwiceNatEntry()` (L2009)、
`addHwSnatEntry()` (L2137)、`addHwDnatEntry()` (L2294) にも存在する。

### 依存内容

| 参照方向 | 依存フィールド | 参照先テーブル | 参照先キー | 依存内容 | 証跡 |
|---------|-------------|--------------|----------|---------|------|
| NatOrch → NAT_GLOBAL | `admin_mode` | `NAT_GLOBAL` | `NAT_GLOBAL\|Values` | `admin_mode=enabled` が APP_DB に伝播するまで、NAT_BINDINGS に対応する SAI SNAT/DNAT エントリは登録されない。`enableNatFeature()` で `admin_mode = "enabled"` がセットされた後、未追加エントリを `addAllNatEntries()` で一括追加する | `natorch.cpp:2345-2353`, `natorch.cpp:1907`, `natorch.cpp:2534-2581` |

### 解決タイミング

`doNatGlobalTableTask()` (`natorch.cpp:2904-2966`) が `APP_NAT_GLOBAL_TABLE` の
`admin_mode=enabled` を検出して `enableNatFeature()` を呼ぶ。
`enableNatFeature()` 内で `addAllNatEntries()` が実行され、
キャッシュ (`m_natEntries`) に積まれていた NAT エントリが SAI に一括投入される。

---

## 2. NAT_POOL テーブル (DNAT pool) — DNAT pool エントリ依存

### 参照箇所

`NatOrch::enableNatFeature()` — `natorch.cpp:2576-2580`

```cpp
SWSS_LOG_INFO("Adding DNAT Pool Entries ");
addAllDnatPoolEntries();

SWSS_LOG_INFO("Adding NAT Entries ");
addAllNatEntries();
```

`NatOrch::addAllDnatPoolEntries()` — `natorch.cpp:1854-1864`

```cpp
void NatOrch::addAllDnatPoolEntries()
{
    DnatPoolEntry::iterator dnatPoolIter = m_dnatPoolEntries.begin();
    while (dnatPoolIter != m_dnatPoolEntries.end())
    {
        addHwDnatPoolEntry((*dnatPoolIter));
        dnatPoolIter++;
    }
}
```

`NatOrch::doDnatPoolTableTask()` — `natorch.cpp:2968-3031`
APP_DB の `NAT_DNAT_POOL_TABLE` を購読し、pool の各 IP を SAI `SAI_NAT_TYPE_DESTINATION_NAT_POOL` エントリとして管理する。

### 依存内容

| 参照方向 | 依存フィールド | 参照先テーブル | 参照先キー | 依存内容 | 証跡 |
|---------|-------------|--------------|----------|---------|------|
| NatOrch → NAT_POOL (APPL_DB 経由) | `nat_ip` (pool IP アドレス群) | `APP_NAT_DNAT_POOL_TABLE` (APPL_DB) | `NAT_DNAT_POOL_TABLE\|<ip>` | NAT_POOL の各 IP は `natmgrd` 経由で APPL_DB に DNAT pool エントリとして書き込まれる。NatOrch が `doDnatPoolTableTask()` でこれを受信し、SAI `SAI_NAT_TYPE_DESTINATION_NAT_POOL` エントリを作成する。NAT_BINDINGS による dynamic SNAT が機能するには、対応する DNAT pool エントリが SAI に登録されている必要がある | `natorch.cpp:2968-3031`, `natorch.cpp:1854-1864` |
| NAT_BINDINGS.nat_pool → NAT_POOL.name (YANG leafref) | `nat_pool` | `NAT_POOL` | `NAT_POOL\|<name>` | YANG バリデーション強制参照整合性。`NAT_BINDINGS` を追加する際、`nat_pool` に指定した名前が `NAT_POOL` に存在しなければ YANG レベルで拒否される | `sonic-nat.yang:271` |

---

## 3. ACL_TABLE / ACL_RULE テーブル — dynamic NAT の ACL バインディング

### 参照箇所

`natmgrd.cpp:119-120` (購読テーブル登録):

```cpp
// doNatAclTableTask() を呼ぶために CFG_ACL_TABLE_TABLE_NAME を購読
// doNatAclRuleTask() を呼ぶために CFG_ACL_RULE_TABLE_NAME を購読
```

`NatMgr::doNatAclTableTask()` — `natmgr.cpp:7750-7900`
ACL TABLE の `type=L3` / `stage=INGRESS` のエントリのみを
`m_natAclTableInfo[aclId] = interface` としてキャッシュする。

`NAT_BINDINGS` の `access_list` フィールドに指定された ACL 名がこのキャッシュに存在する場合、
`setDynamicAclbasedRules()` が対象インタフェースを特定して iptables SNAT ルールを設定する。

### 依存内容

| 参照方向 | 依存フィールド | 参照先テーブル | 参照先キー | 依存内容 | 証跡 |
|---------|-------------|--------------|----------|---------|------|
| NAT_BINDINGS → ACL_TABLE | `access_list` → ACL テーブル名 | `ACL_TABLE` | `ACL_TABLE\|<table_id>` | `NAT_BINDINGS.access_list` に指定した ACL 名が `ACL_TABLE` に `type=L3, stage=INGRESS` で登録されていない場合、binding の iptables SNAT ルールはスキップされる。ACL 登録後に `doNatAclTableTask()` が再評価して自動適用される | `natmgr.cpp:7750-7900`, `natmgrd.cpp:119` |
| NAT_BINDINGS → ACL_RULE | `access_list` (参照テーブルのルール) | `ACL_RULE` | `ACL_RULE\|<table_id>\|<rule_id>` | ACL_RULE が追加・削除されると NAT binding の有効性を再評価し、iptables MASQUERADE / SNAT ルールを更新する | `natmgr.cpp:doNatAclRuleTask()`, `natmgrd.cpp:120` |

---

## 4. RouteOrch observer — DNAT translated IP next-hop 追跡 (BRCM 専用)

### 参照箇所

`NatOrch::addHwDnatEntry()` — `natorch.cpp:414`

```cpp
if (gNhTrackingSupported == true)
{
    m_routeOrch->attach(this, translatedIp);  // next-hop 変化を subscribe
}
```

`NatOrch::updateNextHop()` — `natorch.cpp:200-257`
`SubjectType::SUBJECT_TYPE_NEXTHOP_CHANGE` イベント受信時に `addNhCacheDnatEntries()` で
SAI DNAT エントリを差し替える。

### 依存内容

| 参照方向 | 依存内容 | 証跡 |
|---------|---------|------|
| NatOrch → RouteOrch | DNAT エントリ追加時に translated IP の next-hop 変化を subscribe。BRCM プラットフォームのみ有効 (`gNhTrackingSupported == true`)。非 BRCM では経路変更時に DNAT エントリが stale になるリスクあり | `natorch.cpp:414,458,504,591`, `natorch.cpp:144-148` |

---

## 5. NeighOrch observer — DNAT translated IP ARP/neighbor 解決 (BRCM 専用)

### 参照箇所

`NatOrch::enableNatFeature()` — `natorch.cpp:2573`

```cpp
if (gNhTrackingSupported == true)
{
    SWSS_LOG_INFO("Attach to Neighbor Orch ");
    m_neighOrch->attach(this);
}
```

`NatOrch::updateNeighbor()` — `natorch.cpp:259-302`
`SubjectType::SUBJECT_TYPE_NEIGH_CHANGE` を受信し、
`m_nhResolvCache` にキャッシュされた DNAT translated IP と一致する場合に
`addNhCacheDnatEntries(ip, 1/0)` で SAI エントリを追加/削除する。

### 依存内容

| 参照方向 | 依存内容 | 証跡 |
|---------|---------|------|
| NatOrch → NeighOrch | `enableNatFeature()` 時に全 neighbor の ARP 解決状態を subscribe。DNAT translated IP が neighbor として解決済みかつ next-hop が有効な場合のみ SAI DNAT エントリを登録する二段階ガード。`disableNatFeature()` 時に detach | `natorch.cpp:2573,2610`, `natorch.cpp:259-302` |

---

## cross-refs ブロック（最終形）

以下を `docs/reference/config-db/nat-bindings.md` の `<!-- /ordering -->` 直後に挿入する。

```markdown
<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`NAT_BINDINGS` エントリが処理される際に `NatOrch` (`natorch.cpp`) が
暗黙的に依存する他テーブルの関係を示す。

<!-- evidence: sonic-swss/orchagent/natorch.cpp NatOrch::isNatEnabled L2345 / addNatEntry L1907 / enableNatFeature L2534-2581 / addAllDnatPoolEntries L1854 / doDnatPoolTableTask L2968 / addHwDnatEntry L414 / updateNextHop L200 / updateNeighbor L259 -->

| 依存方向 | 参照元 | 参照先テーブル | 参照先キー形式 | 依存内容 | 証跡 |
|---------|--------|--------------|--------------|---------|------|
| NatOrch → NAT_GLOBAL | `admin_mode` キャッシュ (`isNatEnabled()`) | `NAT_GLOBAL` (CONFIG_DB → APP_NAT_GLOBAL_TABLE) | `NAT_GLOBAL\|Values` | `admin_mode=enabled` が APP_DB に伝播するまで、NAT_BINDINGS に対応する SAI エントリは登録されない。`enableNatFeature()` で有効化後に `addAllNatEntries()` で一括追加 | `natorch.cpp:2345`, `natorch.cpp:1907`, `natorch.cpp:2534-2581` |
| NatOrch → NAT_POOL (APPL_DB 経由) | `doDnatPoolTableTask()` — `m_dnatPoolEntries` | `APP_NAT_DNAT_POOL_TABLE` (APPL_DB) | `NAT_DNAT_POOL_TABLE\|<ip>` | NAT_POOL の各 IP が APPL_DB に DNAT pool エントリとして書き込まれ、NatOrch が SAI `SAI_NAT_TYPE_DESTINATION_NAT_POOL` エントリを作成する。`enableNatFeature()` 内で `addAllDnatPoolEntries()` として一括適用される | `natorch.cpp:2968-3031`, `natorch.cpp:1854-1864`, `natorch.cpp:2576` |
| NAT_BINDINGS → NAT_POOL (YANG leafref) | `nat_pool` フィールド | `NAT_POOL` | `NAT_POOL\|<name>` | YANG バリデーション強制参照整合性。`nat_pool` に指定した名前が `NAT_POOL` に存在しなければ YANG レベルで拒否される | `sonic-nat.yang:271` |
| NAT_BINDINGS → ACL_TABLE | `access_list` フィールド → ACL 名 | `ACL_TABLE` | `ACL_TABLE\|<table_id>` | `access_list` に指定した ACL が `type=L3, stage=INGRESS` で未登録の場合、iptables SNAT ルールがスキップされる。ACL 登録後に `doNatAclTableTask()` が自動再評価 | `natmgr.cpp:7750-7900`, `natmgrd.cpp:119` |
| NAT_BINDINGS → ACL_RULE | `access_list` フィールド → ACL ルール | `ACL_RULE` | `ACL_RULE\|<table_id>\|<rule_id>` | ACL_RULE の追加・削除が NAT binding の iptables MASQUERADE / SNAT ルールを再評価・更新する | `natmgr.cpp:doNatAclRuleTask()`, `natmgrd.cpp:120` |
| NatOrch → RouteOrch (BRCM 専用) | `addHwDnatEntry()` — `m_routeOrch->attach()` | RouteOrch (SUBJECT_TYPE_NEXTHOP_CHANGE) | — | DNAT エントリ追加時に translated IP の next-hop 変化を subscribe。BRCM プラットフォームのみ有効 | `natorch.cpp:414,458,504,591`, `natorch.cpp:144-148` |
| NatOrch → NeighOrch (BRCM 専用) | `enableNatFeature()` — `m_neighOrch->attach()` | NeighOrch (SUBJECT_TYPE_NEIGH_CHANGE) | — | NAT 有効化時に全 neighbor の ARP 解決状態を subscribe し、DNAT translated IP の SAI エントリを neighbor 解決タイミングで差し替える | `natorch.cpp:2573,2610`, `natorch.cpp:259-302` |

### 解決タイミング

- **NAT_GLOBAL `admin_mode` 依存**: `doNatGlobalTableTask()` が `APP_NAT_GLOBAL_TABLE` の `admin_mode=enabled` を検出して `enableNatFeature()` → `addAllNatEntries()` を呼ぶ。有効化前に受信した NAT エントリはキャッシュ (`m_natEntries`) に積まれ、有効化後に一括 SAI 投入される。
- **NAT_POOL (DNAT pool) 依存**: `doDnatPoolTableTask()` が APPL_DB の `APP_NAT_DNAT_POOL_TABLE` を購読し、pool IP ごとに即時 SAI エントリ作成。`enableNatFeature()` 内で `addAllDnatPoolEntries()` として未投入分を一括追加。
- **ACL_TABLE / ACL_RULE 依存**: `doNatAclTableTask()` / `doNatAclRuleTask()` が CONFIG_DB の変化を購読。ACL の登録・削除のたびに iptables SNAT ルールを再評価。未解決の ACL 名は次回 ACL 登録時に自動補完される。
- **RouteOrch / NeighOrch observer (BRCM 専用)**: `gNhTrackingSupported == true` のときのみ有効。DNAT translated IP の next-hop / neighbor 解決状態に応じてリアルタイムに SAI DNAT エントリを差し替える。非 BRCM 環境では経路変更時に stale エントリになるリスクあり。
<!-- /cross-refs -->
```
