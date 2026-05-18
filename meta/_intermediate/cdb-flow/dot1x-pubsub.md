# dot1x — Phase G 通信メカニズム調査ノート

## 対象テーブル
- `PAC_PORT_CONFIG_TABLE`
- `HOSTAPD_GLOBAL_CONFIG_TABLE`

## 購読 API の確認

### pacmgrd 側
- ソース: `sonic-buildimage/src/sonic-pac/pacmgr/pacmgr.h:137-147`
- `m_confPacTbl`          → `SubscriberStateTable(configDb, CFG_PAC_PORT_CONFIG_TABLE)`
- `m_confPacGblTbl`       → `SubscriberStateTable(configDb, CFG_PAC_GLOBAL_CONFIG_TABLE)` (PAC グローバル設定)
- `m_confPacHostapdGblTbl`→ `SubscriberStateTable(configDb, CFG_PAC_HOSTAPD_GLOBAL_CONFIG_TABLE)`
- `m_confVlanTbl`         → `SubscriberStateTable(configDb, CFG_VLAN_TABLE_NAME)`
- `m_confVlanMemTbl`      → `SubscriberStateTable(configDb, CFG_VLAN_MEMBER_TABLE_NAME)`
- `m_vlanTbl`             → `SubscriberStateTable(stateDb, STATE_VLAN_TABLE_NAME)`
- `m_vlanMemTbl`          → `SubscriberStateTable(stateDb, STATE_VLAN_MEMBER_TABLE_NAME)`

すべて **`SubscriberStateTable`** (keyspace PSUBSCRIBE ベース)。`ConsumerStateTable` は使用していない。

### hostapdmgrd 側
- ソース: `sonic-buildimage/src/sonic-pac/hostapdmgr/hostapdmgr.h:81-84`
- `m_confHostapdPortTbl`    → `SubscriberStateTable(configDb, CFG_PAC_PORT_CONFIG_TABLE)`
- `m_confHostapdGlobalTbl`  → `SubscriberStateTable(configDb, CFG_PAC_HOSTAPD_GLOBAL_CONFIG_TABLE)`
- `m_confRadiusServerTable` → `SubscriberStateTable(configDb, "RADIUS_SERVER")`
- `m_confRadiusGlobalTable` → `SubscriberStateTable(configDb, "RADIUS")`

## イベントループ

### pacmgrd
`pacmgr_main.cpp:65`: `s.addSelectables(pacmgr.getSelectables())` で全 SubscriberStateTable を swss::Select に登録。
イベント発生時に `processDbEvent(tbl)` が呼ばれ、テーブル種別でディスパッチ。

### hostapdmgrd
同様に `getSelectables()` で Select に登録し `processDbEvent(tbl)` でディスパッチ。
`hostapdmgr.cpp:69-100`

## PSUBSCRIBE パターン
`SubscriberStateTable` は `__keyspace@<dbId>__:<table>|*` パターンで keyspace 通知を受信する (swss-common 実装)。
通知ペイロードは操作名 (hset/del)。フィールド値は HGETALL で別途取得。

## ポーリング間隔
swss::Select のデフォルトタイムアウトを使用 (通常 1000ms)。
pacmgrd は pac ソケットからの非同期メッセージも同一 Select で多重化する (`pacqueue`)。

## Evidence
- `sonic-buildimage/src/sonic-pac/pacmgr/pacmgr.h:137-147`
- `sonic-buildimage/src/sonic-pac/pacmgr/pacmgr.cpp:80-133`
- `sonic-buildimage/src/sonic-pac/pacmgr/pacmgr_main.cpp:65`
- `sonic-buildimage/src/sonic-pac/hostapdmgr/hostapdmgr.h:81-84`
- `sonic-buildimage/src/sonic-pac/hostapdmgr/hostapdmgr.cpp:69-100`
