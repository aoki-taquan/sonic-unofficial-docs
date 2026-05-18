# tunnel-encap-orch — Phase H: プラットフォーム差・SAI capability 分岐

## 調査対象

slug: tunnel-encap-orch
phase: platform (プラットフォーム差・SAI capability 分岐)
調査日: 2026-05-18

## ソース

- `orchagent/vxlanorch.cpp` (4305596156d70e9797e8a881b3d19b46de0bce0d)
- `orchagent/vxlanorch.h` (同リポジトリ)

## 調査結果

### 1. isDipTunnelsSupported() — P2P peer mode capability による分岐

VxlanTunnelOrch コンストラクタ (vxlanorch.cpp:L1256-L1278) が SAI capability query を実行:

```cpp
status = sai_query_attribute_enum_values_capability(
    gSwitchId, SAI_OBJECT_TYPE_TUNNEL,
    SAI_TUNNEL_ATTR_PEER_MODE, &values);
```

- `SAI_STATUS_SUCCESS` で `SAI_TUNNEL_PEER_MODE_P2P` が含まれる → `is_dip_tunnel_supported = true`
- `SAI_STATUS_SUCCESS` で P2P が含まれない → `is_dip_tunnel_supported = false`
- SAI クエリが失敗 → `SWSS_LOG_WARN` + デフォルト `true` (P2P サポートありとして扱う)

この結果が以下の挙動を決定する:

| `isDipTunnelsSupported()` | EVPN DIP トンネルポート (`Port_EVPN_*`) | SRC VTEP ポート (`Port_SRC_VTEP_*`) |
|---|---|---|
| `true` (P2P 対応) | 各リモート VTEP ごとに個別生成 | 生成されない |
| `false` (P2P 非対応) | 生成されない | VXLAN_TUNNEL_MAP 追加時に 1 つだけ生成、全リモート VTEP を共用 |

### 2. SAI query 失敗時のデフォルト

SAI capability query 自体が失敗した場合 (SAI_STATUS_SUCCESS 以外)、
`is_dip_tunnel_supported = true` に設定し `SWSS_LOG_WARN` を出力する (vxlanorch.cpp:L1260-L1263)。
VS (Virtual Switch) プラットフォームでは SAI capability query が失敗する可能性が高く、
デフォルト `true` が適用されるため DIP トンネルモードで動作する。

### 3. encap TTL — SAI プラットフォームデフォルト依存

`encap_ttl == 0` の場合は `SAI_TUNNEL_ATTR_ENCAP_TTL_MODE` を SAI に渡さず、
プラットフォーム SAI のデフォルト値に依存する (vxlanorch.cpp:L389-L393)。
同様に `ttl_mode == NOT_SET` 時は `SAI_TUNNEL_ATTR_DECAP_TTL_MODE` も省略される。
これらのデフォルト値はベンダー SAI 実装依存。

### 4. FlexCounter — プラットフォーム非依存

FlexCounter のポーリング間隔 (`TUNNEL_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS = 10000 ms`) は
プラットフォーム問わず固定。SAI tunnel stats のサポート有無はプラットフォームによって異なるが、
`setCounterIdList` の失敗はログのみで継続動作する。

## 結論

主要なプラットフォーム差は `SAI_TUNNEL_ATTR_PEER_MODE` capability (P2P サポートの有無) により
`isDipTunnelsSupported()` が決まる 1 点。P2P 非対応プラットフォームでは EVPN DIP トンネル
アーキテクチャが根本的に変わる（個別 DIP トンネル → 共用 SRC VTEP ポート縮退）。
