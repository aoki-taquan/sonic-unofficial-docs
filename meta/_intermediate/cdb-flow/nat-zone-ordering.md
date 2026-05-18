# nat-zone — Phase B ordering 調査メモ

## 調査対象
- `sonic-swss/cfgmgr/natmgr.cpp` — `doNatIpInterfaceTask` / `NatMgr::isPortStateOk` / `NatMgr::isIntfStateOk`
- `sonic-swss/orchagent/intfsorch.cpp` — `doIntfTask` / `setRouterIntfsNatZoneId`

## natmgr 側の ordering

### key サイズ 1 (ポート単位 / nat_zone フィールドが付くパス)
natmgr.cpp:7484-7490: Loopback 以外はポート状態確認
- Ethernet: STATE_PORT_TABLE が存在するまで it++ でリトライ
- Vlan: STATE_VLAN_TABLE が存在するまで it++ でリトライ
- PortChannel: STATE_LAG_TABLE が存在するまで it++ でリトライ
- Loopback: スキップして即時処理

## intfsorch 側の ordering
intfsorch.cpp:965: setIntf() 成功後に nat_zone 設定
- setIntf() 失敗時は it++ でリトライ（RIF 作成が先決）

## ordering 依存サマリ
- STATE_PORT_TABLE / STATE_VLAN_TABLE / STATE_LAG_TABLE: natmgrd がポート ready を確認
- Port オブジェクト in PortsOrch: intfsorch の setIntf() 前提
- NAT_GLOBAL.admin_mode=enabled: dynamic NAT rule 設定時のみ（mangle MARK には不要）
