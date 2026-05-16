# MUX_CABLE Phase H: プラットフォーム差分

<!-- evidence: sonic-swss/orchagent/muxorch.cpp -->

## 1. Active-Standby vs Active-Active モデル差

| 観点 | Active-Standby (default) | Active-Active |
|------|--------------------------|---------------|
| ステートマシン | `MUX_STATE_ACTIVE_STANDBY` → `stateStandby` | 同一ステートマシン (`MuxState`)、両 ToR が active |
| ACL drop rule | standby 遷移時に追加 (`aclHandler(port, alias, true)`) | **skip** (`cable_type_ == ACTIVE_ACTIVE` で `aclHandler` を即 `return true`) (muxorch.cpp:625-628) |
| `soc_ipv4`/`soc_ipv6` | 無視 (skip_neighbors に追加されない) | skip_neighbors に追加し tunnel 経由を抑制 (muxorch.cpp:2218-2228) |
| `state=detach` | linkmgrd が `WARN` を出して無視 | active-active 専用: NIC/ToR を論理的に切り離す |
| tunnel NH 利用 | standby 遷移で peer ToR への SAI tunnel NH を使用 | 両 ToR で tunnel NH が設定されることがある |

**証跡**: `muxorch.cpp:625-628` — `aclHandler` 冒頭の分岐でACL プログラムをスキップ。

## 2. xcvrd 実装差 (hardware prober / gRPC)

コード引用 (muxorch.cpp:1094-1100):
```
// avoid kernel route re-programming to allow xcvrd(gRPC)
// traffic to flow locally to the NIC(SoC) when in standby
if (mux_orch->isSkipNeighbor(nh.ip_address))
{
    SWSS_LOG_INFO("Skip updating neighbor %s, add %d", ...);
    return;
}
```

- `prober_type=hardware` の場合、xcvrd が gRPC 経由でハードウェア MUX を制御する。
- active-active 構成で `soc_ipv4`/`soc_ipv6` が設定されると、`skip_neighbors` セットに登録される。
- standby 状態で `MuxNbrHandler::updateTunnelRoute()` が呼ばれた際、skip_neighbor は tunnel route の更新をスキップ。
- これにより `prober_type=software` (linkmgrd ICMP) とは異なり、xcvrd が gRPC でネイティブに処理する経路が分離される。

## 3. SmartSwitch / DPU 差分

- `soc_ipv4`/`soc_ipv6` は SmartSwitch (SoC = Data Processing Unit) に対応するフィールド。
- SoC IP は `skip_neighbors` に登録され、通常の neighbor → tunnel NH 切替から除外される (`addSkipNeighbors`, muxorch.cpp:2281)。
- `isSkipNeighbor()` が `true` を返す IP は `MuxPrefixBasedNbrHandler::update()` でも tunnel route 更新をスキップ (muxorch.cpp:1877)。
- DELETE 時は `removeSkipNeighbors()` で skip_neighbors セットからクリア (muxorch.cpp:2327)。
- `prefix_nbrs_supported_` が `false` の ASIC では `neighbor_mode=prefix-route` を設定しても `NBR_HANDLER_HOST_ROUTE` で動作する (muxorch.cpp:2240)。

## 4. neighbor_mode × ASIC サポート差

| ASIC 能力 | `prefix_nbrs_supported_` | `neighbor_mode=prefix-route` 効果 |
|-----------|--------------------------|-----------------------------------|
| `SAI_NEIGHBOR_ENTRY_ATTR_NO_HOST_ROUTE` 対応 | `true` | `MuxPrefixBasedNbrHandler` 選択 |
| 非対応 (silent 無視) | `false` | `MuxNbrHandler` (host-route) に強制降格 |

起動時に `SWSS_LOG_NOTICE("MuxOrch: prefix_nbrs_supported_ = %s", ...)` でログ出力 (muxorch.cpp:2193)。

## 5. グレップカバレッジ

| パターン | hit 数 | 証跡行 |
|---------|--------|--------|
| `ACTIVE_ACTIVE` / `active-active` | 5 | 625,627,2233,2235 |
| `xcvrd\|gRPC` | 2 | 1094-1095 |
| `soc_ip` | 6 | 2218-2228,2281 |
| `isSkipNeighbor` | 3 | 1096,1687,1877 |
| `prefix_nbrs_supported_` | 4 | 1681,2192,2193,2240 |
