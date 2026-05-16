# MIRROR_SESSION テーブル — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB MIRROR_SESSION` テーブル
ソース: `sonic-swss/orchagent/mirrororch.cpp`, `orchdaemon.cpp`

## 1. Consumer 登録パス

`MirrorOrch` は `Orch` 基底クラスを継承し、`ConsumerStateTable` ベースの swsscommon Consumer パスで CONFIG_DB `MIRROR_SESSION` を購読する。

```cpp
// orchdaemon.cpp:403-406
TableConnector stateDbMirrorSession(m_stateDb, STATE_MIRROR_SESSION_TABLE_NAME);
TableConnector confDbMirrorSession(m_configDb, CFG_MIRROR_SESSION_TABLE_NAME);
gMirrorOrch = new MirrorOrch(stateDbMirrorSession, confDbMirrorSession,
                              gPortsOrch, gRouteOrch, gNeighOrch, gFdbOrch, gPolicerOrch, gSwitchOrch);

// mirrororch.cpp:79-81 (constructor)
MirrorOrch::MirrorOrch(TableConnector stateDbConnector, TableConnector confDbConnector, ...)
    : Orch(confDbConnector.first, confDbConnector.second),  // ← ConsumerStateTable 生成
```

`Orch` 基底クラスが `ConsumerStateTable(confDbConnector.first, confDbConnector.second)` を内部生成し、`OrchDaemon` の Select ループ (`orchdaemon.cpp:1127-1142`) がイベントをポーリングして `MirrorOrch::doTask()` を呼ぶ。

- keyspace notification (`PSUBSCRIBE`) は使用しない
- ZMQ パスも使用しない (CONFIG_DB MIRROR_SESSION は通常 ConsumerStateTable)
- `orchdaemon.cpp:1139-1142`: `gMirrorOrch->doTask()` は全 Orch の後で最後に実行

## 2. Observer パターン (Subject アタッチ)

`MirrorOrch` コンストラクタで 3 つの Subject にアタッチ:

```cpp
// mirrororch.cpp:93-95
m_portsOrch->attach(this);   // LAG_MEMBER / VLAN_MEMBER
m_neighOrch->attach(this);   // NEIGH_CHANGE
m_fdbOrch->attach(this);     // FDB_CHANGE
```

ERSPAN セッション作成時はさらに per-IP で RouteOrch にアタッチ:

```cpp
// mirrororch.cpp:517
m_routeOrch->attach(this, entry.dstIp);

// 削除時 (mirrororch.cpp:557)
m_routeOrch->detach(this, session.dstIp);
```

## 3. MirrorOrch::update() ディスパッチ (mirrororch.cpp:160-199)

```cpp
void MirrorOrch::update(SubjectType type, void *cntx)
{
    switch(type) {
    case SUBJECT_TYPE_NEXTHOP_CHANGE:
        updateNextHop(*static_cast<NextHopUpdate *>(cntx));   break;
    case SUBJECT_TYPE_NEIGH_CHANGE:
        updateNeighbor(*static_cast<NeighborUpdate *>(cntx)); break;
    case SUBJECT_TYPE_FDB_CHANGE:
        updateFdb(*static_cast<FdbUpdate *>(cntx));           break;
    case SUBJECT_TYPE_LAG_MEMBER_CHANGE:
        updateLagMember(*static_cast<LagMemberUpdate *>(cntx)); break;
    case SUBJECT_TYPE_VLAN_MEMBER_CHANGE:
        updateVlanMember(*static_cast<VlanMemberUpdate *>(cntx)); break;
    }
}
```

| SubjectType | 発行 Orch | ハンドラ | 目的 |
|---|---|---|---|
| `SUBJECT_TYPE_NEXTHOP_CHANGE` | RouteOrch | `updateNextHop()` (L1293) | ERSPAN nexthop prefix / nexthop group 変化 → `updateSession()` |
| `SUBJECT_TYPE_NEIGH_CHANGE` | NeighOrch | `updateNeighbor()` (L1376) | dst_ip / nexthop の neighbor MAC 解決後 → `updateSession()` |
| `SUBJECT_TYPE_FDB_CHANGE` | FdbOrch | `updateFdb()` (L1404) | VLAN SVI 経由 ERSPAN の FDB 学習完了 → `updateSession()` |
| `SUBJECT_TYPE_LAG_MEMBER_CHANGE` | PortsOrch | `updateLagMember()` | src_port LAG メンバ変化 → セッション再評価 |
| `SUBJECT_TYPE_VLAN_MEMBER_CHANGE` | PortsOrch | `updateVlanMember()` | VLAN メンバ変化 → セッション再評価 |

## 4. SAI mirror_session_api 呼び出し経路

APP_DB への中継なし。`activateSession()` が直接 SAI API を呼ぶ:

```
MirrorOrch::activateSession()
  ├─ (SPAN)  sai_mirror_api->create_mirror_session([SAI_MIRROR_SESSION_TYPE_LOCAL, ...])
  └─ (ERSPAN) sai_mirror_api->create_mirror_session([SAI_MIRROR_SESSION_TYPE_ENHANCED_REMOTE, ...])
       attrs: SAI_MIRROR_SESSION_ATTR_ERSPAN_ENCAPSULATION_TYPE
              SAI_MIRROR_SESSION_ATTR_IPHDR_VERSION
              SAI_MIRROR_SESSION_ATTR_TOS
              SAI_MIRROR_SESSION_ATTR_TTL
              SAI_MIRROR_SESSION_ATTR_SRC_IP_ADDRESS
              SAI_MIRROR_SESSION_ATTR_DST_IP_ADDRESS
              SAI_MIRROR_SESSION_ATTR_SRC_MAC_ADDRESS
              SAI_MIRROR_SESSION_ATTR_DST_MAC_ADDRESS
              SAI_MIRROR_SESSION_ATTR_GRE_PROTOCOL_TYPE
              SAI_MIRROR_SESSION_ATTR_MONITOR_PORT
              SAI_MIRROR_SESSION_ATTR_TC (queue != 0 の場合のみ)
              SAI_MIRROR_SESSION_ATTR_POLICER (policer 指定時)
```

## 5. MirrorOrch → 下流への notify

`MirrorOrch` 自身も Subject として機能し、セッション状態変化を発行する:

```cpp
// activateSession() — mirrororch.cpp:1095-1096
MirrorSessionUpdate update = { name, true };
notify(SUBJECT_TYPE_MIRROR_SESSION_CHANGE, static_cast<void *>(&update));

// deactivateSession() — mirrororch.cpp:1110-1111
MirrorSessionUpdate update = { name, false };
notify(SUBJECT_TYPE_MIRROR_SESSION_CHANGE, static_cast<void *>(&update));
```

購読者: `AclOrch`, `DtelOrch` などが `SUBJECT_TYPE_MIRROR_SESSION_CHANGE` を受信し、ACL mirror action の SAI OID を更新する。

## 6. STATE_DB 書き戻し

`setSessionState()` (mirrororch.cpp:574) が `STATE_DB MIRROR_SESSION_TABLE|<name>` へ書き込む:

| フィールド | 書込みタイミング |
|---|---|
| `status` = `active`/`inactive` | activateSession / deactivateSession |
| `next_hop_ip` | updateNextHop |
| `monitor_port` | updateSession / updateSessionDstPort |
| `route_prefix` | updateNextHop |
| `vlan_id` | updateSessionType (ERSPAN + VLAN SVI 経由) |

## 7. 通信フロー全体図

```
CONFIG_DB MIRROR_SESSION
    │ ConsumerStateTable (swsscommon Select ループ)
    ▼
MirrorOrch::doTask() → createEntry() / deleteEntry()
    │                         │
    │ m_routeOrch->attach()   │ (ERSPAN: per dst_ip)
    ▼                         ▼
RouteOrch ──NEXTHOP_CHANGE──→ updateNextHop()  ──→ updateSession()
NeighOrch  ──NEIGH_CHANGE───→ updateNeighbor() ──→ updateSession()
FdbOrch    ──FDB_CHANGE─────→ updateFdb()      ──→ updateSession()
PortsOrch  ──LAG/VLAN───────→ updateLag/VlanMember() ──→ updateSession()
    │
    ▼ activateSession()
sai_mirror_api->create_mirror_session()
    │
    ▼ notify(SUBJECT_TYPE_MIRROR_SESSION_CHANGE)
AclOrch / DtelOrch (ACL mirror action SAI OID 更新)
    │
    ▼ setSessionState()
STATE_DB MIRROR_SESSION_TABLE|<name>
```

## 8. 参考行番号

- `orchdaemon.cpp`: 403-406 (MirrorOrch 生成), 1139-1142 (doTask 実行順)
- `mirrororch.cpp`: 79-110 (constructor / attach), 160-199 (update dispatch)
- `mirrororch.cpp`: 517 (routeOrch->attach per dstIp), 557 (detach)
- `mirrororch.cpp`: 574-647 (setSessionState / STATE_DB 書き戻し)
- `mirrororch.cpp`: 760-800 (updateSession)
- `mirrororch.cpp`: 1060-1096 (activateSession SAI 呼び出し + notify)
- `mirrororch.cpp`: 1101-1131 (deactivateSession + notify)
- `mirrororch.cpp`: 1293-1370 (updateNextHop)
- `mirrororch.cpp`: 1376-1401 (updateNeighbor)
- `mirrororch.cpp`: 1404-1460 (updateFdb)
