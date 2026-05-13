# PEER_SWITCH フィールド値分析

## enum フィールド

なし — address_ipv4 は inet:ipv4-address 型、peer_switch (key) は stypes:hostname 型。

## 特殊制約

### エントリ数 (max-elements 1)
- 0件: linkmgrd が警告、Dual-ToR 機能無効扱い
- 1件: 正常
- 2件以上: YANG max-elements 1 により reject

### `address_ipv4`
- 有効な IPv4: linkmgrd がピアへの ICMP 到達確認に使用
- 未設定: MUX 切り替え不可

## ソース
- sonic-peer-switch.yang (sonic-buildimage sha 9ea932ec)
- linkmgrd (sonic-linkmgrd)
