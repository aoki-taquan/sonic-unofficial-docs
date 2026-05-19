# VXLAN_FDB_TABLE — Phase F side-effects 調査ノート

## 調査対象ソース

- `sonic-swss/orchagent/fdborch.cpp` (主: addFdbEntry, removeFdbEntry, update)
- `sonic-swss/fdbsyncd/fdbsync.cpp` (processStateFdb, processStateMclagRemoteFdb)
- `sonic-swss/orchagent/orchdaemon.cpp` (attach 関係)
- `sonic-swss/orchagent/mirrororch.cpp` (SUBJECT_TYPE_FDB_CHANGE subscriber)

## 結論

VXLAN_FDB_TABLE エントリは `FDB_ORIGIN_VXLAN_ADVERTIZED` として処理されるため、**STATE_DB:FDB_TABLE への書き込みは行われない**。ただし以下の副次 DB 書込みと内部通知が発生する。

### 1. STATE_DB 書込み

`addFdbEntry()` (`fdborch.cpp:1567-1613`) での origin 判定:

```cpp
// fdborch.cpp:1567-1572
if ((fdbData.origin == FDB_ORIGIN_LEARN) ||
    (fdbData.origin == FDB_ORIGIN_PROVISIONED) ||
    (fdbData.origin == FDB_ORIGIN_ADVERTIZED) ||
    ((fdbData.origin == FDB_ORIGIN_MCLAG_ADVERTIZED) && (fdbData.type == "dynamic_local")))
{
    // → m_fdbStateTable.set(key, fvs);  ← VXLAN は該当しない
```

`FDB_ORIGIN_VXLAN_ADVERTIZED` はこの条件に含まれないため、`STATE_DB:FDB_TABLE` にはエントリを書かない。

`removeFdbEntry()` (`fdborch.cpp:1722-1726`):

```cpp
if ((fdbData.origin != FDB_ORIGIN_VXLAN_ADVERTIZED) && (fdbData.origin != FDB_ORIGIN_MCLAG_ADVERTIZED))
{
    m_fdbStateTable.del(key);
}
```

削除時も `FDB_ORIGIN_VXLAN_ADVERTIZED` は `STATE_DB:FDB_TABLE` から削除しない（書いていないため）。

### 2. MCLAG remote FDB state table

VXLAN 経由 (`FDB_ORIGIN_VXLAN_ADVERTIZED`) のエントリは `m_mclagFdbStateTable` (STATE_DB:MCLAG_REMOTE_FDB_TABLE) にも書かれない（`fdborch.cpp:1595-1613`）。

### 3. CRM カウンタ更新

- 新規 FDB エントリ作成: `gCrmOrch->incCrmResUsedCounter(CRM_FDB_ENTRY)` (`fdborch.cpp:1617`)
- FDB エントリ削除: `gCrmOrch->decCrmResUsedCounter(CRM_FDB_ENTRY)` (`fdborch.cpp:1728`)

CRM カウンタは COUNTERS_DB に書かれる。

### 4. Subject 通知 (内部 Observer パターン)

`addFdbEntry()` 完了後に `notify(SUBJECT_TYPE_FDB_CHANGE, &update)` が呼ばれる (`fdborch.cpp:1626`)。
`removeFdbEntry()` 完了後も同様 (`fdborch.cpp:1736`)。

Observer:
- **MirrorOrch**: `mirrororch.cpp:95` で `m_fdbOrch->attach(this)` して `SUBJECT_TYPE_FDB_CHANGE` を受信。ミラーセッションの next-hop が FDB 変化で再評価される (`mirrororch.cpp:179, 1400`)。
- **MuxOrch**: `muxorch.cpp:2161` で同イベントを受信し、MUX 状態管理に反映。

### 5. VxlanTunnelOrch へのコールバック

`removeFdbEntry()` 末尾で `notifyTunnelOrch(update.port)` を呼ぶ (`fdborch.cpp:1738`)。

```cpp
// fdborch.cpp:1792-1801
void FdbOrch::notifyTunnelOrch(Port& port) {
    VxlanTunnelOrch* tunnel_orch = gDirectory.get<VxlanTunnelOrch*>();
    if((port.m_type != Port::TUNNEL) || (port.m_fdb_count != 0))
      return;
    tunnel_orch->deleteTunnelPort(port);
}
```

VXLAN TUNNEL ポートの FDB エントリが 0 になったとき、VxlanTunnelOrch がトンネルポートを削除する。これは VXLAN_FDB_TABLE エントリ削除の間接的副作用。

### 6. fdbsyncd の STATE_DB 読み取り (逆方向)

`fdbsyncd` は `STATE_DB:FDB_TABLE` を **読み取り側** として監視し、ローカル MAC 学習イベントを netlink にミラーする (`fdbsync.cpp:125, processStateFdb()`)。VXLAN_FDB_TABLE への書き込みが STATE_DB:FDB_TABLE を経由しないため、この逆フィードバックは VXLAN FDB エントリには適用されない。
