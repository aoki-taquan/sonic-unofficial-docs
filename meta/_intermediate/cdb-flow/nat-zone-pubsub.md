# NAT ゾーン設定 (nat_zone フィールド) — Phase G: 通信メカニズム

## 調査対象

- `sonic-swss/cfgmgr/natmgrd.cpp`
- `sonic-swss/cfgmgr/natmgr.cpp`
- `sonic-swss/cfgmgr/intfmgrd.cpp`
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/orchagent/intfsorch.cpp`

## 概要

`nat_zone` フィールドの変更は 2 つの独立した購読経路で伝播する。`natmgrd` は CONFIG_DB を直接購読してカーネル iptables を更新し、`intfmgrd → orchagent (IntfsOrch)` の 2 段経路が SAI RIF 属性を更新する。

## 購読経路

### 経路 A: CONFIG_DB → natmgrd (直接購読) → kernel iptables

`natmgrd` は `INTERFACE` / `PORTCHANNEL_INTERFACE` / `VLAN_INTERFACE` / `LOOPBACK_INTERFACE` の 4 テーブルを直接 `Consumer` (SubscriberStateTable) で購読する (`natmgrd.cpp:109-121`)。`NatMgr::doTask()` が table_name に応じて `doNatZoneIntfTask()` へディスパッチし、`nat_zone` 値を取得して `setMangleIptablesRules()` で iptables mangle MARK ルールを更新する。

```
CONFIG_DB INTERFACE|<port> {nat_zone=N}
  → Consumer(SubscriberStateTable) → NatMgr::doNatZoneIntfTask()
  → setMangleIptablesRules(ADD, port, zone+1)
  → kernel iptables mangle PREROUTING/POSTROUTING MARK
```

### 経路 B-1: CONFIG_DB → intfmgrd → APPL_DB

`intfmgrd` は `CFG_INTF_TABLE_NAME` 等を Consumer で購読し、`IntfMgr::setIntf()` が `nat_zone` フィールドを APPL_DB `INTF_TABLE` に転送する (`intfmgr.cpp:887-889`, `intfmgr.cpp:1053`)。

```
CONFIG_DB INTERFACE|<port> {nat_zone=N}
  → Consumer(SubscriberStateTable) → IntfMgr::setIntf()
  → m_appIntfTableProducer.set(alias, {nat_zone=N})
  → APPL_DB INTF_TABLE|<intf> {nat_zone=N}
```

### 経路 B-2: APPL_DB → orchagent (IntfsOrch) → SAI

`orchdaemon.cpp:296` で `IntfsOrch(m_applDb, APP_INTF_TABLE_NAME, ...)` として生成。Orch 基底クラスが `ConsumerStateTable` を登録し、`doIntfTask()` で `nat_zone` を解析して `setRouterIntfsNatZoneId(port)` 経由で SAI を更新する。

```
APPL_DB INTF_TABLE|<intf> {nat_zone=N}
  → ConsumerStateTable → IntfsOrch::doIntfTask()
  → setRouterIntfsNatZoneId(port)
  → SAI set_router_interface_attribute(SAI_ROUTER_INTERFACE_ATTR_NAT_ZONE_ID)
```

## 冪等性と再起動挙動

- **natmgrd 再起動**: SubscriberStateTable が既存 key をスナップショット再生 → iptables mangle ルールが再構築される
- **orchagent 再起動**: APPL_DB の INTF_TABLE に残存する `nat_zone` フィールドが再読み込みされ SAI RIF zone_id が再適用される
- **intfmgrd 再起動**: CONFIG_DB の全 INTERFACE エントリを再処理し `nat_zone` を APPL_DB に再書き込みする

## evidence

- `natmgrd.cpp:109-121` — SubscriberStateTable 購読テーブル一覧
- `natmgr.cpp:8178-8182` — doNatZoneIntfTask ディスパッチ
- `intfmgrd.cpp:29-44` — intfmgrd 購読テーブル一覧
- `intfmgr.cpp:813-815`, `intfmgr.cpp:887-889`, `intfmgr.cpp:1053` — nat_zone APPL_DB 転送
- `orchdaemon.cpp:296` — IntfsOrch 生成 (APP_INTF_TABLE_NAME)
- `intfsorch.cpp:63` — Orch コンストラクタ (APP_INTF_TABLE_NAME, intfsorch_pri=35)
