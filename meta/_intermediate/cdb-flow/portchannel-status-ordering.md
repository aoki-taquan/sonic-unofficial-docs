# Phase B: APPL_DB LAG_TABLE (portchannel-status) 書込み順依存調査

## 対象ファイル

- `sonic-swss/teamsyncd/teamsync.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/teammgr.cpp` (同上)
- `sonic-swss/orchagent/portsorch.cpp` (同上)

## APPL_DB LAG_TABLE の書き込み元と順序

APPL_DB `LAG_TABLE` には 2 プロセスが書き込む:

1. **teamsyncd** — カーネル netlink `RTM_NEWLINK` イベントを受けて即座に `admin_status` / `oper_status` / `mtu` を書き込む
   - コード: `teamsync.cpp:156-161` (`TeamSync::addLag()` — `m_lagTable.set(lagName, fvVector)`)
   - タイミング: teamd がカーネルデバイスを作成し RTM_NEWLINK が発火した時点
   - **前提条件なし**: portsyncd 完了を待たない。カーネルイベント駆動

2. **teammgrd** — CONFIG_DB `PORTCHANNEL` の SET を受けて `admin_status` / `mtu` / `tpid` / `learn_mode` を書き込む
   - コード: `teammgr.cpp:314, 513-515, 542-545, 556-559` (`TeamMgr::doLagTask()`)
   - タイミング: `addLag()` 完了後、フィールド順に適用

## orchagent (PortsOrch) の処理順序

`PortsOrch::doTask()` (`portsorch.cpp:6464-6487`) は以下の固定順序でテーブルを drain する:

```
1. APP_PORT_TABLE
2. APP_LAG_TABLE       ← LAG_TABLE はここで処理
3. APP_LAG_MEMBER_TABLE
4. APP_VLAN_TABLE
5. APP_VLAN_MEMBER_TABLE
```

### LAG 処理のブロック条件

`PortsOrch::doTask(Consumer)` (`portsorch.cpp:6513-6517`) では `allPortsReady()` が `false` の間、
LAG / VLAN / VLAN_MEMBER 処理をブロックする:

```cpp
if (!allPortsReady())
{
    return;
}
```

`allPortsReady()` は `m_initDone && m_pendingPortSet.empty()` で判定される (`portsorch.cpp:1687`)。
`m_initDone` は portsyncd が発行する `PortInitDone` 通知を受けて true になる。

## SET 時の先行必須テーブル

| 先行テーブル / 条件 | 理由 | ソース |
|---|---|---|
| `APP_PORT_TABLE` (PortInitDone) | orchagent は `allPortsReady()` が true になるまで `doLagTask()` に到達しない。teamsyncd → APPL_DB 書き込みは独立に行われるが、orchagent 側の処理は APP_PORT_TABLE 処理完了まで保留 | `portsorch.cpp:6513-6517, 1687` |
| STATE_DB `PORT_TABLE` (LAG_MEMBER 追加時のみ) | `TeamMgr::doLagMemberTask()` (`teammgr.cpp:357`) が `isPortStateOk(member)` を確認。STATE_DB `PORT_TABLE` の `state: ok` がなければ LAG_MEMBER 追加を `task_need_retry` で保留 | `teammgr.cpp:357, 67-86` |
| STATE_DB `LAG_TABLE` (LAG_MEMBER 追加時のみ) | 同じく `isLagStateOk(lag)` を確認。teamsyncd が STATE_DB `LAG_TABLE` に書き込み (`state: ok`) するまで LAG_MEMBER 追加は保留 | `teammgr.cpp:357, 89-97` |

## SET 時のフィールド適用順序 (teamsyncd → teammgrd)

teamsyncd と teammgrd は並行動作するが、それぞれ独立した順序でフィールドを APPL_DB に書き込む:

### teamsyncd 側 (teamsync.cpp:156-161)

```cpp
FieldValueTuple a("admin_status", admin_state ? "up" : "down");
FieldValueTuple o("oper_status", oper_state ? "up" : "down");
FieldValueTuple m("mtu", std::to_string(mtu));
fvVector.push_back(a);
fvVector.push_back(o);
fvVector.push_back(m);
m_lagTable.set(lagName, fvVector);  // 一括書き込み
```

3 フィールドを 1 回の `set()` で書き込む。原子的操作。

### teammgrd 側 (teammgr.cpp の doLagTask)

```
1. addLag()            — teamd プロセス起動 + カーネル bond デバイス作成
2. setLagAdminStatus() — APPL_DB admin_status 書き込み (teammgr.cpp:314)
3. setLagMtu()         — APPL_DB mtu 書き込み (teammgr.cpp:512-515)
4. setLagLearnMode()   — CONFIG_DB に learn_mode がある場合のみ (teammgr.cpp:316-320)
5. setLagTpid()        — CONFIG_DB に tpid がある場合のみ (teammgr.cpp:321-323)
```

## DEL 時の削除順序

APPL_DB `LAG_TABLE` のエントリを削除するには以下が先行必須:

| ステップ | 削除対象 | 省略時の動作 |
|---|---|---|
| 1 | `APP_VLAN_MEMBER_TABLE` (LAG が VLAN に所属する場合) | orchagent が LAG 削除前に VLAN メンバ参照をチェックする |
| 2 | `APP_LAG_MEMBER_TABLE` (全メンバポート) | teamsyncd が LAG 削除時に member table を先に del する |
| 3 | `LAG_TABLE` DEL | `TeamsSync::removeLag()` / `TeamMgr::removeLag()` が書き込む |

## 起動時シーケンス

```
CONFIG_DB PORTCHANNEL SET
  ↓
TeamMgr::addLag() → teamd プロセス起動
  ↓
teamd がカーネル bond デバイス作成 → RTM_NEWLINK 発火
  ↓
TeamSync::addLag() → APPL_DB LAG_TABLE 書き込み (admin_status/oper_status/mtu)
                   → STATE_DB LAG_TABLE 書き込み (state: ok)
  ↓
portsyncd が PortInitDone → orchagent::allPortsReady() = true
  ↓
PortsOrch::doLagTask() が APPL_DB LAG_TABLE を処理 → SAI create_lag()
  ↓
PORTCHANNEL_MEMBER 追加 → isPortStateOk + isLagStateOk 確認 → addLagMember()
```

## 証跡

- `portsorch.cpp:6464-6487`: `PortsOrch::doTask()` — tableOrder でのドレイン順
- `portsorch.cpp:6513-6517`: LAG 処理前の `allPortsReady()` ガード
- `portsorch.cpp:1685-1688`: `allPortsReady()` = `m_initDone && m_pendingPortSet.empty()`
- `teamsync.cpp:146-162`: `TeamSync::addLag()` — APPL_DB 一括書き込み
- `teamsync.cpp:198-223`: `TeamSync::addLag()` — STATE_DB `state: ok` 書き込み (team_init 後)
- `teammgr.cpp:302-330`: `TeamMgr::doLagTask()` — SET フィールド順適用
- `teammgr.cpp:357`: `doLagMemberTask()` の `isPortStateOk` + `isLagStateOk` ガード
- `teammgr.cpp:67-97`: `isPortStateOk()` / `isLagStateOk()` 実装
