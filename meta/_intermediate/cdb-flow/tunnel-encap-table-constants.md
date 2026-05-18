# TUNNEL_ENCAP_TABLE — Phase E ハードコード定数スキャンノート

対象テーブル: `FIXED_TUNNEL_TABLE` (APPL_DB P4RT_TABLE)
Consumer: `GreTunnelManager` (`sonic-swss/orchagent/p4orch/gre_tunnel_manager.cpp`)
スキャン範囲: `p4orch_util.h`, `gre_tunnel_manager.cpp` 全行精読

---

## アクション文字列定数 (`p4orch_util.h:111`)

- `kTunnelAction = "mark_for_p2p_tunnel_encap"` — 唯一受け入れられるアクション名。`validateGreTunnelAppDbEntry()` (L83-87) で比較され、不一致は即 `SWSS_RC_INVALID_PARAM`。

## フィールド名定数 (`p4orch_util.h`)

- `kTunnelId = "tunnel_id"` (L44) — match フィールド末尾部
- `kRouterInterfaceId = "router_interface_id"` (L28) — `param/router_interface_id` の末尾部
- `kEncapSrcIp = "encap_src_ip"` (L105) — `param/encap_src_ip` の末尾部
- `kEncapDstIp = "encap_dst_ip"` (L106) — `param/encap_dst_ip` の末尾部
- `kControllerMetadata = "controller_metadata"` (L92) — ホワイトリスト外だが例外的に無視
- `kMatchPrefix = "match"` (L84) — フィールド名プレフィックス
- `kActionParamPrefix = "param"` (L85) — フィールド名プレフィックス
- `kFieldDelimiter = '/'` (L80) — `match/`・`param/` のデリミタ文字

## テーブル名定数 (`schema.h:72`)

- `APP_P4RT_TUNNEL_TABLE_NAME = "FIXED_TUNNEL_TABLE"` — APPL_DB キー生成に使用

## SAI ハードコード定数 (`gre_tunnel_manager.cpp`)

- `SAI_TUNNEL_TYPE_IPINIP_GRE` (L42) — トンネル種別、`prepareSaiAttrs()` でハードコード
- `SAI_TUNNEL_PEER_MODE_P2P` (L46) — ピアモード、同上
- `SAI_BULK_OP_ERROR_MODE_STOP_ON_ERROR` (L431, L493) — Bulk SAI 呼び出しモード
- `gUnderlayIfId` (L420) — `SAI_TUNNEL_ATTR_OVERLAY_INTERFACE` の代用値（グローバルループバック RIF）
