# TUNNEL (IPinIP / MuxTunnel0) — Phase H: プラットフォーム差

生成日: 2026-05-16  
対象ページ: `docs/reference/config-db/tunnel.md`  
evidence sources:
  - `sonic-swss/orchagent/tunneldecaporch.cpp`
  - `sonic-swss/orchagent/tunneldecaporch.h`
  - `sonic-swss/orchagent/muxorch.cpp`
  - `sonic-swss/orchagent/orch.h`

---

## 調査方針

`docs/reference/config-db/ipinip-tunnel.md` は存在しない。近似 slug `docs/reference/config-db/tunnel.md` が IPinIP / MuxTunnel 関連ページであるため、当該ファイルへ `<!-- platform -->` ブロックを適用した。

本ファイルは `tunneldecaporch.cpp` 起点の Phase H (プラットフォーム差) 調査記録として独立して保存する。なお `tunnel-platform.md`（Phase H 前の調査記録）も参照可。

---

## H-1. `ecn_mode` / `encap_ecn_mode` — SAI create-only 属性（全プラットフォーム共通）

`SAI_TUNNEL_ATTR_DECAP_ECN_MODE` と `SAI_TUNNEL_ATTR_ENCAP_ECN_MODE` は SAI 仕様上 **create-only** 属性。`tunneldecaporch.cpp` では既存トンネルへの変更 SET をガードし、`valid=false` で SET 全体を無効化する。

```cpp
// tunneldecaporch.cpp L177-182
if (exists)
{
    SWSS_LOG_WARN("Skip setting ecn_mode since the SAI attribute SAI_TUNNEL_ATTR_DECAP_ECN_MODE is create only");
    valid = false;
    break;
}

// tunneldecaporch.cpp L193-198
if (exists)
{
    SWSS_LOG_NOTICE("Skip setting encap_ecn_mode since the SAI attribute SAI_TUNNEL_ATTR_ENCAP_ECN_MODE is create only");
    valid = false;
    break;
}
```

- Broadcom / Mellanox 共通。ベンダー固有分岐なし。
- 変更には `TUNNEL|MuxTunnel0` DEL → 再 SET が必要。

---

## H-2. Dual-ToR QoS DSCP リマッピング — SAI capability 依存

Dual-ToR 環境でのみ有効な QoS リマッピングフィールド。SAI spec 202012 以降に追加された属性を使用するため、古い SAI 実装では非サポートとなる可能性がある。

| フィールド | SAI 属性 | 担当 orch | 備考 |
|---|---|---|---|
| `decap_dscp_to_tc_map` | `SAI_TUNNEL_ATTR_DECAP_QOS_DSCP_TO_TC_MAP` | tunneldecaporch | decap 時 DSCP→TC 再マッピング |
| `decap_tc_to_pg_map` | `SAI_TUNNEL_ATTR_DECAP_QOS_TC_TO_PRIORITY_GROUP_MAP` | tunneldecaporch | decap 時 TC→PG 再マッピング |
| `encap_tc_to_dscp_map` | `SAI_TUNNEL_ATTR_ENCAP_QOS_TC_AND_COLOR_TO_DSCP_MAP` | muxorch 経由 | encap 時 TC+Color→DSCP 書換 |
| `encap_tc_to_queue_map` | `SAI_TUNNEL_ATTR_ENCAP_QOS_TC_TO_QUEUE_MAP` | muxorch 経由 | encap 時 TC→Queue 再マッピング |

encap 系 2 フィールドは tunneldecaporch が SAI に直接 push せず、OID を内部キャッシュ (`tunnelTable`) に保持し MuxOrch が `getQosMapId()` 経由で取得して使用する。

`dscp_mode=uniform` では外側 DSCP が内側にコピーされるため、リマッピングの効果が相殺される。QoS リマッピングを有効化するには `dscp_mode=pipe` が前提条件。

evidence: `tunneldecaporch.cpp` L831-845 (`SAI_TUNNEL_ATTR_DECAP_QOS_*`); `muxorch.cpp` L2367, L2374 (`getQosMapId()`); `tunneldecaporch.cpp` L257, L272 (OID キャッシュ保持)

---

## H-3. Mellanox / Broadcom の明示的なコード分岐なし

`orch.h` に `MLNX_PLATFORM_SUBSTRING = "mellanox"`, `BRCM_PLATFORM_SUBSTRING = "broadcom"` が定義されているが、`tunneldecaporch.cpp` / `tunneldecaporch.h` 内でこれらを参照する分岐は**存在しない**。

プラットフォーム差は SAI API の戻り値（`SAI_STATUS_NOT_SUPPORTED`, `SAI_STATUS_ATTR_NOT_SUPPORTED_0` 等）でのみ現れ、`handleSaiCreateStatus()` / `handleSaiSetStatus()` でハンドリングされる。

evidence: `tunneldecaporch.cpp` 全体をスキャン → `MLNX_PLATFORM_SUBSTRING` / `BRCM_PLATFORM_SUBSTRING` ヒットなし

---

## H-4. overlay RIF MTU のハードコード

```cpp
// tunneldecaporch.cpp L14
#define OVERLAY_RIF_DEFAULT_MTU 9100

// tunneldecaporch.cpp L749-750
overlay_intf_attr.id = SAI_ROUTER_INTERFACE_ATTR_MTU;
overlay_intf_attr.value.u32 = OVERLAY_RIF_DEFAULT_MTU;
```

CONFIG_DB から変更できない。全プラットフォームで 9100 固定。ベンダー SAI が 9100 以下の MTU 制約を持つ場合でも同値を送信する。

---

## H-5. P2P / P2MP / MP2MP decap term — SAI capability 事前クエリなし

`tunneldecaporch` は decap term type の SAI capability を事前クエリせず直接 `create_tunnel_term_table_entry()` を呼ぶ。

- **P2P**: Dual-ToR MuxTunnel の decap terminator。`src_ip = PEER_SWITCH.address_ipv4`。
- **P2MP**: `src_ip` 未設定時のデフォルト。ワイルドカード decap（全 IPinIP を受け入れ）。
- **MP2MP**: Subnet decap (`IPINIP_SUBNET` / `IPINIP_SUBNET_V6`) 専用。`is_subnet_decap_term && term_type != MP2MP` はエラー（`tunneldecaporch.cpp` L446-448`）。

非対応プラットフォームでは SAI エラーが返り、`handleSaiCreateStatus()` でタスク失敗として処理される（リトライなし）。

---

## H-6. `ttl_mode` / `dscp_mode` — 既存トンネルへの変更可否

`ecn_mode` と異なり、`ttl_mode` / `dscp_mode` は create-only ではなく `sai_tunnel_api->set_tunnel_attribute()` で変更可能。ただし、ベンダー SAI 実装によっては `SAI_STATUS_NOT_SUPPORTED` を返す場合があり、コードは LOG_ERROR のみでリトライなし。

evidence: `tunneldecaporch.cpp` L1017-1062 (`setTunnelAttribute()`)

---

## まとめ

| 条件 | 影響フィールド | 挙動 | evidence |
|---|---|---|---|
| 全プラットフォーム共通 | `ecn_mode`, `encap_ecn_mode` | SAI create-only。既存トンネルへの変更 SET で SET 全体無効化 | `tunneldecaporch.cpp` L179, L195 |
| SAI spec 202012 未満の古い SAI | `decap_dscp_to_tc_map` 等 4 フィールド | QoS リマッピング SAI 属性が非サポートとなる可能性あり | SAI spec (202205 対象) |
| 全プラットフォーム共通 | overlay RIF MTU | 固定値 9100 を SAI に送信。CONFIG_DB 変更不可 | `tunneldecaporch.cpp` L14, L750 |
| 全プラットフォーム共通 | `ttl_mode`, `dscp_mode` | 既存トンネルへの変更は `set_tunnel_attribute()` 経由で可能。SAI 実装依存で失敗することもある | `tunneldecaporch.cpp` L1050 |
| Dual-ToR 環境のみ | `encap_tc_to_dscp_map`, `encap_tc_to_queue_map` | MuxOrch 経由で SAI push。tunneldecaporch は内部キャッシュ保持のみ | `tunneldecaporch.cpp` L257, L272 |
| 非対応 SAI 実装 | P2P/P2MP/MP2MP decap term | SAI create_tunnel_term_table_entry 失敗でリトライなし | `tunneldecaporch.cpp` L979 |
