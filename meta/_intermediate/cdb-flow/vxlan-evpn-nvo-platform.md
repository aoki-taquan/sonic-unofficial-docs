# vxlan-evpn-nvo — Phase H Platform Differences

Source: `sonic-swss/orchagent/vxlanorch.cpp`

## 1. EVPN 対応 ASIC 差: P2MP vs P2P トンネルモード

`VXLAN_EVPN_NVO` が参照する VXLAN_TUNNEL の実際の ASIC 動作は、`VxlanTunnelOrch` 初期化時に行う SAI ケーパビリティクエリで決定される。

### 判定ロジック (vxlanorch.cpp:1256-1274)

```cpp
status = sai_query_attribute_enum_values_capability(gSwitchId, SAI_OBJECT_TYPE_TUNNEL,
                                                    SAI_TUNNEL_ATTR_PEER_MODE, &values);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_WARN("Unable to get supported tunnel peer modes. Defaulting to P2P");
    is_dip_tunnel_supported = true;  // P2P (DIP) モードへ fallback
}
else
{
    is_dip_tunnel_supported = false;
    for (uint32_t idx = 0; idx < values.count; idx++)
    {
        if (values.list[idx] == SAI_TUNNEL_PEER_MODE_P2P)
        {
            is_dip_tunnel_supported = true;
            break;
        }
    }
}
```

- SAI ケーパビリティクエリが失敗した場合（未対応 ASIC ドライバ等）: `is_dip_tunnel_supported = true` (P2P モード) に自動 fallback。
- `SAI_TUNNEL_PEER_MODE_P2P` が列挙されれば DIP トンネル（P2P）サポートあり。
- P2MP のみが返された場合: `is_dip_tunnel_supported = false` → P2MP モードで動作。

## 2. EVPN NVO の動作に対する ASIC 差の影響

`VXLAN_EVPN_NVO` テーブルの `EvpnNvoOrch` 自体に ASIC 依存分岐はない。ただし、NVO が参照する VTEP（`source_vtep` → `VXLAN_TUNNEL`）の動作が以下の通り分岐する。

### P2P モード (DIP トンネルサポートあり)

- EVPN ルート受信時にリモート VTEP ごとに個別の P2P DIP トンネルを動的生成。
- `addTunnelUser()` (vxlanorch.cpp:1701-1724): `createDynamicDIPTunnel(remote_vtep, usr)` を呼び出し、SAI `create_tunnel()` を `SAI_TUNNEL_PEER_MODE_P2P` + `SAI_TUNNEL_ATTR_ENCAP_DST_IP` で実行。
- FDB エントリは DIP トンネルポート単位で管理。
- SIP トンネル HW 削除は全 DIP トンネルの削除完了まで延期 (`del_tnl_hw_pending`)。

### P2MP モード (DIP トンネルサポートなし)

- `addTunnelUser()` (vxlanorch.cpp:1701-1704): DIP トンネルを生成せず、リモート VTEP の IP 参照カウントのみ更新。
- 単一の P2MP SIP トンネルブリッジポートを全リモート VTEP で共有。
- FDB/MAC フラッディングは P2MP トンネルポート + IMET ルートの L2MC グループメンバーとして実現。
  (vxlanorch.cpp コメント: `"P2MP scenario where P2MP tunnel port is used for FDB learning"`)
- SIP トンネル HW 削除はリモート参照カウントが 0 かつ `del_tnl_hw_pending` の場合に即時実行可能。

## 3. EVPN 動的 DIP トンネルの SAI 作成 (create_tunnel, vxlanorch.cpp:356-370)

```cpp
if ((dst_ip != nullptr) && p2p)
{
    attr.value.s32 = SAI_TUNNEL_PEER_MODE_P2P;
    // SAI_TUNNEL_ATTR_ENCAP_DST_IP を追加
}
else
{
    attr.value.s32 = SAI_TUNNEL_PEER_MODE_P2MP;
    // DST_IP 属性なし
}
```

- EVPN 動的 DIP トンネル (`TNL_CREATION_SRC_EVPN`, dst_ip 非ゼロ): `p2p = true` → `SAI_TUNNEL_PEER_MODE_P2P` で SAI 作成。(vxlanorch.cpp:903)
- CLI 静的トンネル (`TNL_CREATION_SRC_CLI`, dst_ip 非ゼロ): `p2p = false` → `SAI_TUNNEL_PEER_MODE_P2MP` で SAI 作成。

## 4. SmartSwitch / DPU 差異

`vxlanorch.cpp` に SmartSwitch DPU 固有の分岐コードは存在しない。DPU 側の VXLAN/EVPN 処理は別のオーバーレイスタックが担当する可能性があるが、現在の orchagent 実装では NPU 通常モードのみが対象。`VXLAN_EVPN_NVO` テーブルも NPU 向けのみ定義されている。

## 5. まとめ表

| 差異ポイント | P2P (DIP サポートあり) | P2MP (DIP サポートなし) |
|---|---|---|
| SAI クエリ失敗時 | fallback で P2P | — |
| リモート VTEP ごとのトンネル | 動的生成 (DIP トンネル) | 生成しない |
| SIP トンネル削除タイミング | DIP カウント 0 待ち | 即時可能 |
| ブリッジポート | VTEP ごと個別 | SIP で共有 |
| FDB/flooding | DIP トンネルポート経由 | P2MP + L2MC グループ経由 |
| EVPN DIP トンネル SAI mode | `SAI_TUNNEL_PEER_MODE_P2P` | 使用しない |
| CLI 静的 tunnel SAI mode | `SAI_TUNNEL_PEER_MODE_P2MP` | 同左 |
| SmartSwitch DPU | コード分岐なし | 同左 |
