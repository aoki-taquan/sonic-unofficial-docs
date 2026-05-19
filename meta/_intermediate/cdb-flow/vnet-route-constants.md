# VNET_ROUTE / VNET_ROUTE_TUNNEL — ハードコード定数 (Phase E)

出典: `sonic-swss/orchagent/vnetorch.h`、`sonic-swss-common/common/schema.h`

## テーブル名定数 (schema.h)

| マクロ名 | 値 | 用途 | ソース |
|---------|-----|------|--------|
| `CFG_VNET_RT_TABLE_NAME` | `"VNET_ROUTE"` | CONFIG_DB テーブル名 | schema.h:369 |
| `CFG_VNET_RT_TUNNEL_TABLE_NAME` | `"VNET_ROUTE_TUNNEL"` | CONFIG_DB トンネル経路テーブル名 | schema.h:370 |
| `APP_VNET_RT_TABLE_NAME` | `"VNET_ROUTE_TABLE"` | APPL_DB passthrough 先テーブル名 | schema.h:82 |
| `APP_VNET_RT_TUNNEL_TABLE_NAME` | `"VNET_ROUTE_TUNNEL_TABLE"` | APPL_DB passthrough 先トンネル経路テーブル名 | schema.h:83 |
| `STATE_VNET_RT_TUNNEL_TABLE_NAME` | `"VNET_ROUTE_TUNNEL_TABLE"` | STATE_DB トンネル経路状態テーブル名 | schema.h:495 |
| `STATE_ADVERTISE_NETWORK_TABLE_NAME` | `"ADVERTISE_NETWORK_TABLE"` | STATE_DB BGP prefix 広告通知テーブル名 | schema.h:496 |
| `APP_BFD_SESSION_TABLE_NAME` | `"BFD_SESSION_TABLE"` | APPL_DB BFD セッション書き込み先 | schema.h:120 |

## リソース上限定数 (vnetorch.h)

| マクロ名 | 値 | 用途 | ソース |
|---------|-----|------|--------|
| `VNET_TUNNEL_SIZE` | `40960` | VNET トンネル nexthop の最大数（SAI nexthop pool サイズ） | vnetorch.h:21 |
| `VNET_ROUTE_FULL_MASK_OFFSET_MAX` | `3000` | `/32` 経路に割り当てる VRF オフセットの最大値 | vnetorch.h:22 |
| `VNET_NEIGHBOR_MAX` | `0xffff` (65535) | VNET ネイバーテーブルの最大エントリ数 | vnetorch.h:23 |
| `VNET_BITMAP_SIZE` | `32` | VNET bitmap（VRF ID 管理用）のサイズ | vnetorch.h:20 |

## encapsulation 定数 (vnetorch.h)

| マクロ名 | 値 | 用途 | ソース |
|---------|-----|------|--------|
| `VXLAN_ENCAP_TTL` | `128` | VXLAN encapsulation で設定する TTL 値 | vnetorch.h:24 |
| `VNET_BITMAP_RIF_MTU` | `9100` | VNET bitmap モードで生成する RIF の MTU（bytes） | vnetorch.h:25 |

## monitoring タイプ定数 (vnetorch.h)

| マクロ名 | 値 | 用途 | ソース |
|---------|-----|------|--------|
| `VNET_MONITORING_TYPE_CUSTOM` | `"custom"` | `monitoring` フィールドのカスタム BFD モード識別子 | vnetorch.h:27 |
| `VNET_MONITORING_TYPE_CUSTOM_BFD` | `"custom_bfd"` | `monitoring` フィールドのカスタム BFD 拡張モード識別子 | vnetorch.h:28 |

## モニタリングタイマーデフォルト (vnetorch.cpp)

`VNET_ROUTE_TUNNEL` の `rx_monitor_timer` / `tx_monitor_timer` フィールド未指定時の内部初期値。

| 変数 | 初期値 | 意味 | ソース |
|-----|--------|------|--------|
| `rx_monitor_timer` | `-1` | BFD rx インターバル未指定（BFD デーモン側デフォルト使用） | vnetorch.cpp:3208 |
| `tx_monitor_timer` | `-1` | BFD tx インターバル未指定（BFD デーモン側デフォルト使用） | vnetorch.cpp:3209 |

`-1` の場合 `createBfdSession()` は BFD セッション SET 時に `rx_interval` / `tx_interval` フィールドを付加しない（vnetorch.cpp:2078-2086）。
