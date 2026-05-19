# STATE_DB PORT_TABLE — Phase F 副次 DB 書込み調査

調査日: 2026-05-19
ソース: sonic-swss/cfgmgr/intfmgr.cpp, sonic-swss/cfgmgr/teammgr.cpp, sonic-swss/cfgmgr/buffermgrdyn.cpp, sonic-swss/cfgmgr/macsecmgr.cpp, sonic-swss/cfgmgr/natmgr.cpp

## 概要

`STATE_DB PORT_TABLE|EthernetN` への SET/DEL は、購読プロセスが次の doTask() イテレーションで検出し、条件を満たした場合に下流 DB への書き込みをトリガーする。書き込み瞬間に同期的な副次書き込みは発生しない（Redis Pub/Sub 通知による非同期）。

## intfmgr (cfgmgr/intfmgr.cpp)

intfmgr は `SubscriberStateTable` で `STATE_PORT_TABLE_NAME` を購読し、SET 受信時に `doPortTableTask()` を呼ぶ (intfmgr.cpp:1183-1186, 1244)。

### admin_status フィールド変化 → APPL_DB INTF_TABLE サブインタフェース更新

`doPortTableTask()` の `admin_status` フィールド受信パスで `updateSubIntfAdminStatus()` が呼ばれ、
親ポート `EthernetN` に紐づくサブインタフェース `EthernetN.VID` の admin_status を
`m_appIntfTableProducer.set(intf, fvVector)` で `APPL_DB INTF_TABLE|EthernetN.VID` に書き込む (intfmgr.cpp:464-485)。

条件: サブインタフェースが `m_subIntfList` に登録済みであること。サブインタフェース未設定時は副次書き込みなし。

### mtu フィールド変化 → APPL_DB INTF_TABLE サブインタフェース更新

同様に `mtu` フィールド変化で `updateSubIntfMtu()` が呼ばれ、サブインタフェース MTU を
`ip link set ... mtu` でカーネルに設定後、`m_appIntfTableProducer.set(intf, fvVector)` で
`APPL_DB INTF_TABLE|EthernetN.VID` に書き込む (intfmgr.cpp:407-428)。

サブインタフェースに `mtu` が明示設定されていない場合 (`MTU_INHERITANCE`)、`DEFAULT_MTU_STR` (9100) を使用する。

### state フィールド存在 → IP インタフェース処理ゲート解除

`isIntfStateOk()` が `m_statePortTable.get(alias, temp)` && `state == "ok"` を確認し、
成功すると `m_appIntfTableProducer.set(alias, data)` で `APPL_DB INTF_TABLE|EthernetN:PREFIX` を書き込む (intfmgr.cpp:686-695, 1053)。
これは CONFIG_DB `INTERFACE` テーブルのキャッシュ再生処理として発動する。

## teammgr (cfgmgr/teammgr.cpp)

teammgr は `SubscriberStateTable` で `STATE_PORT_TABLE_NAME` を購読し、SET 受信時に
`doPortUpdateTask()` → `addLagMember()` を呼ぶ (teammgr.cpp:165-168, 442-481)。

### state SET → LAG メンバー追加 (OS + チームd)

`findPortMaster(lag, alias)` が true（当該ポートが CONFIG_DB `PORTCHANNEL_MEMBER` に登録済み）の場合、
`teamdctl <lag> port add <member>` + `ip link set dev <member> down` を実行して
LAG にメンバーを追加する。この操作は OS レベルの操作のため STATE_DB / APPL_DB への直接書き込みはないが、
`addLagMember()` 成功後に `m_appLagTable.set(alias, fvs)` で `APPL_DB LAG_TABLE|PortChannelN` を
更新するケースがある (teammgr.cpp:515, 545, 559)。

MACsec が有効なポートの場合、`isMACsecIngressSAOk()` が false だと LAG メンバー追加がスキップされ、
STATE_DB PORT_TABLE の次の更新イベントまでリトライされる (teammgr.cpp:461-466)。

## buffermgrdyn (cfgmgr/buffermgrdyn.cpp)

buffermgrdyn は `SubscriberStateTable` で `STATE_PORT_TABLE_NAME` を購読し、
`handlePortStateTable()` で `supported_speeds` フィールドの変化を検出する (buffermgrdyn.cpp:451, 2224-2253)。

### supported_speeds 変化 → バッファプロファイル再計算

`portInfo.supported_speeds` が更新され、かつ `portInfo.auto_neg == true` かつ
`needRefreshPortDueToEffectiveSpeed()` が true の場合、`refreshPgsForPort()` を呼び出して
`APPL_DB BUFFER_PG_TABLE` および `APPL_DB BUFFER_PROFILE_TABLE` を更新する (buffermgrdyn.cpp:2240-2246)。

副次書き込みが発生する条件:
1. `STATE_DB PORT_TABLE|EthernetN.supported_speeds` フィールドが変化
2. CONFIG_DB `PORT.autoneg = true` 設定済み
3. ケーブル長 (`cable_length`) が 0 でない
4. ポートの `state != PORT_ADMIN_DOWN`

## macsecmgr / natmgr (gate のみ)

`macsecmgr` および `natmgr` は STATE_DB PORT_TABLE を **ゲート条件** として参照するのみで、
直接的な副次 DB 書き込みは発生しない。

- `macsecmgr`: `isPortStateOk()` が `state == "ok"` && `netdev_oper_status == "up"` を確認してから
  MACsec セッション設定を開始する (macsecmgr.cpp:622-633)。書き込み先は `STATE_DB MACSEC_PORT_TABLE` 等だが、
  これは MACsec 設定の結果であり PORT_TABLE SET の直接副次書き込みではない。
- `natmgr`: `isPortStateOk()` で `m_statePortTable.get(port, temp)` を確認してから NAT バインド処理を進める (natmgr.cpp:120-126)。

## 副次書き込みなし（直接）

- **ASIC_DB**: STATE_DB PORT_TABLE への書き込みは ASIC_DB に直接波及しない。ASIC_DB への書き込みは PortsOrch が SAI 経由で行うもので経路が独立している。
- **COUNTERS_DB / FLEX_COUNTER_DB**: PORT_TABLE の SET/DEL は FLEX_COUNTER_DB の counter グループ設定を変更しない。カウンタ有効化は PortsOrch が orchagent 初期化フローで別途行う。
- **STATE_DB（自テーブル以外）**: portsyncd / PortsOrch はいずれも PORT_TABLE 書き込みの直接副次として他の STATE_DB テーブルへの書き込みを行わない。

## まとめ表

| トリガー操作 | 副次書込先 | 書込プロセス | 書込条件 |
|---|---|---|---|
| `PORT_TABLE\|EthernetN` SET (admin_status=up/down) | `APPL_DB INTF_TABLE\|EthernetN.VID` admin_status | `intfmgrd` | `m_subIntfList` にサブインタフェースが登録済み (intfmgr.cpp:464-484) |
| `PORT_TABLE\|EthernetN` SET (mtu=NNNN) | `APPL_DB INTF_TABLE\|EthernetN.VID` mtu | `intfmgrd` | `m_subIntfList` にサブインタフェースが登録済み (intfmgr.cpp:407-428) |
| `PORT_TABLE\|EthernetN` SET (state=ok) | `APPL_DB INTF_TABLE\|EthernetN:PREFIX` SET | `intfmgrd` | CONFIG_DB INTERFACE にエントリが存在し `isIntfStateOk()` が通過 (intfmgr.cpp:686-695) |
| `PORT_TABLE\|EthernetN` SET | `APPL_DB LAG_TABLE\|PortChannelN` SET | `teammgrd` | CONFIG_DB PORTCHANNEL_MEMBER に登録済み かつ MACsec 条件通過 (teammgr.cpp:442-481, 732+) |
| `PORT_TABLE\|EthernetN` SET (supported_speeds 変化) | `APPL_DB BUFFER_PG_TABLE` + `BUFFER_PROFILE_TABLE` | `buffermgrdyn` | autoneg=true かつ cable_length 設定済み かつ admin UP (buffermgrdyn.cpp:2240-2246) |
