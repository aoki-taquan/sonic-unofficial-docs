# APPL_DB MCLAG/ICCP — 暗黙参照 (Phase C) 中間調査

対象ページ: `docs/reference/config-db/appl-mclag.md`
ソース: `sonic-swss/mclagsyncd/` (ref `4305596156d70e9797e8a881b3d19b46de0bce0d`)

`mclagsyncd` が APPL_DB に書き込む 7 テーブル (`MCLAG_FDB_TABLE` / `ISOLATION_GROUP_TABLE` /
`ACL_TABLE_TABLE` / `ACL_RULE_TABLE` / `LAG_TABLE` / `PORT_TABLE` / `INTF_TABLE`) は
key / フィールド値として CONFIG_DB / APPL_DB の他テーブルのオブジェクト名を文字列で
保持する。YANG での leafref 制約は無く、参照は `mclagsyncd` または下流 orchagent
(`fdborch` / `isolationGroupOrch` / `aclOrch` / `lagOrch` / `portOrch` / `intfOrch`)
のコード上でのみ表現される。

## 参照一覧

| 参照元 (テーブル.フィールド/key 構造) | 参照先テーブル | 参照先キー形式 | 解決主体 | 参照箇所 |
|---|---|---|---|---|
| `MCLAG_FDB_TABLE` key `Vlan<vid>:<mac>` | CONFIG_DB `VLAN` | `VLAN\|Vlan<vid>` | iccpd / `fdborch` | `mclaglink.cpp:494` |
| `MCLAG_FDB_TABLE.port` | CONFIG_DB `PORTCHANNEL` / `PORT` | `PORTCHANNEL\|<name>` / `PORT\|<name>` | `fdborch` | `mclaglink.cpp:465-521` |
| `ISOLATION_GROUP_TABLE.PORTS` | CONFIG_DB `PORT` | `PORT\|Ethernet<N>` | iccpd / `isolationGroupOrch` | `mclaglink.cpp:237,274` |
| `ISOLATION_GROUP_TABLE.MEMBERS` | CONFIG_DB `PORTCHANNEL` | `PORTCHANNEL\|PortChannel<N>` | `isolationGroupOrch` | `mclaglink.cpp:258,272` (Ethernet を除外) |
| `ACL_TABLE_TABLE.mclag.ports` | CONFIG_DB `PORT` | `PORT\|Ethernet<N>` | `aclOrch` | `mclaglink.cpp:340 付近` |
| `ACL_RULE_TABLE.mclag:mclag.OUT_PORTS` | CONFIG_DB `PORT` | `PORT\|Ethernet<N>` | `aclOrch` | `mclaglink.cpp:352,367` (PortChannel を除外) |
| `LAG_TABLE` key | CONFIG_DB `PORTCHANNEL` | `PORTCHANNEL\|<name>` | `lagOrch` / `portOrch` | `mclaglink.cpp:407` (prefix `PORTCHANNEL_PREFIX`) |
| `PORT_TABLE` key | CONFIG_DB `PORT` | `PORT\|Ethernet<N>` | `portOrch` | `mclaglink.cpp:416` (else 分岐) |
| `INTF_TABLE` key | CONFIG_DB `INTERFACE` / `VLAN_INTERFACE` / `PORTCHANNEL_INTERFACE` | 同名インタフェース | `intfOrch` | `mclaglink.cpp:435-461` |
| (購読) STATE_DB `FDB_TABLE` | STATE_DB `FDB_TABLE` | `FDB_TABLE\|Vlan<vid>:<mac>` | `mclagsyncd` 自身 | `mclaglink.cpp:912` |
| (購読) STATE_DB `VLAN_MEMBER_TABLE` | STATE_DB `VLAN_MEMBER_TABLE` | `VLAN_MEMBER_TABLE\|Vlan<vid>\|<member>` | `mclagsyncd` 自身 | `mclaglink.cpp:915,1183-1278` |
| (購読) CONFIG_DB `MCLAG` (MCLAG_DOMAIN) | CONFIG_DB `MCLAG` | `MCLAG\|<mlag_id>` | iccpd (経由 IPC) | `mclagsyncd.cpp:41`、`mclaglink.cpp:655-892` |
| (購読) CONFIG_DB `MCLAG_INTERFACE` | CONFIG_DB `MCLAG_INTERFACE` | `MCLAG_INTERFACE\|<mlag_id>\|<if>` | iccpd | `mclaglink.cpp:918` |
| (購読) CONFIG_DB `MCLAG_UNIQUE_IP` | CONFIG_DB `MCLAG_UNIQUE_IP` | `MCLAG_UNIQUE_IP\|<vlan_if>` | iccpd | `mclaglink.cpp:921` |

## 解決タイミング・前提

- `MCLAG_FDB_TABLE` の key 末尾 MAC は iccpd 側で normalize 済み (大文字小文字、コロン区切り 6 オクテット)。VLAN は `Vlan<vid>` 形式。
- `ISOLATION_GROUP_TABLE.PORTS` には MCLAG 設定の物理ポート (`MCLAG_INTERFACE` キーの IF 名) がそのまま流入する。
- `ISOLATION_GROUP_TABLE.MEMBERS` は iccpd から来たカンマ区切りリストから `Ethernet` で
  始まる名を除外した PortChannel のみ (`mclaglink.cpp:258`)。
- `ACL_RULE_TABLE.OUT_PORTS` は対称に `PortChannel` を除外した Ethernet のみ
  (`mclaglink.cpp:352`)。ハードウェアが isolation_group を持たない fallback 経路。
- `LAG_TABLE` / `PORT_TABLE` の分岐は `PORTCHANNEL_PREFIX` (`"PortChannel"`) の
  `strncmp` だけで、VXLAN tunnel ブランチはコメントアウト済み (実装外)。
- `INTF_TABLE` の key 形式は iccpd 通知に従い、PORT / PORTCHANNEL_INTERFACE /
  VLAN_INTERFACE いずれの形でも届きうる。`intfOrch` 側で個別に解決される。

## 間接参照

- `MCLAG_FDB_TABLE` → `fdborch` → SAI FDB エントリ。`fdborch` は `PORT` / `PORTCHANNEL`
  のオブジェクト ID 解決を内部で行うため `mclagsyncd` 側に追加参照は不要。
- `LAG_TABLE.learn_mode` / `PORT_TABLE.learn_mode` は `portOrch` 経由で SAI
  `SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE` にマップされる。
- `INTF_TABLE.mac_addr` は `intfOrch` 経由でカーネル netlink + SAI router interface
  両方に反映される。

## grep 根拠 (最小)

```
mclaglink.cpp:237   fvts.emplace_back("PORTS", isolate_src_port);
mclaglink.cpp:258       if (0 == temp.find("Ethernet")) continue;   // MEMBERS から Ethernet 除外
mclaglink.cpp:352       if (0 == temp.find("PortChannel")) continue; // OUT_PORTS から PortChannel 除外
mclaglink.cpp:407   if (strncmp(learn_port.c_str(), PORTCHANNEL_PREFIX, ...) == 0)
mclaglink.cpp:494   snprintf(key, 64, "%s%d:%s", "Vlan", fdb_info->vid, fdb.mac.c_str());
mclaglink.cpp:912   p_state_fdb_tbl = new SubscriberStateTable(p_state_db.get(), STATE_FDB_TABLE_NAME);
mclaglink.cpp:915   p_state_vlan_mbr_subscriber_table = new SubscriberStateTable(p_state_db.get(), STATE_VLAN_MEMBER_TABLE_NAME);
mclaglink.cpp:921   p_mclag_unique_ip_cfg_tbl = new SubscriberStateTable(p_config_db.get(), CFG_MCLAG_UNIQUE_IP_TABLE_NAME);
```
