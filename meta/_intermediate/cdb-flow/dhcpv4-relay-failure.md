# dhcpv4-relay — Phase D 失敗挙動調査ノート

調査日: 2026-05-18
調査対象: `sonic-dhcp-relay/dhcp4relay/src/dhcp4relay.cpp`, `dhcp4relay_mgr.cpp`

## 起動時 fatal exit ポイント

- `event_base_new()` 失敗 → exit(EXIT_FAILURE) (dhcp4relay.cpp:1517-1519)
- `pipe()` 失敗 → exit(EXIT_FAILURE) (dhcp4relay.cpp:1533-1535)
- `event_new()` 失敗 (config pipe) → exit(EXIT_FAILURE) (dhcp4relay.cpp:1545-1547)
- `sock_open()` 失敗 → exit(EXIT_FAILURE) (dhcp4relay.cpp:1565-1567)
- `event_new()` 失敗 (packet) → exit(EXIT_FAILURE) (dhcp4relay.cpp:1560-1562)
- config_pipe sync-barrier write 失敗 → exit(EXIT_FAILURE) (dhcp4relay_mgr.cpp:112-117)

## VLAN ソケット生成失敗 (自動リトライ)

`prepare_vlan_sockets()` が -1 を返す条件:
1. VLAN インタフェースに primary IPv4 なし → "No IPv4 address on interface %s, deferring socket creation"
2. `SO_BINDTODEVICE` 失敗 → ERR ログ → close + return -1
3. `bind()` 失敗 → ERR ログ → close + return -1

呼出し元:
- dhcp4relay.cpp:1266 — DHCP_RELAY_CONFIG_UPDATE 処理時
- dhcp4relay.cpp:1355 — VLAN_INTERFACE_UPDATE 処理時
- dhcp4relay.cpp:1378 — VRF更新後の再ソケット生成時

いずれも "will create when IPv4 is assigned" / "will retry on next event" と LOG_NOTICE を出して continue。

## relay 設定処理中の silent skip

- dhcpv4_servers 空: WARNING "No servers found for VLAN %s, skipping configuration." → delete relay_msg, continue
- bad_alloc: ERR "Memory allocation failed: %s" → delete relay_msg, continue (dhcp4relay_mgr.cpp:379)
- stoi() 例外 (max_hop_count): WARNING "Invalid max_hop_count value" → フィールドスキップ (dhcp4relay_mgr.cpp:411-415)
- config_pipe write 失敗: ERR "Failed to write to config update pipe" → delete relay_msg (dhcp4relay_mgr.cpp:455)

## サーバ応答パスのドロップ

dhcp4relay.cpp:806: "Dropping server reply for %s: VLAN socket not ready (no IPv4 address)"

## select ループエラー

dhcp4relay_mgr.cpp:125-127: Select::ERROR → LOG_ERR + continue (ループ継続)
