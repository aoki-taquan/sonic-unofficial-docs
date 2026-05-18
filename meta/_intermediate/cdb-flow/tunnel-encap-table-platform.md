# tunnel-encap-table platform 調査ノート (Phase H)

調査対象: `TUNNEL_ENCAP_TABLE` (`APPL_DB:P4RT_TABLE:FIXED_TUNNEL_TABLE`)
調査ファイル:
- `orchagent/p4orch/gre_tunnel_manager.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `orchagent/p4orch/gre_tunnel_manager.h` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `orchagent/p4orch/p4orch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## 結論サマリ

### P4RT 対応スイッチのみ動作

`FIXED_TUNNEL_TABLE` は P4RT gRPC サービスが存在するプラットフォームでのみ機能する。
community SONiC master では P4RT コンテナは一般的に存在するが、SAI `SAI_TUNNEL_TYPE_IPINIP_GRE`
の実装は ASIC ベンダーごとに差がある。

### BRCM SAI 固有の制約 (gre_tunnel_manager.h:42-44)

```cpp
// neighbor_id is required to be equal to encap_dst_ip by BRCM. And the
// neighbor entry needs to be created before GRE tunnel object
swss::IpAddress neighbor_id;
```

コード内に明示的に BRCM SAI 要件として `neighbor_id = encap_dst_ip` が設定されている。
他の SAI 実装でこの制約が必要かは未確認。

### SAI_TUNNEL_ATTR_OVERLAY_INTERFACE の暫定実装

gre_tunnel_manager.cpp:417-420 に以下の TODO がある:
```cpp
// TODO: Remove when SAI_TUNNEL_ATTR_OVERLAY_INTERFACE is not
// mandatory Use gUnderlayIfId, a shared global loopback rif, for encap
// tunnels
entries[i].overlay_if_oid = gUnderlayIfId;
```

これは SAI が `SAI_TUNNEL_ATTR_OVERLAY_INTERFACE` を必須属性として要求するため、
専用 overlay RIF を作らず、グローバルループバック RIF (`gUnderlayIfId`) を代用している。
将来 SAI の仕様変更で不要になる見込み。

### プラットフォーム分岐コードなし

`gre_tunnel_manager.cpp` には `getenv("platform")` / `MLNX_PLATFORM_SUBSTRING` /
`BRCM_PLATFORM_SUBSTRING` 等のプラットフォーム分岐コードは一切存在しない。
SAI create_tunnels の戻り値でエラーハンドリングするのみ。

### VS/VPP プラットフォーム

libsaivs / libsaivpp は `SAI_TUNNEL_TYPE_IPINIP_GRE` の create_tunnels を SUCCESS で返すが
実機転送はない。CI テスト用途に限定される。

### SAI Bulk モード固定

create_tunnels / remove_tunnels は `SAI_BULK_OP_ERROR_MODE_STOP_ON_ERROR` 固定で呼ばれる
(gre_tunnel_manager.cpp:431, 493)。Partial success モードは使われない。

## 根拠コード

- `gre_tunnel_manager.h:42-44`: BRCM SAI neighbor_id 要件
- `gre_tunnel_manager.cpp:417-420`: overlay_if_oid = gUnderlayIfId (TODO 付き)
- `gre_tunnel_manager.cpp:431, 493`: SAI_BULK_OP_ERROR_MODE_STOP_ON_ERROR
