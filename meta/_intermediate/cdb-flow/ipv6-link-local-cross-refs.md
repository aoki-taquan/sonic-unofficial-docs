# ipv6-link-local cross-refs (Phase C)

Phase C 調査メモ。`ipv6_use_link_local_only` フィールドを参照する他テーブル/モジュール/CLI/YANG の横断マッピング。

## 横断マッピング

| 種別 | 名前 | 参照位置 (HEAD) | 役割 |
|------|------|----------------|------|
| CONFIG_DB テーブル | `INTERFACE` (属性ロウ) | `cfgmgr/intfmgr.cpp:817-820` | フィールドの一次格納先 (Ethernet) |
| CONFIG_DB テーブル | `PORTCHANNEL_INTERFACE` | 同上 (共通パーサ) | PortChannel 用属性ロウ |
| CONFIG_DB テーブル | `VLAN_INTERFACE` | 同上 (共通パーサ) | VLAN 用属性ロウ |
| CONFIG_DB テーブル | `PORT` / `PORTCHANNEL` / `VLAN` | `show/main.py:1611-1623` | `show ipv6 link-local-mode` でポート空間の網羅に使用 |
| STATE_DB テーブル | `PORT_TABLE` / `LAG_TABLE` / `VLAN_TABLE` | `intfmgr.cpp` (`isIntfStateOk`) | 書込み順依存の gating (Phase B 既出) |
| STATE_DB テーブル | `VRF_TABLE` | `intfmgr.cpp:839-843` | VRF バインド時の gating (Phase B 既出) |
| APP_DB テーブル | `INTF_TABLE` | `intfmgr.cpp:926` (`fvTuple`) | `intfmgr` が `"enable"` 時に転送するが orchagent では dead consumer |
| APP_DB テーブル | `NEIGH_TABLE` | `neighsyncd/neighsync.cpp:227` | link-local neigh の登録/抑止判断にフィールドを参照 |
| swss daemon | `intfmgrd` | `cfgmgr/intfmgr.cpp` | CONFIG_DB → APP_DB 転送 |
| swss daemon | `neighsyncd` | `neighsyncd/neighsync.cpp:193-239` | CONFIG_DB 直接参照 (APP_DB 経由ではない) |
| swss daemon | `orchagent` IntfsOrch | `orchagent/intfsorch.cpp` | APP_DB の本フィールドは受信するが SAI 転送しない (dead consumer) |
| CLI (config) | `config interface ipv6 enable/disable use-link-local-only` | `config/main.py:L9462-L9484` (`set_ipv6_link_local_only_on_interface`) | 個別 IF の属性ロウ書込み |
| CLI (config) | `config ipv6 enable/disable link-local` | `config/main.py` (`enable_ipv6_link_local_all` 系) | 全 IF 一括 (VLAN/PortChannel member は除外) |
| CLI (show) | `show ipv6 link-local-mode` | `show/main.py:1620-1623` | 表示は PORT / PORTCHANNEL / VLAN 空間と INTERFACE 属性ロウの join |
| YANG | `sonic-interface` (`/sonic-interface:sonic-interface/INTERFACE/INTERFACE_LIST/ipv6_use_link_local_only`) | `sonic-interface.yang:95-99` | YANG default `disable` |
| YANG | `sonic-portchannel-interface` | 同様の leaf | PortChannel 属性 |
| YANG | `sonic-vlan-interface` | 同様の leaf | VLAN 属性 |
| YANG 型 | `sonic-types:mode-status` | `sonic-types.yang` | `enum enable | enum disable` |

## 整合性メモ

- INTERFACE / PORTCHANNEL_INTERFACE / VLAN_INTERFACE は三者で同一名のフィールドを共有するが、CLI レイヤ (`set_ipv6_link_local_only_on_interface`) はテーブルを `get_interface_table_name(interface_name)` で判別して書き分ける。フィールド名は完全に同一
- `INTF_TABLE` (APP_DB) は dead consumer であり、依存リファレンスは neighsyncd の CONFIG_DB 直接参照に集約される。Phase B の `neighsyncd の CONFIG_DB 直接参照 (依存 #3)` と整合
- `show ipv6 link-local-mode` は `PORT`/`PORTCHANNEL`/`VLAN` を母集合とするため、`INTERFACE` 属性ロウが存在しないポートは `Disabled` 表示になる。属性ロウの欠如はランタイム的に `disable` と等価
