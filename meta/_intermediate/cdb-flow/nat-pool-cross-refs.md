# nat-pool-cross-refs — Phase C 調査メモ

対象ページ: `docs/reference/config-db/nat-pool.md`
対象テーブル: `NAT_POOL`
調査日: 2026-05-16

## 調査対象ファイル

- `sonic-swss/cfgmgr/natmgr.cpp`（`doNatPoolTask` L6482–6866、`addDynamicNatRule` L4621–4680、`getIpEnabledIntf` L236–255、`isPoolMappedtoBinding` L182–200）
- `sonic-swss/orchagent/natorch.cpp`（`doDnatPoolTableTask` L2968–3031、`addAllDnatPoolEntries` L1854–1863、`enableNatFeature` L2534–2581）
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-nat.yang`

## 暗黙参照テーブル (Phase C) — NAT_POOL 視点

### 依存関係サマリ

`NAT_POOL` の処理は `natmgrd`（natmgr.cpp）と `orchagent/NatOrch`（natorch.cpp）の両層で複数の外部テーブルに依存する。

#### 1. NAT_GLOBAL (CONFIG_DB) — admin_mode 依存

`addDynamicNatRule()` (`natmgr.cpp:4632`) 冒頭で `isNatEnabled()` を呼び出す。NAT_GLOBAL の `admin_mode=enabled` が
APP_DB (`APP_NAT_GLOBAL_TABLE`) に伝播するまで pool の iptables / APPL_DB 反映は行われない。

#### 2. INTERFACE / PORTCHANNEL_INTERFACE / VLAN_INTERFACE (CONFIG_DB) — L3 インタフェース依存

`addDynamicNatRule()` (`natmgr.cpp:4654–4659`) は `getIpEnabledIntf(nat_ip[0], pool_interface)` を呼び、
`m_natIpInterfaceInfo` キャッシュ（各インタフェースのサブネット一覧）に pool の `nat_ip` 低位アドレスが含まれるかを確認する。
L3 インタフェース（`nat_zone` 設定済み）が有効化されていない場合は dynamic NAT ルールをスキップ。

`m_natIpInterfaceInfo` は `doNatInterfaceTask()` が `CFG_INTF_TABLE_NAME` / `CFG_LAG_INTF_TABLE_NAME` / `CFG_VLAN_INTF_TABLE_NAME` / `CFG_LOOPBACK_INTERFACE_TABLE_NAME` の変更を受けて更新する (`natmgr.cpp:8179`)。

#### 3. NAT_BINDINGS (CONFIG_DB) — 双方向参照

`doNatPoolTask()` (`natmgr.cpp:6815–6822`) 末尾で `isPoolMappedtoBinding(key, binding_name)` を使いすべての binding をイテレートし、
この pool を参照している binding があれば `addDynamicNatRule(binding_name)` を自動呼び出しする。
pool 追加時と pool 更新時の双方で binding の再適用が走る。

NAT_BINDINGS の `nat_pool` フィールドは YANG leafref で `NAT_POOL` を参照強制（sonic-nat.yang:271）。

#### 4. STATIC_NAT (CONFIG_DB) — IP 重複チェック

`doNatPoolTask()` (`natmgr.cpp:6748–6775`) は `m_staticNatEntry` をイテレートし、
pool の `nat_ip` 範囲が `STATIC_NAT` の global IP (`nat_globally_unique` IP) と重複する場合に silent drop する。

```cpp
// natmgr.cpp:6760-6773 (抜粋)
if ((static_address >= ipv4_addr_low) and (static_address <= ipv4_addr_high))
{
    isOverlap = true;
    break;
}
...
SWSS_LOG_ERROR("Pool Ip address is overlaps with static NAT entry, skipping %s", key.c_str());
```

#### 5. APP_NAT_DNAT_POOL_TABLE (APPL_DB) — NatOrch 中継

`natmgrd` は `setDnatPoolfromNatPool(ADD, ip_range)` で APPL_DB の `NAT_DNAT_POOL_TABLE` に pool IP ごとのエントリを書き込む。
`NatOrch::doDnatPoolTableTask()` (`natorch.cpp:2968`) がこれを購読し、SAI `SAI_NAT_TYPE_DESTINATION_NAT_POOL` エントリを作成する。
pool と NatOrch は直接 CONFIG_DB を共有せず、APPL_DB 経由でのみ通信する。

### 依存テーブル一覧

| 依存方向 | 参照元 | 参照先テーブル | 参照先キー形式 | 依存内容 | 証跡 |
|---------|--------|--------------|--------------|---------|------|
| natmgr → NAT_GLOBAL | `addDynamicNatRule()` — `isNatEnabled()` | `NAT_GLOBAL` (CONFIG_DB) / `APP_NAT_GLOBAL_TABLE` (APPL_DB) | `NAT_GLOBAL\|Values` | `admin_mode=enabled` が APPL_DB に伝播するまで pool の iptables / APPL_DB 反映をスキップ | `natmgr.cpp:4632-4636` |
| natmgr → INTERFACE 系 | `addDynamicNatRule()` — `getIpEnabledIntf()` | `INTERFACE` / `PORTCHANNEL_INTERFACE` / `VLAN_INTERFACE` (CONFIG_DB) | 各インタフェース名 | pool `nat_ip` 低位アドレスのサブネットに一致する L3 インタフェース (nat_zone 設定済み) が必要 | `natmgr.cpp:4654-4659`, `natmgr.cpp:8179` |
| natmgr → NAT_BINDINGS | `doNatPoolTask()` — `isPoolMappedtoBinding()` | `NAT_BINDINGS` (CONFIG_DB) | `NAT_BINDINGS\|<name>` | pool 追加・更新時に参照 binding を自動再評価して `addDynamicNatRule()` を再呼び出し | `natmgr.cpp:6815-6822`, `natmgr.cpp:182-200` |
| NAT_BINDINGS → NAT_POOL | YANG leafref (`nat_pool` フィールド) | `NAT_POOL` (CONFIG_DB) | `NAT_POOL\|<name>` | YANG バリデーション参照整合性。pool が存在しない場合は YANG レベルで拒否 | `sonic-nat.yang:271` |
| natmgr → STATIC_NAT | `doNatPoolTask()` — m_staticNatEntry 走査 | `STATIC_NAT` (CONFIG_DB) | `STATIC_NAT\|<ip>` | pool `nat_ip` 範囲が STATIC_NAT global IP と重複する場合 silent drop | `natmgr.cpp:6748-6775` |
| natmgr → APP_NAT_DNAT_POOL_TABLE | `setDnatPoolfromNatPool()` | `NAT_DNAT_POOL_TABLE` (APPL_DB) | `NAT_DNAT_POOL_TABLE\|<ip>` | pool の各 IP を APPL_DB に書き込み NatOrch に伝達。NatOrch は SAI DESTINATION_NAT_POOL エントリを作成 | `natmgr.cpp:2276-2277`, `natorch.cpp:2968-3031` |
