# TUNNEL_ENCAP_TABLE — Phase B 書込み順依存スキャンノート

対象テーブル: `FIXED_TUNNEL_TABLE` (APPL_DB P4RT_TABLE)
Consumer: `GreTunnelManager` (`sonic-swss/orchagent/p4orch/gre_tunnel_manager.cpp`)
スキャン範囲: `validateGreTunnelAppDbEntry()`, `createGreTunnels()`, `deleteGreTunnels()`, `drain()` 全行精読

---

## 検出した順序依存・タイミング依存

### 1. FIXED_ROUTER_INTERFACE_TABLE 先行必須（SET 時）

`validateGreTunnelAppDbEntry()` (`gre_tunnel_manager.cpp:129-135`) が `m_p4OidMapper->getOID(SAI_OBJECT_TYPE_ROUTER_INTERFACE, router_interface_key, &entry.underlay_if_oid)` を呼ぶ。
`param/router_interface_id` が指す RIF エントリが centralized mapper に未登録の場合は `SWSS_RC_NOT_FOUND` を返してトンネル SET が失敗する。
**retry はなく即時エラー**（`LOG_ERROR_AND_RETURN`）。

- evidence: `gre_tunnel_manager.cpp:127-135`

### 2. FIXED_NEIGHBOR_TABLE 先行必須（SET 時）

同じく `validateGreTunnelAppDbEntry()` (`gre_tunnel_manager.cpp:139-148`) が `m_p4OidMapper->existsOID(SAI_OBJECT_TYPE_NEIGHBOR_ENTRY, neighbor_key)` を呼ぶ。
`neighbor_key` は `router_interface_id` + `encap_dst_ip` (= neighbor_id) で生成される。
neighbor エントリが未登録の場合は `SWSS_RC_NOT_FOUND` を返してトンネル SET が失敗する。
**retry はなく即時エラー**。

- evidence: `gre_tunnel_manager.cpp:137-148`

### 3. FIXED_TUNNEL_TABLE DEL は参照カウント = 0 が必須

`validateGreTunnelAppDbEntry()` DEL パス (`gre_tunnel_manager.cpp:160-173`) が `m_p4OidMapper->getRefCount(SAI_OBJECT_TYPE_TUNNEL, entry.tunnel_key, &ref_count)` を呼ぶ。
`FIXED_NEXTHOP_TABLE` エントリが `param/tunnel_id` でこのトンネルを参照している間は ref_count > 0 となり、`SWSS_RC_INVALID_PARAM` でトンネル DEL が失敗する。
**retry はなく即時エラー**。

- evidence: `gre_tunnel_manager.cpp:160-173`、`createGreTunnels()` での `increaseRefCount` (`gre_tunnel_manager.cpp:445-451`)

### 4. SAI Bulk API は STOP_ON_ERROR モード

`createGreTunnels()` (`gre_tunnel_manager.cpp:431`) は `SAI_BULK_OP_ERROR_MODE_STOP_ON_ERROR` を指定する。
バッチ内の先行エントリが SAI エラーになると後続エントリは処理されず `SWSS_RC_NOT_EXECUTED` が返る (`gre_tunnel_manager.cpp:269-272`)。
P4RT controller が複数トンネルを同時投入する場合は SAI エラー発生時に全体が止まる点に注意。

- evidence: `gre_tunnel_manager.cpp:269-272, 431`

### 5. Update (SET on existing) は非サポート

既存トンネルキーへの再 SET は `drain()` (`gre_tunnel_manager.cpp:279`) で `SWSS_RC_UNIMPLEMENTED` を返す。
`router_interface_id` / `encap_src_ip` / `encap_dst_ip` の変更には DEL → SET の順が必要。
DEL 時は依存 #3 の参照カウント制約が適用されるため、参照 nexthop を先に DEL する必要がある。

- evidence: `gre_tunnel_manager.cpp:279-282`

---

## 正常系の書込み順序（推奨）

SET 時:
1. FIXED_ROUTER_INTERFACE_TABLE  SET  (router_interface_id)
2. FIXED_NEIGHBOR_TABLE          SET  (router_interface_id + encap_dst_ip)
3. FIXED_TUNNEL_TABLE            SET  (本テーブル)
4. FIXED_NEXTHOP_TABLE           SET  (param/tunnel_id = 本エントリ参照)

DEL 時:
1. FIXED_NEXTHOP_TABLE           DEL  (参照カウントを減らす)
2. FIXED_TUNNEL_TABLE            DEL  (ref_count = 0 を確認してから)
