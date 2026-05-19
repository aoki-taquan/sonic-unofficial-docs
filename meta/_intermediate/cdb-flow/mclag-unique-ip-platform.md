# mclag-unique-ip — Phase H: プラットフォーム差 調査ノート

## 調査対象

`MCLAG_UNIQUE_IP` の CONFIG_DB 書込みから iccpd/mclagsyncd 処理までのプラットフォーム差を特定する。

## mclagsyncdSendMclagUniqueIpCfg() のプラットフォーム差

`mclagsyncdSendMclagUniqueIpCfg()` (mclaglink.cpp:1088-1181) は
`getenv("platform")` / ASIC 識別コードをまったく含まない。
SET / DEL を `MCLAG_CFG_OPER_ADD` / `MCLAG_CFG_OPER_DEL` に変換し、
`MCLAG_SYNCD_MSG_TYPE_CFG_MCLAG_UNIQUE_IP` メッセージを TCP IPC で iccpd へ送信するだけ。
全プラットフォーム共通経路。

## iccpd 側 (iccp_mclagsyncd_mclag_unique_ip_cfg_handler) のプラットフォーム差

`mlacp_link_handler.c:3186-3293` にプラットフォーム識別コードは存在しない。
処理は以下の 2 種:
1. `sys->unq_ip_if_list` への ADD/DEL (in-memory リスト管理) — 全プラットフォーム共通
2. `local_if_is_l3_mode(lif)` 判定 → `update_vlan_if_mac_on_standby()` / `recover_vlan_if_mac_on_standby()` 呼び出し — 全プラットフォーム共通

`local_if_is_l3_mode()` (port.c:382-397) は
`ipv4_addr != 0 || ipv6_addr != null || master_ifindex != 0` の純粋な
カーネルネットワークスタック状態判定であり、ASIC 依存性なし。

## setIntfMac() のプラットフォーム差

`setIntfMac()` (mclaglink.cpp:435-463) は `getenv("platform")` を持たない。
STANDBY ロールかつ L3 モードの VLAN IF に対して iccpd が送信する
`MCLAG_MSG_TYPE_SET_INTF_MAC` を受けて、`APPL_DB INTF_TABLE|<vlan_if>` の
`mac_addr` を書き換えるだけ。全プラットフォーム共通。

## setPortIsolate() とのプラットフォーム差（間接的影響）

MCLAG_UNIQUE_IP 処理自体は `setPortIsolate()` を呼ばない。
ただし UNIQUE_IP を使用する環境では MCLAG ポート isolation が設定されており、
`setPortIsolate()` (mclaglink.cpp:190-378) が以下のプラットフォーム分岐を持つ点に注意:

- `broadcom` / `barefoot` / `centec` / `clounix` / `marvell-prestera` / `marvell-teralynx`:
  → `APPL_DB ISOLATION_GROUP_TABLE|MCLAG_ISO_GRP` (TYPE=bridge-port) を使用
  → MEMBERS から `Ethernet` 系ポートを除外
- `mellanox` / `vs` / その他未定義:
  → `APPL_DB ACL_TABLE_TABLE|mclag` + `ACL_RULE_TABLE|mclag:mclag` (type=L3, DROP) を使用
  → OUT_PORTS から `PortChannel` 系ポートを除外

この分岐は MCLAG 全体の port isolation 挙動に影響するが、
MCLAG_UNIQUE_IP テーブル処理コード自体には関係しない。

## multi-ASIC / VoQ chassis

`mclagsyncd` の UNIQUE_IP 処理は single-ASIC 前提で実装されており、
VoQ chassis / multi-ASIC 構成での動作保証は明示されていない。
`MclagLink` コンストラクタ (mclaglink.cpp:1795-1823) は単一の
`CONFIG_DB` / `APPL_DB` / `STATE_DB` を参照する設計。

## Sources

- sonic-swss/mclagsyncd/mclaglink.h L54-59 (platform macros)
- sonic-swss/mclagsyncd/mclaglink.cpp L190-378 (setPortIsolate platform分岐)
- sonic-swss/mclagsyncd/mclaglink.cpp L435-463 (setIntfMac)
- sonic-swss/mclagsyncd/mclaglink.cpp L1088-1181 (mclagsyncdSendMclagUniqueIpCfg)
- sonic-buildimage/src/iccpd/src/mlacp_link_handler.c L3186-3293 (iccp_mclagsyncd_mclag_unique_ip_cfg_handler)
- sonic-buildimage/src/iccpd/src/port.c L382-397 (local_if_is_l3_mode)
