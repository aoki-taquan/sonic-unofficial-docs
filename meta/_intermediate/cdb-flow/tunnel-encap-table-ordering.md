# TUNNEL_ENCAP_TABLE (FIXED_TUNNEL_TABLE) — ordering 調査メモ

## 調査対象ファイル

- `sonic-swss/orchagent/p4orch/p4orch.cpp`
- `sonic-swss/orchagent/p4orch/gre_tunnel_manager.cpp`
- `sonic-swss/orchagent/p4orch/gre_tunnel_manager.h`

## P4Orch 内での処理順序 (ADD)

`p4orch.cpp:88-102` で定義される `m_p4ManagerAddPrecedence` の順序:

1. TablesDefnManager (TABLE_DEFINITION)
2. RouterInterfaceManager (ROUTER_INTERFACE) ← GRE tunnel が依存
3. NeighborManager (NEIGHBOR) ← GRE tunnel が依存
4. **GreTunnelManager (FIXED_TUNNEL_TABLE)** ← 本テーブル (4番目)
5. NextHopManager (NEXTHOP)
6. WcmpManager (WCMP_GROUP)
7. L3MulticastManager / IpMulticastManager
8. RouteManager (IPV4/IPV6)
9. MirrorSessionManager, AclTableManager, AclRuleManager, L3AdmitManager
10. TunnelDecapGroupManager (IPV6_TUNNEL_TERMINATION)
11. ExtTablesManager

削除 (DEL) には専用の precedence リストなし。削除順はコントローラ側の責務。

## SET における依存前提条件

`validateGreTunnelAppDbEntry()` (gre_tunnel_manager.cpp:106-177) が SET 時に以下を必須チェック:

1. `router_interface_id` に対応する `SAI_OBJECT_TYPE_ROUTER_INTERFACE` が P4OidMapper に存在すること
2. `(router_interface_id, encap_dst_ip)` の neighbor エントリ (`SAI_OBJECT_TYPE_NEIGHBOR_ENTRY`) が P4OidMapper に存在すること

→ RIF と neighbor が先行して作成されていないと `SWSS_RC_NOT_FOUND` で失敗する。

## DEL における依存チェック

`validateGreTunnelAppDbEntry()` (DEL パス) が ref_count を確認:
- `m_p4OidMapper->getRefCount(SAI_OBJECT_TYPE_TUNNEL, ...)` で参照カウントを確認
- `ref_count > 0` の場合は `SWSS_RC_INVALID_PARAM` エラー
→ GRE tunnel を参照しているオブジェクトを先に削除しないと消せない。

## Warm-reboot 挙動

`doTask(ConsumerBase&)` (p4orch.cpp:142-152):
- `consumer.m_toSync` が空でない場合は warm-boot 復元フェーズ
- `m_publisher.setEnableDbWriteAndNotify(false)` で DB 書き戻しを無効化
- エントリを enqueue → drain して SAI 状態を復元
- drain 後に `setEnableDbWriteAndNotify(true)` に戻す

これは `m_p4ManagerAddPrecedence` の順序に従って全マネージャの drain を順次実行する
(`P4Orch::drain()`: p4orch.cpp:266-276)。

## bulk SAI 呼び出しモード

`createGreTunnels()` (gre_tunnel_manager.cpp:429):
- `sai_tunnel_api->create_tunnels()` を `SAI_BULK_OP_ERROR_MODE_STOP_ON_ERROR` で呼び出し
- 1 件でも失敗するとバッチ内の後続エントリはすべてキャンセル

## drain 内のバッチ処理

`drain()` (gre_tunnel_manager.cpp:204-302):
- 同一 op (SET/DEL) かつ同一 update/create 種別のエントリを蓄積してから `processEntries()` を一括呼び出し
- op が変わる (SET→DEL, DEL→SET) またはupdate種別が変わると前バッチを先に処理してから次バッチへ

## 結論

FIXED_TUNNEL_TABLE エントリは以下の順序制約を持つ:

ADD: RIF → Neighbor → **GRE Tunnel** → (NextHop など下流)
DEL: (NextHop など上流) → **GRE Tunnel** → Neighbor/RIF

warm-reboot は `m_toSync` に残留したエントリを `m_p4ManagerAddPrecedence` 順で replay する (DB 書き戻し無効)。
