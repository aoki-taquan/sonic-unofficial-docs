# Phase F 中間ファイル: VXLAN_FDB_TABLE 副次 DB 書込

ソース: `sonic-swss/orchagent/fdborch.cpp`

## 調査方針

`FdbOrch::addFdbEntry()` (fdborch.cpp:1480-1630) と `FdbOrch::deleteFdbEntry()` (fdborch.cpp:1640-1741)
で `origin == FDB_ORIGIN_VXLAN_ADVERTIZED` の場合の副次 DB 書込を追跡した。

## STATE_DB — 書込なし（VXLAN エントリは除外）

`addFdbEntry()` の STATE_DB 書込コード (fdborch.cpp:1569-1592):

```cpp
// fdborch.cpp:1569-1582
if (((fdbData.origin != FDB_ORIGIN_MCLAG_ADVERTIZED) &&
     (fdbData.origin != FDB_ORIGIN_VXLAN_ADVERTIZED)) ||
    ((fdbData.origin == FDB_ORIGIN_MCLAG_ADVERTIZED) &&
      (fdbData.type == "dynamic_local")))
{
    /* State-DB is updated only for Local Mac addresses */
    // Write to StateDb
    ...
    m_fdbStateTable.set(key, fvs);  // STATE_DB FDB_TABLE への書込
}
```

`FDB_ORIGIN_VXLAN_ADVERTIZED` はこの if 条件から除外されるため、`APP_VXLAN_FDB_TABLE` から来た
エントリは **STATE_DB `FDB_TABLE`（= `STATE_FDB_TABLE_NAME`）に書き込まれない**。

同様に `deleteFdbEntry()` の STATE_DB 削除 (fdborch.cpp:1722-1726) も:

```cpp
// fdborch.cpp:1723-1725
if ((fdbData.origin != FDB_ORIGIN_VXLAN_ADVERTIZED) && (fdbData.origin != FDB_ORIGIN_MCLAG_ADVERTIZED))
{
    m_fdbStateTable.del(key);
}
```

VXLAN_ADVERTIZED は除外されるため削除も行われない。

## CRM カウンタ更新（副次効果）

`addFdbEntry()` (fdborch.cpp:1617):

```cpp
gCrmOrch->incCrmResUsedCounter(CrmResourceType::CRM_FDB_ENTRY);
```

`deleteFdbEntry()` (fdborch.cpp:1728):

```cpp
gCrmOrch->decCrmResUsedCounter(CrmResourceType::CRM_FDB_ENTRY);
```

VXLAN FDB エントリの追加・削除は **CRM (Critical Resource Monitor) の `CRM_FDB_ENTRY` カウンタを更新する**。
これは ASIC FDB テーブルのリソース使用量追跡のため。CRM テーブルは直接 DB に書き込まれるわけではなく、
`CrmOrch` 内部カウンタを介して STATE_DB `CRM_TABLE` に反映される。

## FDB 変更通知（SUBJECT_TYPE_FDB_CHANGE）

`addFdbEntry()` / `deleteFdbEntry()` 完了後に:

```cpp
notify(SUBJECT_TYPE_FDB_CHANGE, &update);  // fdborch.cpp:1626, 1736
```

`SUBJECT_TYPE_FDB_CHANGE` の購読者（orchagent 内部のオブザーバー）:

- **MirrorOrch**: FDB 変更に応じてミラーセッションのポート解決を更新する
- **MacsecOrch**: MACsec ポートの FDB 状態に連動する（構成による）

これらは orchagent 内部の状態更新であり、直接 DB 書込には至らない場合が多いが、
MirrorOrch が STATE_DB `MIRROR_SESSION_TABLE` を更新する可能性がある（ポート解決の変化）。

## TunnelOrch 通知（VXLAN FDB 削除時のみ）

`deleteFdbEntry()` (fdborch.cpp:1738):

```cpp
notifyTunnelOrch(update.port);
```

`notifyTunnelOrch()` の実装 (fdborch.cpp:1792-1801):

```cpp
void FdbOrch::notifyTunnelOrch(Port& port)
{
    VxlanTunnelOrch* tunnel_orch = gDirectory.get<VxlanTunnelOrch*>();

    if((port.m_type != Port::TUNNEL) ||
       (port.m_fdb_count != 0))
      return;

    tunnel_orch->deleteTunnelPort(port);
}
```

VXLAN FDB エントリが削除された際、そのポートが TUNNEL 型かつ FDB カウントが 0 になった場合に
`VxlanTunnelOrch::deleteTunnelPort()` が呼ばれ、動的 VXLAN トンネルポートが解体される。
これにより SAI トンネルポートオブジェクトが削除される副次効果が生じる。

## 結論サマリ

| 副次 DB | 書込有無 | 条件 | 根拠 |
|---------|---------|------|------|
| STATE_DB `FDB_TABLE` | **なし** | VXLAN_ADVERTIZED は条件除外 | fdborch.cpp:1569-1582, 1723-1726 |
| STATE_DB `MCLAG_REMOTE_FDB_TABLE` | なし | MCLAG 専用パス | fdborch.cpp:1595-1612 |
| CRM カウンタ (`CRM_FDB_ENTRY`) | **あり** | SET/DEL 両方で inc/dec | fdborch.cpp:1617, 1728 |
| COUNTERS_DB | なし | FdbOrch は COUNTERS_DB に直接書込なし | fdborch.cpp 全体 grep で 0 件 |
| FLEX_COUNTER_DB | なし | FdbOrch は FLEX_COUNTER_DB に直接書込なし | fdborch.cpp 全体 grep で 0 件 |
| SAI FDB テーブル | **あり**（主目的） | `sai_fdb_api->create_fdb_entry()` | fdborch.cpp:1531-1542 |
| VxlanTunnelOrch → SAI tunnel port 削除 | **あり**（削除時のみ） | FDB カウント = 0 の TUNNEL ポートに限定 | fdborch.cpp:1792-1801 |
