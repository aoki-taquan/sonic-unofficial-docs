# nat-pool-ordering — Phase B 調査メモ

対象ページ: `docs/reference/config-db/nat-pool.md`
対象テーブル: `NAT_POOL`
調査日: 2026-05-16

## 調査対象ファイル

- `sonic-swss/cfgmgr/natmgr.cpp`（`doNatPoolTask` L6482–6866、`addDynamicNatRule` L4621–4680、`isNatEnabled` L150）
- `sonic-swss/orchagent/natorch.cpp`（`enableNatFeature` L2534–2581、`addAllDnatPoolEntries` L1854–1863、`doDnatPoolTableTask` L2968–3031）

## 書込み順依存 (Phase B) — NAT_POOL 視点

### 前提依存: NAT_GLOBAL (admin_mode=enabled) が先行必須

`addDynamicNatRule()` (`natmgr.cpp:4632-4636`) 冒頭で `isNatEnabled()` を確認し、false の場合は処理をスキップする:

```cpp
// natmgr.cpp:4632-4636
if (!isNatEnabled())
{
    SWSS_LOG_INFO("NAT is not yet enabled, skipping dynamic nat rules addition for %s", key.c_str());
    return;
}
```

つまり `NAT_POOL` を先に書いても `admin_mode=disabled` のままでは iptables / APPL_DB のルール設定は行われない。
`NAT_GLOBAL|Values` に `admin_mode=enabled` を書いた後でなければ pool の実効化は行われない。

### NAT_POOL は NAT_BINDINGS より先行が必要

`addDynamicNatRule()` (`natmgr.cpp:4638-4643`) は binding 処理時に pool キャッシュを参照する:

```cpp
// natmgr.cpp:4638-4643
if (m_natPoolInfo.find(pool_name) == m_natPoolInfo.end())
{
    SWSS_LOG_INFO("Pool %s is not yet enabled, skipping dynamic nat rules addition for %s", pool_name.c_str(), key.c_str());
    return;
}
```

`NAT_POOL` が `m_natPoolInfo` キャッシュに存在しない場合は binding が来ても動的 NAT ルールをスキップする。ただし **エントリは失われない**: pool が後から追加されると `doNatPoolTask()` L6816-6822 の末尾 `addDynamicNatRule(binding_name)` が再トリガーされる仕組みになっている。

推奨順序:
```
SET NAT_GLOBAL|Values    admin_mode=enabled          # NAT feature を有効化
SET NAT_POOL|<name>      nat_ip=...  nat_port=...    # pool を先に定義
SET NAT_BINDINGS|<name>  nat_pool=<name>              # pool 登録後に binding を追加
```

### pool 更新時の自動再適用 (update path)

既存 pool の `nat_ip` / `nat_port` を変更する場合 (`doNatPoolTask` L6779-6801):

```cpp
// natmgr.cpp:6794-6800
if (isPoolMappedtoBinding(key, binding_name))
{
    /* Remove the existing Dynamic NAT rules */
    removeDynamicNatRule(binding_name);
}
// その後 ip_range / port_range をキャッシュに書き直し
// → addDynamicNatRule(binding_name) で再適用
```

pool を変更すると既存 binding に紐づく iptables ルールと APPL_DB `NAT_DNAT_POOL_TABLE` エントリが一旦削除され、新しい pool 情報で再生成される。この間 (数十 ms オーダー) は dynamic NAT セッションが確立できない空白期間が発生しうる。

### DEL 順序 — 安全な削除順序

`doNatPoolTask` DEL パス (`natmgr.cpp:6831-6857`):
- pool が binding にマッピングされている場合、`removeDynamicNatRule(binding_name)` が呼ばれ iptables / APPL_DB の DNAT pool エントリが自動削除される
- CONFIG_DB の `NAT_BINDINGS` エントリは残る (自動削除されない)
- binding を削除せず pool だけ削除した場合、CONFIG_DB には dangling binding が残り次に pool が追加されたタイミングで再接続される

安全な削除手順:
```
DEL NAT_BINDINGS|<name>    # binding を先に削除 (iptables/APPL_DB クリーンアップ)
DEL NAT_POOL|<name>        # pool を後に削除
```

### L3 インタフェース readiness — getIpEnabledIntf() 依存

`addDynamicNatRule()` (`natmgr.cpp:4654-4659`) は pool の `nat_ip[0]`（範囲の低位アドレス）に対応する L3 インタフェースが up かつ有効状態であることを確認する:

```cpp
// natmgr.cpp:4654-4659
if (!getIpEnabledIntf(nat_ip[0], pool_interface))
{
    SWSS_LOG_INFO("L3 Interface is not yet enabled for %s, skipping dynamic nat rules addition", key.c_str());
    return;
}
```

L3 インタフェース (`INTERFACE`/`PORTCHANNEL_INTERFACE`/`VLAN_INTERFACE`) が有効化されていない場合、pool / binding が揃っていても dynamic NAT ルールは設定されない。

### NatOrch 層 (APPL_DB → SAI) での pool 投入順序

`enableNatFeature()` (`natorch.cpp:2576-2580`) は NAT feature 有効化時に以下の順序で処理する:

```cpp
// natorch.cpp:2576-2580
addAllDnatPoolEntries();   // SAI_NAT_TYPE_DESTINATION_NAT_POOL を先に投入
addAllNatEntries();        // SNAT/DNAT/NAPT エントリを後に投入
```

DNAT pool entry (`SAI_NAT_TYPE_DESTINATION_NAT_POOL`) が DNAT entry (`SAI_NAT_TYPE_DESTINATION_NAT`) より必ず先行してハードウェアに投入される設計。
`doDnatPoolTableTask()` (`natorch.cpp:2968-3031`) でも pool entry を `sai_nat_api->create_nat_entry()` で登録してから NAT エントリ処理が行われる。

## 要約

| 依存関係 | 方向 | 遅延時の挙動 | ソース |
|---------|------|------------|-------|
| `NAT_GLOBAL.admin_mode=enabled` → `NAT_POOL` 実効化 | 前提 | pool はキャッシュされるが iptables/APPL_DB 反映なし | `natmgr.cpp:4632` |
| `NAT_POOL` → `NAT_BINDINGS` ルール生成 | 先行推奨 | binding は受理されるが dynamic NAT ルール未生成。pool 追加で自動再トリガー | `natmgr.cpp:4639` |
| L3 インタフェース有効化 → `NAT_POOL` 実効化 | 前提 | インタフェース up 後に再トリガーなし (要 pool 再投入 or binding 再処理) | `natmgr.cpp:4655` |
| `NAT_DNAT_POOL_TABLE`（APPL_DB）→ SAI DNAT pool entry | 先行必須 | `enableNatFeature` が DNAT pool → NAT entry の順序を強制 | `natorch.cpp:2577` |
