# PORT フィールド値分析

## enum フィールド

### `admin_status` (stypes:admin_status)
- `up` → SAI_PORT_ATTR_ADMIN_STATE=true
- `down` (デフォルト) → SAI_PORT_ATTR_ADMIN_STATE=false

### `fec` (string pattern)
- `rs` → SAI_PORT_FEC_MODE_RS (Reed-Solomon、100G+ 向け)
- `fc` → SAI_PORT_FEC_MODE_FC (FireCode、25G 向け)
- `none` → SAI_PORT_FEC_MODE_NONE
- `auto` → SAI_PORT_FEC_MODE_AUTO (対向とネゴシエーション)
- 不正: `Failed to set FEC mode` → SWSS_LOG_ERROR

### `autoneg` / `link_training` (string pattern `on|off`)
- `on`: オートネゴ / リンクトレーニング有効
- `off`: 無効
- 非サポート HW で `on`: `autoneg is not supported` → SWSS_LOG_ERROR

### `mode` (stypes:switchport_mode)
- `routed` (デフォルト): L3 ルーテッドポート
- `access`: L2 access (single VLAN)
- `trunk`: L2 trunk (複数 VLAN)

### `role` (pattern `Ext|Int|Inb|Rec|Dpc`)
- `Ext` (デフォルト): 外部向けポート
- `Int`: 内部 ASIC 間接続
- `Inb`: inband 管理
- `Rec`: recirculation
- `Dpc`: DPC ポート

### `pfc_asym` (string `on|off`)
- `on`: 非対称 PFC 有効
- `off`: 無効

### `tpid` (stypes:tpid_type)
- `0x8100`: 標準 802.1Q
- `0x9100` / `0x9200`: Q-in-Q / VLAN Stacking
- `0x88a8` / `0x88A8`: 802.1ad (Provider Bridging)
- 非対応値: SAI エラー

### `dom_polling` (stypes:admin_mode)
- `enabled`: DOM ポーリング有効
- `disabled`: 無効

## 数値範囲フィールド
- `speed`: 1..1600000 (Mbps)、mandatory
- `mtu`: 68..9216 (byte)
- `subport`: 0..8 (breakout 論理サブポート番号)

## adv_speeds / adv_interface_types の `all` 制約
- `all` 単独でのみ指定可能 (must 制約)
- `all` と他値の混在: `must` 違反 → reject

## ソース
- sonic-port.yang (sonic-buildimage sha 9ea932ec)
- orchagent/portsorch.cpp (sonic-swss)
- portmgrd (sonic-swss)
