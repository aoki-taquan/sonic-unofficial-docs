# MUX_CABLE per-port Phase H: プラットフォーム差分

<!-- evidence:
  sonic-swss/orchagent/muxorch.cpp:625-628,2192-2193,2233-2246
  sonic-swss/orchagent/neighorch.cpp:78-105
  sonic-linkmgrd/src/DbInterface.cpp:858-888
-->

## 1. cable_type × ACL プログラム

| cable_type | ACL drop rule 動作 | evidence |
|------------|-------------------|---------|
| `active-standby`（デフォルト）| standby 遷移時に `MuxAclHandler` を生成し `INGRESS_TABLE_DROP\|mux_acl_rule` を ASIC に設定 | `muxorch.cpp:630-632` |
| `active-active` | `aclHandler()` 冒頭の `cable_type_ == ACTIVE_ACTIVE` 分岐で即 `return true`（ACL プログラムを完全スキップ）| `muxorch.cpp:625-628` |

`active-active` 構成では ACL によるトラフィック遮断を行わず、両 ToR が同時に active として転送する設計。ACL テーブル `INGRESS_TABLE_DROP` が存在しない ASIC でも `active-active` ポートへの影響はない。

## 2. neighbor_mode × SAI_NEIGHBOR_ENTRY_ATTR_NO_HOST_ROUTE サポート

`neighbor_mode=prefix-route` の効果はプラットフォームの SAI ケーパビリティに依存する。

| ASIC 能力 | `prefix_nbrs_supported_` | `neighbor_mode=prefix-route` 設定時の動作 |
|-----------|--------------------------|-------------------------------------------|
| `SAI_NEIGHBOR_ENTRY_ATTR_NO_HOST_ROUTE` の `create_implemented=true` | `true` | `MuxPrefixBasedNbrHandler` を使用。prefix ベースルーティングで host route を抑制 |
| 非対応（SAI クエリ失敗 or `create_implemented=false`）| `false` | `neighbor_mode` フィールドを無視し `MuxNbrHandler`（host-route）で動作。**silent 降格**（設定値は保持されるが効果なし） |

`prefix_nbrs_supported_` は `MuxOrch` 初期化時（`muxorch.cpp:2192`）に `NeighOrch::isNoHostRouteSupported()` を 1 度だけ呼び出して確定する。ASIC 再起動なしでの変更は不可。

起動ログ（`muxorch.cpp:2193`）:
```
SWSS_LOG_NOTICE("MuxOrch: prefix_nbrs_supported_ = %s", prefix_nbrs_supported_ ? "true" : "false");
```

## 3. prober_type × ASIC ICMP ハードウェアオフロード能力

`prober_type` フィールドの実効値は `linkmgrd` が起動時に `STATE_DB.SWITCH_CAPABILITY.ICMP_OFFLOAD_CAPABLE` を参照して決定する（`DbInterface.cpp:858-888`）。

| `ICMP_OFFLOAD_CAPABLE` 値 | `prober_type` 設定値 | linkmgrd の実効値 | 降格ログ |
|--------------------------|--------------------|--------------------|---------|
| `"true"` | `"hardware"` | `"hardware"`（有効） | なし |
| `"true"` | `"software"` | `"software"` | なし |
| それ以外 / キー不在 | `"hardware"` | 強制 `"software"`（**silent 降格**）| `MUXLOGWARNING` のみ |
| それ以外 / キー不在 | `"software"` | `"software"` | なし |

`hw_offload_capable` は `static` 変数で初回チェック後に固定される（`DbInterface.cpp:858`）。実行中に ASIC ケーパビリティが変化した場合は linkmgrd の再起動が必要。

## 4. active-active × soc_ipv4/soc_ipv6 skip_neighbors

`active-active` 構成で `soc_ipv4` / `soc_ipv6` が設定されると、`handleMuxCfg()` が `addSkipNeighbors()` を呼び出しこれらの IP を `skip_neighbors` セットに登録する（`muxorch.cpp:2218-2228, 2281`）。

- `isSkipNeighbor(ip)` が `true` の IP アドレスは、`MuxNbrHandler::updateTunnelRoute()` および `MuxPrefixBasedNbrHandler::update()` において tunnel route 更新をスキップする（`muxorch.cpp:1096, 1877`）。
- これにより SoC IP 宛のトラフィックは通常の tunnel nexthop 切替から除外され、xcvrd/gRPC 経路を維持する。
- `active-standby` 構成では `soc_ipv4` / `soc_ipv6` が存在しても `skip_neighbors` への登録は行われない（パースループで `soc_ipv4` / `soc_ipv6` フィールドのみ処理）。

## 5. プラットフォーム差分サマリ

| フィールド / 機能 | 影響プラットフォーム条件 | 効果 |
|-----------------|----------------------|------|
| `cable_type=active-active` | `MuxCableType::ACTIVE_ACTIVE` 判定 | ACL drop rule スキップ |
| `neighbor_mode=prefix-route` | `SAI_NEIGHBOR_ENTRY_ATTR_NO_HOST_ROUTE` 非対応 ASIC | silent に host-route 動作 |
| `prober_type=hardware` | `ICMP_OFFLOAD_CAPABLE != "true"` の ASIC | silent に software prober 降格 |
| `soc_ipv4` / `soc_ipv6` 設定 | `cable_type=active-active` 時のみ有効 | skip_neighbors 登録 → tunnel NH 切替除外 |
