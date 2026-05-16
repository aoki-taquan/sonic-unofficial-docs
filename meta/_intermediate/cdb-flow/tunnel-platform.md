# TUNNEL — Phase H: プラットフォーム差 (SAI capability / vendor)

生成日: 2026-05-15
対象ページ: `docs/reference/config-db/tunnel.md`
evidence sources:
  - `sonic-swss/orchagent/tunneldecaporch.cpp`
  - `sonic-swss/orchagent/muxorch.cpp`
  - `sonic-swss/orchagent/vxlanorch.cpp`
  - `sonic-swss/orchagent/switchorch.cpp`
  - `SONiC/doc/qos/tunnel_dscp_remapping.md`
  - `SONiC/doc/dualtor/dualtor_active_standby_hld.md`

---

## H-1. `ecn_mode` / `encap_ecn_mode` — SAI create-only 属性

`SAI_TUNNEL_ATTR_DECAP_ECN_MODE` と `SAI_TUNNEL_ATTR_ENCAP_ECN_MODE` は SAI 標準で **create-only** フラグを持つ属性である。この制約はベンダー SAI 実装に関わらず、SAI 仕様上の共通制約として `tunneldecaporch.cpp` で明示的にハンドルされる。

```
// tunneldecaporch.cpp L179
SWSS_LOG_WARN("Skip setting ecn_mode since the SAI attribute SAI_TUNNEL_ATTR_DECAP_ECN_MODE is create only");

// tunneldecaporch.cpp L195
SWSS_LOG_NOTICE("Skip setting encap_ecn_mode since the SAI attribute SAI_TUNNEL_ATTR_ENCAP_ECN_MODE is create only");
```

- 既存トンネルへの `ecn_mode` / `encap_ecn_mode` の変更 SET は **SET 全体が無効化** (valid=false) される。
- 変更には `TUNNEL|MuxTunnel0` の DEL 後に再 SET が必要。
- この動作は Broadcom / Mellanox 問わず共通。

---

## H-2. Dual-ToR QoS リマッピング — `dscp_mode=pipe` 時のみ有効

Dual-ToR (`DEVICE_METADATA.subtype = "DualToR"`) 環境でのみ、QoS リマッピング用の4フィールドが有効に機能する。

| フィールド | SAI 属性 | 担当orch | 用途 |
|---|---|---|---|
| `decap_dscp_to_tc_map` | `SAI_TUNNEL_ATTR_DECAP_QOS_DSCP_TO_TC_MAP` | tunneldecaporch | デカプセル時 DSCP→TC 再マッピング |
| `decap_tc_to_pg_map` | `SAI_TUNNEL_ATTR_DECAP_QOS_TC_TO_PRIORITY_GROUP_MAP` | tunneldecaporch | デカプセル時 TC→PG 再マッピング |
| `encap_tc_to_dscp_map` (= `encap_tc_color_to_dscp_map`) | `SAI_TUNNEL_ATTR_ENCAP_QOS_TC_AND_COLOR_TO_DSCP_MAP` | muxorch | カプセル時 TC+Color→DSCP 書き換え |
| `encap_tc_to_queue_map` | `SAI_TUNNEL_ATTR_ENCAP_QOS_TC_TO_QUEUE_MAP` | muxorch | カプセル時 TC→Queue 再マッピング |

これらの SAI 属性は SAI spec `202012` 以降 (branch 202205 対象) に追加された。非対応の古い SAI 実装ではトンネル CREATE 時に `SAI_STATUS_NOT_SUPPORTED` または `SAI_STATUS_ATTR_NOT_SUPPORTED_0` が返る可能性がある。

この機能を有効にするには `dscp_mode` を `pipe` にする必要がある (HLD ドキュメントより)。`uniform` モードではカプセル外側の DSCP が内側にコピーされるため、リマッピングの効果が相殺される。

evidence: `SONiC/doc/qos/tunnel_dscp_remapping.md`, `muxorch.cpp L308-321`, `tunneldecaporch.cpp L831-845`

---

## H-3. SAI Tunnel Peer Mode — P2P vs P2MP の SAI capability クエリ (VxLAN 系)

VXLAN_TUNNEL (vxlanorch) は起動時に SAI に `SAI_TUNNEL_ATTR_PEER_MODE` の対応 enum を問い合わせる:

```cpp
// vxlanorch.cpp L1256-1274
sai_query_attribute_enum_values_capability(gSwitchId, SAI_OBJECT_TYPE_TUNNEL,
                                            SAI_TUNNEL_ATTR_PEER_MODE, &values);
```

- **成功**: `SAI_TUNNEL_PEER_MODE_P2P` が返値リストにあれば `is_dip_tunnel_supported = true` (P2P + P2MP 両対応)。
- **失敗**: クエリ非対応のベンダー SAI の場合 `SWSS_LOG_WARN` を出力し、`is_dip_tunnel_supported = true` にデフォルト設定 (P2P サポートと仮定)。

TUNNEL テーブル (MuxTunnel0) の `tunneldecaporch` / `muxorch` は P2P を固定使用し、この capability クエリは行わない (vxlanorch 固有の処理)。ただし、Dual-ToR の decap terminator 構成で P2P/P2MP の使い分けが影響する:
- `MuxTunnel` の decap term: `P2P` (src_ip = peer Loopback 指定)
- 通常 IPinIP トンネルの decap term: `P2MP` (src_ip なし)

evidence: `vxlanorch.cpp L1256-1274`, `SONiC/doc/qos/tunnel_dscp_remapping.md L325-326`

---

## H-4. VxLAN UDP Source Port セキュリティ — Broadcom vs 他ベンダー

`switchorch` の `setSwitchTunnelVxlanParams()` は `SAI_OBJECT_TYPE_SWITCH_TUNNEL` の `SAI_SWITCH_TUNNEL_ATTR_VXLAN_UDP_SPORT_SECURITY` を capability クエリしてから設定する:

```cpp
// switchorch.cpp L526-538
sai_query_attribute_capability(gSwitchId, SAI_OBJECT_TYPE_SWITCH_TUNNEL,
                                SAI_SWITCH_TUNNEL_ATTR_VXLAN_UDP_SPORT_SECURITY, &capability);
if (capability.create_implemented) {
    // 属性を SET する
} else {
    SWSS_LOG_NOTICE("VXLAN UDP sport security attribute not supported for switch tunnel creation");
}
```

SWITCH_TABLE の `vxlan_sport_security` 設定が非対応の SAI 実装では静かにスキップされる。このフィールドは TUNNEL テーブルには無いが、VXLAN Tunnel との間接的な挙動差に影響する。

evidence: `switchorch.cpp L508-552`

---

## H-5. `ttl_mode` / `dscp_mode` の SET 後変更可否

`ttl_mode` と `dscp_mode` は create-only ではなく、既存トンネルへの `setTunnelAttribute()` で変更可能 (`sai_tunnel_api->set_tunnel_attribute()`)。ただし、ベンダー SAI 実装によっては `SAI_STATUS_NOT_SUPPORTED` を返す場合がある。コードは `handleSaiSetStatus()` でエラー処理するが、ログレベルは ERROR のみでリトライなし。

```cpp
// tunneldecaporch.cpp L1050-1058
sai_status_t status = sai_tunnel_api->set_tunnel_attribute(existing_tunnel_id, &attr);
if (status != SAI_STATUS_SUCCESS) {
    SWSS_LOG_ERROR("Failed to set attribute %s with value %s", field.c_str(), value.c_str());
    ...
}
```

evidence: `tunneldecaporch.cpp L1017-1062`

---

## H-6. Broadcom T1 スイッチ固有考慮点

Broadcom T1 (Tomahawk 系) における TUNNEL テーブル利用のコード上の明示的な分岐はソース内に見当たらない。ただし以下の実装上の注意点がある:

1. **overlay RIF (loopback) の MTU ハードコード**: `OVERLAY_RIF_DEFAULT_MTU = 9100` がすべてのプラットフォームで固定使用される (`tunneldecaporch.cpp L750`)。Broadcom の最大 MTU 制約がある場合も同値が送信される。
2. **SAI create-only 属性**: Broadcom SAI は ECN 系属性を create-only として実装しているため、デプロイ後の `ecn_mode` 変更は DEL/SET が必要。
3. **decap term sharing**: `tunneldecaporch` が P2MP decap term と `muxorch` の P2P decap term を両立するには同一 `dst_ip` でも別 terminator エントリを作成する設計になっている (`SONiC/doc/qos/tunnel_dscp_remapping.md L322-326`)。

---

## まとめ

| プラットフォーム条件 | 影響フィールド | 挙動 | evidence |
|---|---|---|---|
| 全プラットフォーム共通 | `ecn_mode`, `encap_ecn_mode` | SAI create-only。既存トンネルへの変更 SET で SET 全体無効化 | tunneldecaporch.cpp L179, L195 |
| SAI spec 202012 未満の古い SAI | `decap_dscp_to_tc_map`, `decap_tc_to_pg_map`, `encap_tc_to_dscp_map`, `encap_tc_to_queue_map` | QoS リマッピング SAI 属性が非サポートとなる可能性あり | SONiC HLD (202205) |
| SAI capability クエリ非対応 (VxLAN peer mode) | VXLAN tunnel P2P/P2MP 選択 | P2P サポートと仮定してデフォルト動作 | vxlanorch.cpp L1260 |
| SAI capability クエリ非対応 (VxLAN sport security) | VxLAN UDP sport security | 静かにスキップ (NOTICE ログ) | switchorch.cpp L536 |
| 全プラットフォーム共通 | `ttl_mode`, `dscp_mode` | 既存トンネルへの変更可能。SAI 実装依存で失敗することもある | tunneldecaporch.cpp L1050 |
| 全プラットフォーム共通 | overlay RIF MTU | 固定値 9100 を SAI に送信 | tunneldecaporch.cpp L750 |
