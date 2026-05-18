# tunnel-encap-orch — Phase F: side-effects

## 調査対象

slug: tunnel-encap-orch
phase: side-effects (副次 DB 書込・外部システム影響)
調査日: 2026-05-18

## ソース

- `orchagent/vxlanorch.cpp` (4305596156d70e9797e8a881b3d19b46de0bce0d)
- `orchagent/vxlanorch.h` (4305596156d70e9797e8a881b3d19b46de0bce0d)

## 調査結果

### STATE_DB 書込 (STATE_VXLAN_TUNNEL_TABLE)

`VxlanTunnel` コンストラクタ (vxlanorch.cpp:537–539) は EVPN 作成元トンネル
(`TNL_CREATION_SRC_EVPN`) の場合のみ `addRemoveStateTableEntry()` を呼び STATE_DB に書き込む。
CLI 作成トンネル (`TNL_CREATION_SRC_CLI`) は `addVTEP()` を呼ぶのみで STATE_DB 書込なし。

`addRemoveStateTableEntry()` (vxlanorch.cpp:1913) が STATE_DB の
`STATE_VXLAN_TUNNEL_TABLE|<tunnel_name>` に以下を書く:
- `src_ip`: トンネル送信元 IP
- `dst_ip`: トンネル宛先 IP (または `0.0.0.0`)
- `tnl_src`: `CLI` または `EVPN`
- `operstatus`: `down` (初期値)

デストラクタは同関数で `add=false` を渡しエントリを削除する。

`updateDbTunnelOperStatus()` (vxlanorch.cpp:1893) が SAI ポートステータス変化イベントで
`operstatus` を `up`/`down` に更新する。

### COUNTERS_DB 書込 (FlexCounter)

`createTunnelHw()` (vxlanorch.cpp:911) が SAI create_tunnel 成功後に
`addTunnelToFlexCounter(ids_.tunnel_id, tunnel_name_)` を呼ぶ。
実際の COUNTERS_DB 書込は `doTask(SelectableTimer)` (1 秒タイマー) 発火時:
- `COUNTERS_DB::COUNTERS_TUNNEL_NAME_MAP`: `{tunnel_name → sai_oid}`
- `COUNTERS_DB::COUNTERS_TUNNEL_TYPE_MAP`: `{sai_oid → "SAI_TUNNEL_TYPE_VXLAN"}`
- `FLEX_COUNTER_DB` への FlexCounter 登録

削除時は `removeTunnelFromFlexCounter()` (vxlanorch.cpp:1347) で両テーブルから削除。

### VxlanTunnelOrch 内部マップ更新 (in-memory)

`VxlanTunnelMapOrch::addOperation` (vxlanorch.cpp:2120) が
`tunnel_orch->addVlanMappedToVni(vni_id, vlan_id)` を呼び、
`vxlan_vni_vlan_map_table_[vni] = vlan_id` を更新する (vxlanorch.h:354)。
この in-memory マップは `EvpnRemoteVnip2pOrch` / `EvpnRemoteVnip2mpOrch` が参照する。
DB への書込はない。

### APPL_DB / CONFIG_DB 書込

なし。VxlanTunnelOrch / VxlanTunnel は CONFIG_DB / APPL_DB に書き戻さない。

## ブロック案

```markdown
<!-- side-effects -->
## 副次 DB 書込 (Phase F)

`VxlanTunnelOrch` / `VxlanTunnel` がトンネル生成・削除時に引き起こす副次的な DB 書込とシステム副作用[^1]。

| 副次 DB | テーブル / キー | トリガ | タイミング |
|---------|--------------|--------|----------|
| STATE_DB | `VXLAN_TUNNEL_TABLE\|<tunnel_name>` (`src_ip`, `dst_ip`, `tnl_src`, `operstatus=down`) | EVPN 作成トンネルのコンストラクタ → `addRemoveStateTableEntry(add=true)` (`vxlanorch.cpp:537`) | `createTunnelHw()` / コンストラクタと同期 |
| STATE_DB | `VXLAN_TUNNEL_TABLE\|<tunnel_name>` (`operstatus`: `up`/`down`) | SAI ポートステータス変化 → `updateDbTunnelOperStatus()` (`vxlanorch.cpp:1893`) | アンダーレイ経路確立時に非同期 |
| COUNTERS_DB | `COUNTERS_TUNNEL_NAME_MAP` / `COUNTERS_TUNNEL_TYPE_MAP` | `addTunnelToFlexCounter()` → `doTask(SelectableTimer)` (`vxlanorch.cpp:1322–1335`) | SAI create_tunnel 成功後、最大 1 秒遅延 |
| FLEX_COUNTER_DB | FlexCounter エントリ | `tunnel_stat_manager->setCounterIdList()` | COUNTERS_DB 書込と同タイミング |
| APPL_DB | なし | 書戻しなし | — |
| CONFIG_DB | なし | 読取専用 | — |

### 詳細: STATE_DB 書込対象

CLI 作成トンネル (`TNL_CREATION_SRC_CLI`) のコンストラクタは `addVTEP()` を呼ぶのみで
`addRemoveStateTableEntry()` を呼ばない。STATE_DB への初期書込は **EVPN 作成トンネルのみ**。
ただし `updateDbTunnelOperStatus()` はトンネル種別に関わらず oper-status 変化時に STATE_DB を更新する。

```
VxlanTunnel ctor (TNL_CREATION_SRC_EVPN)
  → addRemoveStateTableEntry(add=true)
    → STATE_VXLAN_TUNNEL_TABLE|<name> = {src_ip, dst_ip, tnl_src="EVPN", operstatus="down"}

VxlanTunnel dtor
  → addRemoveStateTableEntry(add=false)
    → STATE_VXLAN_TUNNEL_TABLE|<name> DEL
```

### 詳細: FlexCounter 登録フロー

SAI `create_tunnel()` 成功 (`vxlanorch.cpp:911`) → `addTunnelToFlexCounter(oid, name)` →
`m_pendingAddToFlexCntr[oid] = name` に追加。実際の COUNTERS_DB 書込は
`FLEX_COUNTER_UPD_INTERVAL=1` 秒タイマー発火時に行われる。
対象は SAI tunnel_id OID（ブリッジポート OID ではない）。

### 詳細: in-memory マップ更新

`VxlanTunnelMapOrch::addOperation` (vxlanorch.cpp:2120) は処理完了後
`addVlanMappedToVni(vni_id, vlan_id)` を呼び `vxlan_vni_vlan_map_table_[vni] = vlan_id` を更新する。
この in-memory マップは `EvpnRemoteVnip2pOrch` / `EvpnRemoteVnip2mpOrch` が EVPN
リモート VNI 解決時に参照する。**DB への書込はない**。

> 詳細スキャンノート: `meta/_intermediate/cdb-flow/tunnel-encap-orch-side-effects.md`

<!-- /side-effects -->
```

## 引用

[^1]: VxlanTunnel ctor/dtor/addRemoveStateTableEntry (`vxlanorch.cpp:537,545,1913`), addTunnelToFlexCounter (`vxlanorch.cpp:911,1342`), addVlanMappedToVni (`vxlanorch.cpp:2120`, `vxlanorch.h:354`). <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/vxlanorch.cpp>
