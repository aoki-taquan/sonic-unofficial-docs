# PORTCHANNEL フィールド値分析

## enum フィールド

### `admin_status` (stypes:admin_status, mandatory)
- `up` → LAG admin up (SAI + Linux netdev)
- `down` → LAG admin down

### `mode` (stypes:switchport_mode)
- `routed` (デフォルト): L3 ルーテッド LAG
- `access`: L2 access LAG (single VLAN)
- `trunk`: L2 trunk LAG (複数 VLAN)

### `lacp_key` (union: string "auto" | uint16 1..65535)
- `auto`: PortChannel 名末尾の数字から LACP key を自動生成 (数字プレフィックス 1 付加)
- `1`..`65535`: 明示的な LACP key

### `fallback` (stypes:boolean_type)
- `true`: LACP 対向未応答時に fallback (単独メンバで up)
- `false` / 未設定: LACP ネゴシエーション完了まで down

### `fast_rate` (stypes:boolean_type)
- `true`: LACP PDU を 1 秒間隔 (fast) で送受信
- `false` / 未設定: 30 秒間隔 (slow)

### `tpid` (stypes:tpid_type)
- `0x8100`: 802.1Q
- `0x9100` / `0x9200` / `0x88a8` / `0x88A8`: Q-in-Q / 802.1ad
- 非対応: `Failed to set TPID 0x%x to LAG pid:` → SWSS_LOG_ERROR

## 数値範囲フィールド
- `min_links`: uint16 (1..1024) — メンバ数以上に設定すると LAG 常時 down
- `mtu`: uint16 (1..9216)

## ソース
- sonic-portchannel.yang (sonic-buildimage sha 9ea932ec)
- orchagent/portsorch.cpp, lagorch.cpp, teammgrd (sonic-swss)
