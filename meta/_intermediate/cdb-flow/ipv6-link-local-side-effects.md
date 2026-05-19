# IPv6 Link-local モード — Phase F 副次 DB 書込スキャンノート

調査日: 2026-05-19
対象テーブル: INTERFACE / PORTCHANNEL_INTERFACE / VLAN_INTERFACE の ipv6_use_link_local_only フィールド
ソース: sonic-net/sonic-swss cfgmgr/intfmgr.cpp

## 書込チェーン概要

CONFIG_DB.INTERFACE|<intf>|ipv6_use_link_local_only → intfmgrd が以下を実行:
1. APP_DB.INTF_TABLE に ipv6_use_link_local_only フィールドを書込（enable / disable）
2. STATE_DB.INTERFACE_TABLE に vrf フィールドを書込（インタフェース設定全体の一部）
3. disable 時: `ip neigh del` コマンドでカーネルの link-local ネイバーを削除（DB 書込なし）

## 詳細

### APP_DB.INTF_TABLE への書込

intfmgr.cpp の doIntfGeneralTask() 処理（L813-929）:
- ipv6_use_link_local_only フィールドを FieldValueTuple に追加
- `m_appIntfTableProducer.set(alias, data)` で APP_DB.INTF_TABLE に書込（L1053）
- キー: `INTF_TABLE|<interface_name>` (例: `INTF_TABLE|Ethernet0`)
- フィールド: `ipv6_use_link_local_only` = `"enable"` または `"disable"`

### STATE_DB.INTERFACE_TABLE への書込

intfmgr.cpp L1054:
- `m_stateIntfTable.hset(alias, "vrf", vrf_name)` で STATE_DB.INTERFACE_TABLE に書込
- これはインタフェース設定全体の処理の一部であり、ipv6_use_link_local_only に限定されない

### カーネル操作（DB 書込なし）

delIpv6LinkLocalNeigh() (L712-738):
- disable 時に NEIGH_TABLE から link-local (FE80::) スコープのネイバーを読み取り
- `ip neigh del dev <intf> <ipv6_addr>` コマンドでカーネルの近隣テーブルから削除
- DB への書込は行わない（カーネルコマンドのみ）

## ASIC_DB への波及

APP_DB.INTF_TABLE の ipv6_use_link_local_only フィールドは orchagent IntfsOrch が購読するが、
このフィールドは SAI に転送しない（dead consumer）。ASIC_DB への書込は発生しない。
ただし隣接テーブル (NEIGH_TABLE / ASIC_DB SAI_OBJECT_TYPE_NEIGHBOR_ENTRY) はカーネルの近隣テーブル変化経由で
neighsyncd → neighorch が処理する可能性はある。
