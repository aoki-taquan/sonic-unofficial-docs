# nat-zone — Phase F side-effects (intermediate evidence)

slug: nat-zone
phase: F (side-effects)
target: docs/reference/config-db/nat-zone.md

## Evidence sources

- `sonic-swss/cfgmgr/natmgr.cpp` `doNatZoneIntfTask` L7493-7628
- `sonic-swss/cfgmgr/natmgr.cpp` `setMangleIptablesRules` L894-924
- `sonic-swss/orchagent/intfsorch.cpp` `setRouterIntfsNatZoneId` L272-303
- `sonic-swss/orchagent/intfsorch.cpp` `doTask` nat_zone SET L974-985

## Summary

`nat_zone` SET/DEL から発生する副次書込みは以下の 2 系統:

### 1. natmgrd 系 (kernel iptables — 非 DB)

- `setMangleIptablesRules(ADD/DELETE, port, mark)` が `/sbin/iptables -t mangle` を呼び出して
  PREROUTING/POSTROUTING MARK ルールを追加/削除する。
- Loopback インタフェースはスキップ (`natmgr.cpp:7549-7551`)。
- ゾーン変更時のみ: `removeStaticNatIptables()`, `removeStaticNaptIptables()`,
  `removeDynamicNatRules()` → `addStaticNatIptables()`, `addDynamicNatRules()` の順で
  kernel nat テーブルのルールを再構築する (`natmgr.cpp:7534-7568`)。

### 2. orchagent 系 (ASIC_DB via SAI)

- `setRouterIntfsNatZoneId(port)` が `sai_router_intfs_api->set_router_interface_attribute()`
  を呼び `SAI_ROUTER_INTERFACE_ATTR_NAT_ZONE_ID` を設定する (`intfsorch.cpp:285-286`)。
- `gIsNatSupported == false` の場合は silent skip (`intfsorch.cpp:977-985`)。

### 3. APPL_DB / STATE_DB / FLEX_COUNTER_DB

`doNatZoneIntfTask` の処理パスでは Redis 系 DB への副次書込みなし。
