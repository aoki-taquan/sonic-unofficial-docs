# STATIC_ROUTE — Phase 6/7/8 派生・分岐 証跡

## Phase 6: 自動派生 (assignment scan)

`staticd` (FRR) / `fpmsyncd` / `staticroutemgrd` が `STATIC_ROUTE` テーブルを読み、FRR に静的ルートを設定する。

| 派生先フィールド | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| FRR `ip route` コマンド形式 | key に IPv6 プレフィクス (`:` 含む) | `ipv6 route` コマンド使用 | `staticroutemgrd` |
| FRR `ip route` コマンド形式 | key に IPv4 プレフィクス (`.` 含む) | `ip route` コマンド使用 | `staticroutemgrd` |
| `nexthop_vrf` 未指定時 | `nexthop_vrf` フィールドなし | デフォルト VRF を使用 | `staticroutemgrd` |
| `distance` デフォルト | `distance` フィールドなし | FRR デフォルト distance (1) を使用 | `staticroutemgrd` |

## Phase 7: 条件付き登録 (add_manager 条件)

| 条件 | 影響 | ソース |
|---|---|---|
| `staticroutemgrd` / `fpmsyncd` は常時起動 | `STATIC_ROUTE` テーブルは無条件購読 | `orchdaemon.cpp` / `staticroutemgrd` |
| VRF が `STATIC_ROUTE|<vrf>|<prefix>` 形式で指定 | FRR に VRF 付き static route を設定 | `staticroutemgrd` |
| `bfd==true` | BFD セッションとの連携が有効 | `staticroutemgrd` |

## Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `staticroutemgrd` | IPv6 プレフィクス | `ipv6 route <prefix> <nexthop>` | `staticroutemgrd` |
| `staticroutemgrd` | IPv4 プレフィクス | `ip route <prefix> <nexthop>` | `staticroutemgrd` |
| `staticroutemgrd` | `nexthop_vrf` フィールドあり | `ip route ... nexthop-vrf <vrf>` | `staticroutemgrd` |
| `staticroutemgrd` | `blackhole==true` | `ip route <prefix> blackhole` | `staticroutemgrd` |
| `staticroutemgrd` | `bfd==true` | BFD ダウン時に静的ルートを削除 | `staticroutemgrd` |
| `staticroutemgrd` | `distance` フィールドあり | FRR route distance を設定 | `staticroutemgrd` |
| `staticroutemgrd` | del_handler | FRR に `no ip route` 発行 | `staticroutemgrd` |

> **スキャン証跡**: `STATIC_ROUTE` は FRR 静的ルート設定の直接マッピング。IPv4/IPv6 の分岐と VRF/BFD オプション分岐が主要。CONFIG_DB 内フィールド間の自動付与はなし。
