# PORTCHANNEL SET/DEL 副次 DB 書込 分析 (Phase F)

生成日: 2026-05-15
ソース:
- `sonic-swss/cfgmgr/teammgr.cpp`
- `sonic-swss/teamsyncd/teamsync.cpp`
- `sonic-swss/orchagent/portsorch.cpp`

---

## teammgrd (cfgmgr/teammgr.cpp)

teammgrd は CONFIG_DB の `PORTCHANNEL` テーブルを購読し、teamd プロセス管理と APPL_DB への書き込みを行う。

### SET (PORTCHANNEL|<name>) — addLag() → doLagTask()

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `m_appLagTable.set(alias, {mtu})` | APPL_DB / `LAG_TABLE` | `<name>` field=`mtu` | `setLagMtu()` 呼出し時 (常時: 省略時デフォルト "9100") |
| `m_appPortTable.set(member, {mtu})` | APPL_DB / `PORT_TABLE` | `<member>` field=`mtu` | LAG の全メンバポートに MTU を伝播 (`setLagMtu()` 内) |
| `m_appLagTable.set(alias, {tpid})` | APPL_DB / `LAG_TABLE` | `<name>` field=`tpid` | `tpid` フィールドが存在する場合 (`setLagTpid()` 呼出し時) |
| `m_appLagTable.set(alias, {learn_mode})` | APPL_DB / `LAG_TABLE` | `<name>` field=`learn_mode` | `learn_mode` フィールドが存在する場合 (`setLagLearnMode()` 呼出し時) |

カーネル変更 (副次 DB 書込ではなくカーネル操作):
- `ip link set dev <name> up/down` — admin_status を Linux netdev に反映 (`setLagAdminStatus()`)
- `ip link set dev <name> mtu <value>` — MTU を Linux netdev に反映 (`setLagMtu()`)
- `teamd` プロセス起動 (exec) — LAG 新規作成時 (`addLag()`)

### DEL (PORTCHANNEL|<name>) — removeLag()

| 操作 | 対象 DB / テーブル | キー | 条件 |
|------|------------------|------|------|
| (APPL_DB への明示的 del なし) | — | — | removeLag() は teamd プロセスに SIGTERM を送るのみ |

注意: APPL_DB の `LAG_TABLE` エントリ削除は teamsyncd が担当 (RTM_DELLINK を受信して `m_lagTable.del(lagName)` を実行)。

---

## teamsyncd (teamsyncd/teamsync.cpp)

teamsyncd は Linux netlink イベント (RTM_NEWLINK / RTM_DELLINK) を受けて APPL_DB / STATE_DB に書き込む。CONFIG_DB を直接購読しないが、teamd 起動後の間接的な副次書き込みを担う。

### LAG 追加 (RTM_NEWLINK — addLag())

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `m_lagTable.set(lagName, {admin_status, oper_status, mtu})` | APPL_DB / `LAG_TABLE` | `<name>` | 常時 (RTM_NEWLINK 受信時) |
| `m_stateLagTable.set(lagName, {admin_status, oper_status, mtu, state:"ok"})` | STATE_DB / `LAG_TABLE` | `<name>` | 非 warm-reboot 時。team_init() 成功後のみ書き込む |
| (warm-reboot 時) `m_stateLagTablePreserved[lagName] = fvVector` → 後で `m_stateLagTable.set()` | STATE_DB / `LAG_TABLE` | `<name>` | warm-reboot 時: apply_temp_view() 後に書き込み |

### LAG 削除 (RTM_DELLINK — removeLag())

| 操作 | 対象 DB / テーブル | キー | 条件 |
|------|------------------|------|------|
| `m_lagMemberTable.del(lagName + ":" + member)` | APPL_DB / `LAG_MEMBER_TABLE` | `<name>:<member>` | 残存する全メンバを先に削除 |
| `m_lagTable.del(lagName)` | APPL_DB / `LAG_TABLE` | `<name>` | 常時 |
| `m_stateLagTable.del(lagName)` | STATE_DB / `LAG_TABLE` | `<name>` | 非 warm-reboot 時 |

### LAG メンバ状態変化 (TeamPortSync — TEAM_PORT_CHANGE / TEAM_OPTION_CHANGE)

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `m_lagMemberTable->set(lagName:member, {status})` | APPL_DB / `LAG_MEMBER_TABLE` | `<name>:<member>` | メンバ追加またはステータス変化時 |
| `m_lagMemberTable->del(lagName:member)` | APPL_DB / `LAG_MEMBER_TABLE` | `<name>:<member>` | メンバ削除時 |

---

## LagOrch / PortsOrch (orchagent/portsorch.cpp)

LagOrch は APPL_DB の `LAG_TABLE` を購読し、SAI 呼び出し後に COUNTERS_DB へ書き込む。

### LAG 作成 (addLag())

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `m_counterLagTable->set("", {<alias>=<oid>})` | COUNTERS_DB / `COUNTERS_LAG_NAME_MAP` | `""` field=`<alias>` | LAG 作成時 (常時) |
| `m_tableVoqSystemLagTable->set(key, {lag_id, switch_id})` | CHASSIS_APP_DB / `SYSTEM_LAG_TABLE` | `<system_lag_alias>` | VoQ マルチ ASIC 環境かつ Local LAG の場合のみ (`voqSyncAddLag()`) |

SAI 呼び出し (ASIC_DB へ反映):
- `sai_lag_api->create_lag(...)` — ASIC_DB に LAG OID エントリ生成
- `sai_lag_api->set_lag_attribute(SAI_LAG_ATTR_PORT_VLAN_ID)` — PVID 設定
- `sai_lag_api->set_lag_attribute(SAI_LAG_ATTR_TPID)` — TPID 設定

### LAG 削除 (removeLag())

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `m_counterLagTable->hdel("", alias)` | COUNTERS_DB / `COUNTERS_LAG_NAME_MAP` | `""` field=`<alias>` 削除 | 常時 |
| `m_tableVoqSystemLagTable->del(key)` | CHASSIS_APP_DB / `SYSTEM_LAG_TABLE` | `<system_lag_alias>` | VoQ かつ Local LAG の場合のみ (`voqSyncDelLag()`) |

SAI 呼び出し (ASIC_DB から削除):
- `sai_lag_api->remove_lag(lag_id)` — ASIC_DB の LAG OID エントリ削除

---

## 副次書き込みサマリ

| DB | 副次書き込みテーブル | SET 時 | DEL 時 |
|----|---------------------|--------|--------|
| APPL_DB | `LAG_TABLE` | SET (teammgrd → mtu/tpid/learn_mode; teamsyncd → admin_status/oper_status/mtu) | DEL (teamsyncd, RTM_DELLINK 受信時) |
| APPL_DB | `PORT_TABLE` | SET field=`mtu` (teammgrd, 全 LAG メンバポートへの MTU 伝播) | — |
| APPL_DB | `LAG_MEMBER_TABLE` | SET field=`status` (teamsyncd, メンバ状態変化時) | DEL (teamsyncd, メンバ削除 / LAG 削除時) |
| STATE_DB | `LAG_TABLE` | SET {admin_status, oper_status, mtu, state:"ok"} (teamsyncd, team_init() 成功後) | DEL (teamsyncd, RTM_DELLINK 受信時) |
| COUNTERS_DB | `COUNTERS_LAG_NAME_MAP` | SET field=`<alias>=<oid>` (portsorch, LAG 作成時) | DEL field=`<alias>` (portsorch, LAG 削除時) |
| CHASSIS_APP_DB | `SYSTEM_LAG_TABLE` | SET {lag_id, switch_id} (portsorch, VoQ Local LAG のみ) | DEL (portsorch, VoQ Local LAG のみ) |
| ASIC_DB | LAG OID エントリ (syncd 経由) | create_lag (SAI) | remove_lag (SAI) |

### 重要: teamd 起動タイミングと STATE_DB 書き込みの依存関係

STATE_DB `LAG_TABLE` への `state: ok` 書き込みは `team_init()` 成功後のみ発生する。
これは依存サービス (intfmgrd 等) が未完了 LAG に対して動作しないよう意図的に遅延されている
(`teamsync.cpp:191-203` のコメント参照)。

### warm-reboot 挙動

warm-reboot 中は STATE_DB 書き込みが `m_stateLagTablePreserved` にバッファされ、
`apply_temp_view()` 完了後にまとめて STATE_DB に反映される。
APPL_DB の `LAG_TABLE` は temp_view 経由で更新される (`teamsync.cpp:41, 88`)。
