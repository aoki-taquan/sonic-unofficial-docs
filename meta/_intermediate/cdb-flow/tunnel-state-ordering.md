# tunnel-state — Phase B: 書込み順依存

slug: tunnel-state
phase: B (ordering)
source: orchagent/tunneldecaporch.cpp@4305596156d70e9797e8a881b3d19b46de0bce0d
         orchagent/vxlanorch.cpp@4305596156d70e9797e8a881b3d19b46de0bce0d
         cfgmgr/vxlanmgr.cpp@4305596156d70e9797e8a881b3d19b46de0bce0d

## 調査対象

STATE_DB への書き込み順序、トリガー、前提条件を各テーブル別に整理する。

## TUNNEL_DECAP_TABLE (STATE_DB)

書き込みは `setDecapTunnelStatus()` が担当。以下の順序が保証されている:

1. APPL_DB に TUNNEL_DECAP_TABLE エントリが存在する (`tunnelmgrd` による投影完了)
2. `tunneldecaporch` が `addDecapTunnel()` を呼び SAI tunnel 作成に成功
3. 成功後に `setDecapTunnelStatus()` が STATE_DB に書き込む

`APPEND_IF_NOT_EMPTY` マクロ使用のため、内部キャッシュで空のフィールドは書かれない。
既存トンネルの更新 (dscp_mode / ttl_mode 変更) 後にも再び `setDecapTunnelStatus()` が呼ばれる (L285-287)。

DEL は `removeDecapTunnel()` で `stateTunnelDecapTable->del()` を呼ぶが、
参照カウント (`ref_count > 0`) が残る場合は DEL されない (引用: tunneldecaporch.cpp RemoveTunnelIfNotReferenced)。

## TUNNEL_DECAP_TERM_TABLE (STATE_DB)

1. TUNNEL_DECAP_TABLE エントリが先に STATE_DB に存在する (トンネル本体が作成済みであること)
2. `addDecapTunnelTermEntry()` が SAI tunnel term entry 作成に成功
3. 成功後に `setDecapTunnelTermStatus()` が呼ばれ STATE_DB に書き込む

TERM エントリはトンネル本体より先に届くことができる (`unhandledDecapTerms` バッファ)。
しかし STATE_DB には必ずトンネル本体書き込み後に書かれる。

DEL: `removeDecapTunnelTermStatus()` が呼ばれる。トンネル本体 DEL の前に TERM を先に DEL するのが推奨。

## VXLAN_TUNNEL_TABLE (STATE_DB)

`addRemoveStateTableEntry()` が書き込む (vxlanorch.cpp L1913):

前提: `VxlanTunnelOrch::addOperation()` が VXLAN_TUNNEL を受け取り、
さらに VXLAN_TUNNEL_MAP や VRF_MAP の addOperation で SAI tunnel 作成が完了するまで
STATE_DB に書かれない。実際は `addTunnelUser()` または `createDynamicDIPTunnel()` 内から呼ばれる。

Warm boot 時 (WarmStart::INITIALIZED かつ既存エントリが STATE_DB に存在):
→ 書き込みをスキップし重複防止。

`operstatus` は作成時 `"down"` 固定。ポート oper-up イベントで `up` に遷移。

DEL: `addRemoveStateTableEntry(add=false)` で `del()` を呼ぶ。

## VXLAN_TABLE (STATE_DB)

`createVxlan()` (vxlanmgr.cpp L891) が成功した場合のみ書き込む。

前提:
1. CONFIG_DB の `VXLAN_TUNNEL` エントリが存在
2. Linux カーネルの VXLAN netdevice 作成 (`createVxlanNetdevice()`) が成功
3. 成功後のみ `state=ok` を書き込む

失敗時 (netdevice 作成失敗) は STATE_DB エントリが存在しない。
削除時: `m_stateVxlanTable.del()` が呼ばれる (vxlanmgr.cpp L908)。

## SET / DEL 推奨順序

### SET 操作 (STATE_DB 書き込みを起こすために必要な前提)

| 順序 | 操作 | 理由 |
|------|------|------|
| 1 | CONFIG_DB `TUNNEL` SET | tunnelmgrd が APPL_DB に投影 |
| 2 | APPL_DB `TUNNEL_DECAP_TABLE` SET (自動) | tunneldecaporch が SAI 処理 |
| 3 | SAI tunnel create 成功 | TUNNEL_DECAP_TABLE STATE_DB に書き込み |
| 4 | APPL_DB `TUNNEL_DECAP_TERM_TABLE` SET (自動) | TERM STATE_DB に書き込み |

### DEL 操作の安全順序

```
DEL TUNNEL_DECAP_TERM_TABLE エントリ  # term を先に DEL
DEL TUNNEL_DECAP_TABLE エントリ       # ref_count=0 になってから STATE_DB DEL
DEL CONFIG_DB TUNNEL                  # tunnelmgrd → tunneldecaporch → SAI DEL
```

VXLAN_TABLE は vxlanmgrd が VXLAN_TUNNEL の DEL を受け取った時点で自動削除される。
