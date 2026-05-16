# TUNNEL — 副次 DB 書込 (Phase F)

ソース: `sonic-swss/orchagent/tunneldecaporch.cpp`

---

## 1. ASIC_DB — SAI tunnel オブジェクト群

`tunneldecaporch` が `addDecapTunnel()` を呼ぶと、syncd 経由で ASIC_DB に以下の SAI オブジェクトが生成される。

| SAI API 呼び出し | 生成オブジェクト種別 | トリガ | SAI 属性 (主要) |
|----------------|------------------|-------|--------------|
| `sai_router_intfs_api->create_router_interface()` | `SAI_OBJECT_TYPE_ROUTER_INTERFACE` (overlay loopback) | `addDecapTunnel()` L753 | `TYPE=LOOPBACK`, `VRF=gVirtualRouterId`, `MTU=9100` |
| `sai_tunnel_api->create_tunnel()` | `SAI_OBJECT_TYPE_TUNNEL` (IPINIP) | `addDecapTunnel()` L849 | `TYPE=SAI_TUNNEL_TYPE_IPINIP`, `OVERLAY_IF=overlayIfId`, `UNDERLAY_IF=gUnderlayIfId`, `DECAP_ECN_MODE`, `DECAP_TTL_MODE`, `DECAP_DSCP_MODE`, 条件付きで `ENCAP_SRC_IP`, `ENCAP_ECN_MODE`, `DECAP_QOS_DSCP_TO_TC_MAP`, `DECAP_QOS_TC_TO_PRIORITY_GROUP_MAP` |
| `sai_tunnel_api->create_tunnel_term_table_entry()` | `SAI_OBJECT_TYPE_TUNNEL_TERM_TABLE_ENTRY` | `addDecapTunnelTermEntry()` L979 | `VR_ID=gVirtualRouterId`, `TYPE=P2P/P2MP/MP2MP`, `TUNNEL_TYPE=IPINIP`, `ACTION_TUNNEL_ID=tunnel_id`, `DST_IP`, 条件付きで `SRC_IP`, `SRC_IP_MASK`, `DST_IP_MASK` |

### QoS map OID の副次伝播

`decap_dscp_to_tc_map` / `decap_tc_to_pg_map` が設定されている場合:

- `gQosOrch->resolveTunnelQosMap()` で CONFIG_DB の map 名 → SAI OID に解決
- OID が `SAI_NULL_OBJECT_ID` でなければ `SAI_TUNNEL_ATTR_DECAP_QOS_DSCP_TO_TC_MAP` / `SAI_TUNNEL_ATTR_DECAP_QOS_TC_TO_PRIORITY_GROUP_MAP` として `create_tunnel` に含める

`encap_tc_to_dscp_map` / `encap_tc_to_queue_map` は **SAI に直接 push されない**。OID を `tunnelTable[key].encap_tc_to_dscp_map_id` / `tunnelTable[key].encap_tc_to_queue_map_id` に記録し、`MuxOrch` が `TunnelDecapOrch::getQosMapId()` 経由で取得して自身の SAI 書き込みに使う。

---

## 2. STATE_DB — STATE_TUNNEL_DECAP_TABLE / STATE_TUNNEL_DECAP_TERM_TABLE

### STATE_TUNNEL_DECAP_TABLE

| 操作 | トリガ | 書込経路 | 書込フィールド |
|------|-------|---------|--------------|
| SET (初回登録) | `addDecapTunnel()` 成功後 | `setDecapTunnelStatus()` → `stateTunnelDecapTable->set(tunnel_name, fv)` (L873) | `tunnel_type`, `dscp_mode`, `ecn_mode`, `encap_ecn_mode`, `ttl_mode`（空でない値のみ） |
| SET (フィールド更新) | 既存トンネルへの SET でフィールドが変化したとき | `setDecapTunnelStatus()` (L286) | 同上（ミラー済みフィールド一致ログ: `"synchronised in STATE_DB"` L287） |
| DEL | トンネル削除時 (`removeDecapTunnel()`) | `removeDecapTunnelStatus()` → `stateTunnelDecapTable->del(tunnel_name)` (L1536) | — |

### STATE_TUNNEL_DECAP_TERM_TABLE

| 操作 | トリガ | 書込経路 | 書込フィールド |
|------|-------|---------|--------------|
| SET | `addDecapTunnelTermEntry()` 成功後 | `setDecapTunnelTermStatus()` → `stateTunnelDecapTermTable->set(tunnel_name|dst_ip, fv)` (L1560) | `term_type` (P2P/P2MP/MP2MP)、`src_ip`（P2P/MP2MP のみ）、`subnet_type`（サブネット decap 時のみ） |
| DEL | decap term 削除時 | `removeDecapTunnelTermStatus()` → `stateTunnelDecapTermTable->del(...)` (L1566) | — |

---

## 3. MuxOrch への間接 QoS 副次反映

`tunneldecaporch` は `encap_tc_to_dscp_map` / `encap_tc_to_queue_map` の OID を内部キャッシュ `tunnelTable` に保持し SAI へは直接書かない。  
`MuxOrch` が `MUX_CABLE` SET 処理時に以下を呼び出し、この OID を自身の SAI 書き込みに利用する:

- `TunnelDecapOrch::getQosMapId(tunnelKey, "encap_tc_to_dscp_map", oid)`
- `TunnelDecapOrch::getQosMapId(tunnelKey, "encap_tc_to_queue_map", oid)`
- `TunnelDecapOrch::getDscpMode(tunnelKey)` — `dscp_mode` 文字列取得
- `TunnelDecapOrch::getDstIpAddresses(tunnelKey)` — decap term の dst IP 一覧取得

これにより TUNNEL テーブルの QoS map 設定は **MuxOrch 経由で Mux Cable の SAI QoS 設定に伝播**する（`muxorch.cpp:2348-2377`）。

---

## 書込タイミングまとめ

```
TUNNEL SET (CONFIG_DB)
  └─ tunnelmgrd
       └─ APPL_DB APP_TUNNEL_DECAP_TABLE SET
            └─ tunneldecaporch (orchagent)
                 ├─ SAI create_router_interface → syncd → ASIC_DB (overlay loopback RIF)
                 ├─ SAI create_tunnel → syncd → ASIC_DB (SAI_OBJECT_TYPE_TUNNEL IPINIP)
                 │     └─ QoS map OID 条件付き付与 (decap_dscp_to_tc / decap_tc_to_pg)
                 ├─ SAI create_tunnel_term_table_entry → syncd → ASIC_DB (decap term)
                 ├─ STATE_DB STATE_TUNNEL_DECAP_TABLE SET (tunnel_type/dscp/ecn/ttl)
                 ├─ STATE_DB STATE_TUNNEL_DECAP_TERM_TABLE SET (term_type/src_ip)
                 └─ tunnelTable キャッシュに encap QoS OID 保存
                      └─ MuxOrch が MUX_CABLE 処理時に getQosMapId() 参照
                           └─ MuxOrch SAI 書き込みに伝播 (間接副次効果)
```
