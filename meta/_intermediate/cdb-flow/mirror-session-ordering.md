# MIRROR_SESSION テーブル — 書込み順依存調査メモ (Phase B)

調査日: 2026-05-15
調査対象:
- `sonic-swss/orchagent/mirrororch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`

---

## 1. 他テーブル先行必須

### 全ポート初期化完了 (allPortsReady) が先

`MirrorOrch::doTask()` の冒頭で `gPortsOrch->allPortsReady()` を確認する。  
false の場合は即 `return` し、Consumer キューの全エントリを保留する。

```cpp
// mirrororch.cpp:1571-1574
if (!gPortsOrch->allPortsReady())
{
    return;
}
```

**PortsOrch が全物理ポートの初期化を完了するまで、MIRROR_SESSION は一切処理されない。**  
CONFIG_DB に先に書いても orchagent 起動完了まで適用されない。

### POLICER が先行して存在すること

`policer` フィールドを指定した場合、`m_policerOrch->policerExists(fvValue(i))` が false なら `task_need_retry` を返す。  
POLICER エントリが追加されると再処理される。

```cpp
// mirrororch.cpp:434-438
if (!m_policerOrch->policerExists(fvValue(i)))
{
    SWSS_LOG_ERROR("Failed to get policer %s", fvValue(i).c_str());
    return task_process_status::task_need_retry;
}
```

**POLICER テーブルへの書込みが先。POLICER 追加後に MIRROR_SESSION が自動 retry される。**

### ERSPAN: RouteOrch による dst_ip 解決が非同期

ERSPAN セッション作成時、`m_routeOrch->attach(this, entry.dstIp)` を呼び RouteOrch にアタッチする。  
ルート解決 (next-hop / neighbor 情報取得) が完了するまでセッションは INACTIVE のまま。  
NeighOrch / FdbOrch / PortsOrch からの通知を受けて `updateSession()` が呼ばれ、完了すれば ACTIVE 化する。

```cpp
// mirrororch.cpp:516-517
// Attach the destination IP to the routeOrch
m_routeOrch->attach(this, entry.dstIp);
```

**ERSPAN の場合、CONFIG_DB への書込み直後はセッションが inactive。対応するルート・ネイバーエントリが存在してから数 ms で ACTIVE 化。**

### SPAN: dst_port が PORT テーブルに存在すること

`activateSession()` 内で `m_portsOrch->getPort(session.dst_port, dst_port)` を呼び、ポートが未存在なら `false` を返す（ACTIVE 化失敗）。

```cpp
// mirrororch.cpp:942-945
Port dst_port;
if (!m_portsOrch->getPort(session.dst_port, dst_port))
{
    SWSS_LOG_ERROR("Failed to locate Port/LAG %s", session.dst_port.c_str());
```

**SPAN セッションの `dst_port` に指定するポートは、PORT テーブルに先行して存在する必要がある。**

### src_port: PORT または PORTCHANNEL が先行して存在すること

`validateSrcPortList()` がカンマ区切りのポート名を検証する。各ポート名について `m_portsOrch->getPort()` で PHY / LAG を確認する。VLAN 等は `task_invalid_entry`。

```cpp
// mirrororch.cpp:446-450
if (!validateSrcPortList(fvValue(i)))
{
    SWSS_LOG_ERROR("Failed to get valid source port list %s", fvValue(i).c_str());
    return task_process_status::task_invalid_entry;
}
```

**`src_port` に列挙するポートはすべて PORT / PORTCHANNEL テーブルに先行して存在する必要がある。存在しない場合は task_invalid_entry (retry なし)。**

---

## 2. DEL 順依存

### ACL_RULE など refCount 保持中は DEL 不可

`deleteEntry()` 冒頭で `session.refCount` が正の場合、`task_need_retry` を返す。ACL_RULE 等が `MIRROR_*_ACTION` でセッションを参照している間は削除できない。

```cpp
// mirrororch.cpp:539-543
if (session.refCount)
{
    SWSS_LOG_WARN("Failed to remove still referenced mirror session %s, retry...", name.c_str());
    return task_process_status::task_need_retry;
}
```

**MIRROR_SESSION を削除する前に、参照中のすべての ACL_RULE / PBH 等を先に削除する必要がある。**

---

## 3. ERSPAN NEIGHBOR / INTERFACE / ROUTE 先行依存チェーン

ERSPAN セッションの ACTIVE 化は以下の解決チェーン完了を必要とする:

1. **ROUTE 先行**: `m_routeOrch->attach(this, entry.dstIp)` (L517) で RouteOrch アタッチ。Route callback が来るまで待機。
2. **NEIGHBOR 先行**: `NeighOrch::getNeighborEntry(dstIp, neighbor, mac)` (L656-660) で ARP/NDP エントリ確認。未解決なら `SUBJECT_TYPE_NEIGH_CHANGE` で再評価。
3. **INTERFACE / PORT 先行**: `m_portsOrch->getPort(neighbor.alias, port)` (L669) でネイバーのポート OID 取得。ポートが未初期化なら SAI へ monitor port を渡せない。
4. **FDB 先行 (VLAN SVI 経由)**: `FdbOrch::getPort(mac, vlan_id, member)` (L732-743) で FDB 照会。FDB 未学習なら `SUBJECT_TYPE_FDB_CHANGE` で再評価。

MirrorOrch コンストラクタ (L93-95) で `PortsOrch` / `NeighOrch` / `FdbOrch` の Observer として登録されているため、これらの変化時に自動的に `updateSession()` / `updateSessionDstPort()` が呼ばれる。

---

## 4. SAI `create_mirror_session` 属性設定順序

`activateSession()` が構築する属性リストの順序:

| 順序 | SAI 属性 | 条件 | evidence |
|------|---------|------|---------|
| 1 | `SAI_MIRROR_SESSION_ATTR_TC` | queue != 0 のみ | `mirrororch.cpp:931-937` |
| 2 | `SAI_MIRROR_SESSION_ATTR_MONITOR_PORT` | SPAN: dst_port OID / ERSPAN: neighborInfo.portId | `mirrororch.cpp:949-975` |
| 3 | `SAI_MIRROR_SESSION_ATTR_TYPE` | SPAN: LOCAL / ERSPAN: ENHANCED_REMOTE | `mirrororch.cpp:953-978` |
| 4 | VLAN 属性群 (TPID/ID/PRI/CFI) | ERSPAN + VLAN nexthop のみ | `mirrororch.cpp:982-1001` |
| 5-13 | ERSPAN_ENCAPSULATION_TYPE → GRE_PROTOCOL_TYPE | ERSPAN のみ | `mirrororch.cpp:1005-1049` |
| 14 | `SAI_MIRROR_SESSION_ATTR_POLICER` | policer 指定時のみ | `mirrororch.cpp:1055-1065` |

create はアトミック 1 呼び出し (L1067)。部分更新なし。

---

## 5. ACL bind 順序

- **SET**: MIRROR_SESSION 作成 → ACL_TABLE 作成 → ACL_RULE 作成。ACL_RULE 作成時に `AclOrch::increaseRefCount()` (aclorch.cpp:2376) 呼び出し。セッション未存在なら ACL_RULE 作成失敗。
- **DEL**: ACL_RULE DEL (`decreaseRefCount`) → MIRROR_SESSION DEL。`refCount > 0` 中は `task_need_retry` (L539-543)。

---

## 6. Notification（通知）順序

`MirrorOrch` は `PortsOrch` / `NeighOrch` / `FdbOrch` の Observer として登録されている。

- `PortsOrch`: ポート状態変化 → `MirrorOrch::update()` → SPAN の `dst_port` 変化時に `updateSessionDstPort()` 呼び出し
- `NeighOrch`: ネイバー追加/削除 → ERSPAN の `updateSession()` トリガ
- `FdbOrch`: FDB エントリ変化 → ERSPAN nexthop が VLAN 経由のとき再評価

ERSPAN は RouteOrch の callback (via Observer) で非同期に ACTIVE 化するため、**CONFIG_DB 書込みから ACTIVE になるまでのタイミングはルートテーブルの状態に依存する**。

---

## 7. warm-reboot 影響

warm-reboot 前にアクティブだったセッションは `m_recoverySessionMap` に保持される（mirrororch.cpp:130-160）。  
`doTask()` の最後で `m_recoverySessionMap.clear()` を呼び、recovery 状態をクリアする（mirrororch.cpp:1610）。

warm-reboot 後も CONFIG_DB の MIRROR_SESSION エントリが残っていれば、`allPortsReady()` 通過後に再作成される。ERSPAN は再び RouteOrch アタッチから非同期 ACTIVE 化の手順を踏む。

---

## 8. まとめ（書込み順依存一覧）

| 依存カテゴリ | 必須順序 | コード根拠 |
|------------|---------|-----------|
| allPortsReady | 全ポート初期化完了後でないと一切処理されない | `mirrororch.cpp:1571-1574` |
| POLICER → MIRROR_SESSION | `policer` フィールド指定時は POLICER エントリが先 | `mirrororch.cpp:434-438` |
| PORT → MIRROR_SESSION (SPAN dst_port) | dst_port に指定するポートが PORT テーブルに存在すること | `mirrororch.cpp:942-945` |
| PORT/PORTCHANNEL → MIRROR_SESSION (src_port) | src_port の各ポートが PORT/PORTCHANNEL テーブルに存在すること | `mirrororch.cpp:446-450` |
| ROUTE/NEIGHBOR/INTERFACE → ERSPAN ACTIVE | CONFIG_DB 書込み直後は INACTIVE。ROUTE → NEIGHBOR → PORT OID → (FDB) 解決後に非同期 ACTIVE 化 | `mirrororch.cpp:517,656,669,732` |
| MIRROR_SESSION → ACL_RULE (bind) | ACL_RULE は MIRROR_SESSION が先に存在すること。セッション未存在なら increaseRefCount 失敗 | `aclorch.cpp:2376` |
| ACL_RULE DEL → MIRROR_SESSION DEL | refCount > 0 の間は DEL が task_need_retry | `mirrororch.cpp:539-543` |
