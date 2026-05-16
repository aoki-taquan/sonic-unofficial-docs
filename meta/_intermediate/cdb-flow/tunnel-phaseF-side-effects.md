# TUNNEL (IPinIP) — Phase F 副次 DB 書込

調査日: 2026-05-16  
ソース: `sonic-swss/orchagent/tunneldecaporch.cpp`  
対象ページ: `docs/reference/config-db/tunnel.md`

---

## 1. ASIC_DB — SAI tunnel オブジェクト群

`tunneldecaporch` が `addDecapTunnel()` を呼ぶと、syncd 経由で ASIC_DB に以下の SAI オブジェクトが生成される。

| SAI API 呼び出し | 生成オブジェクト種別 | トリガ箇所 | 主要 SAI 属性 |
|----------------|------------------|-----------|-------------|
| `sai_router_intfs_api->create_router_interface()` | `SAI_OBJECT_TYPE_ROUTER_INTERFACE` (overlay loopback) | `addDecapTunnel()` L753 | `TYPE=LOOPBACK`, `VRF=gVirtualRouterId`, `MTU=9100 (OVERLAY_RIF_DEFAULT_MTU)` |
| `sai_tunnel_api->create_tunnel()` | `SAI_OBJECT_TYPE_TUNNEL` (IPINIP) | `addDecapTunnel()` L849 | `TYPE=SAI_TUNNEL_TYPE_IPINIP`, `OVERLAY_IF=overlayIfId`, `UNDERLAY_IF=gUnderlayIfId`, `DECAP_ECN_MODE`, `DECAP_TTL_MODE`, `DECAP_DSCP_MODE`; 条件付き: `ENCAP_SRC_IP`, `ENCAP_ECN_MODE`, `DECAP_QOS_DSCP_TO_TC_MAP`, `DECAP_QOS_TC_TO_PRIORITY_GROUP_MAP` |
| `sai_tunnel_api->create_tunnel_term_table_entry()` | `SAI_OBJECT_TYPE_TUNNEL_TERM_TABLE_ENTRY` | `addDecapTunnelTermEntry()` L979 | `VR_ID=gVirtualRouterId`, `TYPE=P2P/P2MP/MP2MP`, `TUNNEL_TYPE=SAI_TUNNEL_TYPE_IPINIP`, `ACTION_TUNNEL_ID=tunnel_id`, `DST_IP`; 条件付き: `SRC_IP`, `SRC_IP_MASK`, `DST_IP_MASK` |

### QoS map OID の条件付き ASIC_DB push

- `decap_dscp_to_tc_map` が設定済みの場合: `gQosOrch->resolveTunnelQosMap()` で SAI OID を解決し `SAI_TUNNEL_ATTR_DECAP_QOS_DSCP_TO_TC_MAP` として `create_tunnel` 属性に含める (`tunneldecaporch.cpp` L834)
- `decap_tc_to_pg_map` が設定済みの場合: 同様に `SAI_TUNNEL_ATTR_DECAP_QOS_TC_TO_PRIORITY_GROUP_MAP` として含める (L842)
- `encap_tc_to_dscp_map` / `encap_tc_to_queue_map` は **SAI に直接 push されない**。OID を `tunnelTable` 内部キャッシュに保持し、MuxOrch が `TunnelDecapOrch::getQosMapId()` 経由で取得して MUX_CABLE 処理の SAI 書き込みに利用する

---

## 2. STATE_DB — STATE_TUNNEL_DECAP_TABLE / STATE_TUNNEL_DECAP_TERM_TABLE

### STATE_TUNNEL_DECAP_TABLE

| 操作 | トリガ | 書込経路 | 書込フィールド |
|------|-------|---------|--------------|
| SET (初回登録) | `addDecapTunnel()` 成功後 | `setDecapTunnelStatus()` → `stateTunnelDecapTable->set(tunnel_name, fv)` (L873, L1531) | `tunnel_type`, `dscp_mode`, `ecn_mode`, `encap_ecn_mode`, `ttl_mode`（空でない値のみ） |
| SET (フィールド更新) | 既存トンネルへの SET でフィールドが変化したとき | `setDecapTunnelStatus()` (L286) | 同上 |
| DEL | `removeDecapTunnel()` 実行時 | `removeDecapTunnelStatus()` → `stateTunnelDecapTable->del(tunnel_name)` (L1213, L1536) | — |

### STATE_TUNNEL_DECAP_TERM_TABLE

| 操作 | トリガ | 書込経路 | 書込フィールド |
|------|-------|---------|--------------|
| SET | `addDecapTunnelTermEntry()` 成功後 | `setDecapTunnelTermStatus()` → `stateTunnelDecapTermTable->set(tunnel_name\|dst_ip, fv)` (L998, L1560) | `term_type` (P2P/P2MP/MP2MP)、`src_ip`（P2P/MP2MP のみ）、`subnet_type`（サブネット decap 時のみ） |
| DEL | `removeDecapTunnelTermEntry()` 実行時 | `removeDecapTunnelTermStatus()` → `stateTunnelDecapTermTable->del(...)` (L1261, L1566) | — |

---

## 3. MuxOrch への間接 QoS 副次反映

`tunneldecaporch` は `encap_tc_to_dscp_map` / `encap_tc_to_queue_map` の OID を内部キャッシュ `tunnelTable` に保持し SAI には直接書かない。  
`MuxOrch` が `MUX_CABLE` SET 処理時 (`muxorch.cpp:2348-2377`) に以下を呼び出し、OID を自身の SAI 書き込みに利用する:

- `TunnelDecapOrch::getQosMapId(tunnelKey, "encap_tc_to_dscp_map", oid)` (`tunneldecaporch.cpp` L1450+)
- `TunnelDecapOrch::getQosMapId(tunnelKey, "encap_tc_to_queue_map", oid)`
- `TunnelDecapOrch::getDscpMode(tunnelKey)` — `dscp_mode` 文字列取得
- `TunnelDecapOrch::getDstIpAddresses(tunnelKey)` — decap term の dst IP 一覧取得

---

## 書込タイミングまとめ

```
TUNNEL SET (CONFIG_DB)
  └─ tunnelmgrd
       └─ APPL_DB APP_TUNNEL_DECAP_TABLE SET
            └─ tunneldecaporch (orchagent)
                 ├─ SAI create_router_interface → syncd → ASIC_DB (overlay loopback RIF, MTU=9100)
                 ├─ SAI create_tunnel → syncd → ASIC_DB (SAI_OBJECT_TYPE_TUNNEL, TYPE=IPINIP)
                 │     └─ 条件付き: DECAP_QOS_DSCP_TO_TC_MAP / DECAP_QOS_TC_TO_PRIORITY_GROUP_MAP
                 ├─ SAI create_tunnel_term_table_entry → syncd → ASIC_DB (P2P/P2MP/MP2MP term)
                 ├─ STATE_DB STATE_TUNNEL_DECAP_TABLE SET (tunnel_type/dscp_mode/ecn_mode/ttl_mode)
                 ├─ STATE_DB STATE_TUNNEL_DECAP_TERM_TABLE SET (term_type/src_ip/subnet_type)
                 └─ tunnelTable 内部キャッシュに encap QoS OID 保存
                      └─ MuxOrch が MUX_CABLE 処理時に getQosMapId() 参照
                           └─ MuxOrch SAI 書き込みに間接伝播 (muxorch.cpp:2348-2377)
```

---

## 証跡サマリ

| 書込先 | 経路 | コンポーネント | evidence |
|---|---|---|---|
| ASIC_DB (SAI_OBJECT_TYPE_ROUTER_INTERFACE) | `sai_router_intfs_api->create_router_interface()` → syncd | TunnelDecapOrch | `tunneldecaporch.cpp` L753 |
| ASIC_DB (SAI_OBJECT_TYPE_TUNNEL, IPINIP) | `sai_tunnel_api->create_tunnel()` → syncd | TunnelDecapOrch | `tunneldecaporch.cpp` L849 |
| ASIC_DB (SAI_OBJECT_TYPE_TUNNEL_TERM_TABLE_ENTRY) | `sai_tunnel_api->create_tunnel_term_table_entry()` → syncd | TunnelDecapOrch | `tunneldecaporch.cpp` L979 |
| STATE_DB `STATE_TUNNEL_DECAP_TABLE` | `stateTunnelDecapTable->set/del()` | TunnelDecapOrch | `tunneldecaporch.cpp` L1531, L1536 |
| STATE_DB `STATE_TUNNEL_DECAP_TERM_TABLE` | `stateTunnelDecapTermTable->set/del()` | TunnelDecapOrch | `tunneldecaporch.cpp` L1560, L1566 |
| MuxOrch SAI QoS 書込 (間接) | `getQosMapId()` 経由で OID 伝播 | MuxOrch | `muxorch.cpp:2348-2377` |
