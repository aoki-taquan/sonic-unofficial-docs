# PORTCHANNEL_MEMBER — Phase F 副次 DB 書込 分析

生成日: 2026-05-16
ソース:
- `sonic-swss/cfgmgr/teammgr.cpp`
- `sonic-swss/teamsyncd/teamsync.cpp`
- `sonic-swss/orchagent/portsorch.cpp`

---

## teammgrd (cfgmgr/teammgr.cpp)

teammgrd は CONFIG_DB の `PORTCHANNEL_MEMBER` テーブルを購読し、teamd へのメンバ操作と APPL_DB への書き込みを行う。

### SET (PORTCHANNEL_MEMBER|<lag>|<member>) — addLagMember()

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `m_appPortTable.set(member, {mtu})` | APPL_DB / `PORT_TABLE` | `<member>` field=`mtu` | 常時: メンバポートが LAG の MTU を継承 (`teammgr.cpp:830`) |
| `ip link set dev <member> down` | カーネル netdev | `<member>` admin-down | enslave 前に teamd 要件として admin down に変更 (`teammgr.cpp:761`) |
| `teamdctl <lag> port config update <member> ...` | teamd (UNIX ソケット) | `<member>` lacp_key / link_watch | LACP キーと link_watch 設定を teamd に送付 (`teammgr.cpp:762-768`) |
| `teamdctl <lag> port add <member>` | teamd (UNIX ソケット) | `<member>` | teamd にポートを LAG メンバとして登録 (`teammgr.cpp:769`) |
| `ip link set dev <member> [up\|down]` | カーネル netdev | `<member>` admin_status | CONFIG_DB `PORT.admin_status` に従い復元 (`teammgr.cpp:828`) |

### DEL (PORTCHANNEL_MEMBER|<lag>|<member>) — removeLagMember()

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `teamdctl <lag> port remove <member>` | teamd (UNIX ソケット) | `<member>` | teamd からポートを削除 (`teammgr.cpp:836`) |
| `ip link set dev <member> mtu <mtu>` | カーネル netdev | `<member>` MTU | CONFIG_DB `PORT.mtu` に従い元 MTU に復元 (`teammgr.cpp:858`) |
| `ip link set dev <member> [up\|down]` | カーネル netdev | `<member>` admin_status | CONFIG_DB `PORT.admin_status` に従い復元 (`teammgr.cpp:860`) |
| `m_appPortTable.set(member, {mtu})` | APPL_DB / `PORT_TABLE` | `<member>` field=`mtu` | メンバ削除後に元の MTU を APPL_DB に書き戻し (`teammgr.cpp:862`) |

**注意**: teamd からの `port remove` 後、teamsyncd が `RTM_DELLINK` ではなく `TEAM_PORT_CHANGE` イベントを受けて `LAG_MEMBER_TABLE` から該当エントリを削除する。

---

## teamsyncd (teamsyncd/teamsync.cpp)

teamsyncd は teamd からの TEAM_PORT_CHANGE / TEAM_OPTION_CHANGE イベントを監視し、APPL_DB `LAG_MEMBER_TABLE` を更新する。PORTCHANNEL_MEMBER の SET/DEL に対する間接的な副次書き込みを担う。

### LAG メンバ状態変化 (TeamPortSync — TEAM_PORT_CHANGE)

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `m_lagMemberTable->set(<lag>:<member>, {status})` | APPL_DB / `LAG_MEMBER_TABLE` | `<lag>:<member>` field=`status` (`enabled`/`disabled`) | メンバ追加またはステータス変化時 (`teamsync.cpp:420`) |
| `m_lagMemberTable->del(<lag>:<member>)` | APPL_DB / `LAG_MEMBER_TABLE` | `<lag>:<member>` | teamd からメンバが削除されたとき (`teamsync.cpp:432`) |

---

## LagOrch / PortsOrch (orchagent/portsorch.cpp)

LagOrch は APPL_DB の `LAG_MEMBER_TABLE` を購読し、SAI 呼び出し後に ASIC_DB と CHASSIS_APP_DB へ書き込む。

### LAG メンバ追加 (addLagMember())

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `sai_lag_api->create_lag_member(...)` → ASIC_DB | ASIC_DB / `ASIC_STATE:SAI_OBJECT_TYPE_LAG_MEMBER` | SAI OID (lag_member_id) | 常時 (`portsorch.cpp:8172`) |
| `sai_lag_api->set_lag_member_attribute(SAI_LAG_MEMBER_ATTR_EGRESS_DISABLE)` | ASIC_DB | lag_member_id | LACP ネゴ未完 (`status=disabled`) かつ SYSTEM 型以外 (`portsorch.cpp:8162-8167`) |
| `sai_lag_api->set_lag_member_attribute(SAI_LAG_MEMBER_ATTR_INGRESS_DISABLE)` | ASIC_DB | lag_member_id | 同上 |
| `setPortPvid(port, pvid)` → SAI → ASIC_DB | ASIC_DB / LAG PVID | port.m_port_id | LAG に PVID が設定されている場合 (`portsorch.cpp:8143-8145`) |
| `setHostIntfsStripTag(port, SAI_HOSTIF_VLAN_TAG_KEEP)` | ASIC_DB / hostif | port hostif | LAG が bridge_port または child_ports を持つ場合 (`portsorch.cpp:8198`) |
| `m_tableVoqSystemLagMemberTable->set(key, {status})` | CHASSIS_APP_DB / `SYSTEM_LAG_MEMBER_TABLE` | `<system_lag>:<system_port>` | VoQ マルチ ASIC かつ Local LAG の場合のみ (`portsorch.cpp:8213, voqSyncAddLagMember:11179`) |

### LAG メンバ削除 (removeLagMember())

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `sai_lag_api->remove_lag_member(lag_member_id)` → ASIC_DB | ASIC_DB / `ASIC_STATE:SAI_OBJECT_TYPE_LAG_MEMBER` | lag_member_id | 常時 (`portsorch.cpp:8221`) |
| `setHostIntfsStripTag(port, SAI_HOSTIF_VLAN_TAG_STRIP)` | ASIC_DB / hostif | port hostif | LAG が bridge_port または child_ports を持つ場合 (`portsorch.cpp:8244`) |
| `m_tableVoqSystemLagMemberTable->del(key)` | CHASSIS_APP_DB / `SYSTEM_LAG_MEMBER_TABLE` | `<system_lag>:<system_port>` | VoQ マルチ ASIC かつ Local LAG の場合のみ (`portsorch.cpp:8261, voqSyncDelLagMember:11195`) |

---

## 副次書き込みサマリ

| DB | 副次書き込みテーブル | SET 時 | DEL 時 | 担当 |
|----|---------------------|--------|--------|------|
| APPL_DB | `PORT_TABLE` | SET field=`mtu` (LAG 継承) | SET field=`mtu` (元値に復元) | teammgrd |
| APPL_DB | `LAG_MEMBER_TABLE` | SET field=`status` (`enabled`/`disabled`) | DEL | teamsyncd |
| ASIC_DB | `SAI_OBJECT_TYPE_LAG_MEMBER` | `create_lag_member` (SAI OID 生成) | `remove_lag_member` (SAI OID 削除) | portsorch (syncd 経由) |
| CHASSIS_APP_DB | `SYSTEM_LAG_MEMBER_TABLE` | SET {status} (VoQ Local LAG のみ) | DEL (VoQ Local LAG のみ) | portsorch |
| カーネル | netdev (`ip link`) | admin-down → enslave → admin復元 | admin/MTU を元値に復元 | teammgrd |
| teamd | UNIX ソケット (`teamdctl`) | `port config update` + `port add` | `port remove` | teammgrd |

### LACP ネゴシエーションと ASIC_DB 更新タイミング

メンバ追加直後は `LAG_MEMBER_TABLE.status = disabled` で ASIC_DB に `SAI_LAG_MEMBER_ATTR_EGRESS_DISABLE=true` / `SAI_LAG_MEMBER_ATTR_INGRESS_DISABLE=true` が設定される。
LACP ネゴシエーション完了後、teamd が `TEAM_PORT_CHANGE` で `status=enabled` を通知 → teamsyncd が `LAG_MEMBER_TABLE` を更新 → portsorch が SAI attribute を解除する。
この遷移は `portsorch.cpp:8295-8340` (`enableLagMember` / `disableLagMember`) が担う。

### STATE_DB LAG_MEMBER_TABLE

STATE_DB に `LAG_MEMBER_TABLE` は書き込まれない。LAG メンバの状態は APPL_DB `LAG_MEMBER_TABLE.status` フィールドで管理される。
teamsyncd は STATE_DB には LAG 本体 (`LAG_TABLE`) のみ書き込む (`teamsync.cpp:160-203`)。
