# DHCP_SERVER_IPV4 フィールド値分析

## enum フィールド

### `state` (admin_mode: enabled/disabled)
- `enabled` → dhcpservd が kea-dhcp4 サーバを起動し DHCP DISCOVER に応答
- `disabled` → kea-dhcp4 を停止。クライアントへの応答なし

### `mode` (enum: PORT, 必須)
- `PORT` → ポート単位で IP を割り当て（DHCP_SERVER_IPV4_PORT テーブルで定義）。現在は PORT のみサポート

## uint / ip フィールド

### `lease_time` (uint32, 必須)
- 正の整数（秒）→ kea-dhcp4 のリース有効期間として設定
- 0 → YANG range 違反（1 以上必須）

### `gateway` (ipv4-address)
- 設定あり → DHCP OFFER の option 3 (Router) にこの IP を通知
- 未設定 → gateway なしで OFFER（クライアントのデフォルトルートが設定されない）

### `netmask` (ipv4-address-no-zone, 必須)
- サブネットマスクとして kea-dhcp4 のサブネット定義に使用

## cross-cutting
- DEVICE_METADATA.dhcp_server が設定されていないと dhcpservd 自体が起動しない
- `customized_options` で DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS を参照。leafref が存在しない option 名を指定すると YANG validate で reject
