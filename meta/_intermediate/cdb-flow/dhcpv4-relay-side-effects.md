# dhcpv4-relay Phase F — 副次 DB 書込 調査ノート

## 調査対象

- `sonic-dhcp-relay/dhcp4relay/src/dhcp4relay_stats.cpp` 全行読了
- `sonic-dhcp-relay/dhcp4relay/src/dhcp4relay_stats.h` 読了
- `sonic-dhcp-relay/dhcp4relay/src/dhcp4relay.cpp:86-87, 591-828, 1570-1571` 読了
- `sonic-dhcp-relay/dhcp4relay/src/dhcp4relay_mgr.cpp:56-90, 510-518, 762-771` 読了

## 発見事項

### COUNTERS_DB 書き込み

- テーブル: `COUNTERS_DHCPV4`
- キー形式: `<Vlan>|RX` / `<Vlan>|TX`
- フィールド: `Discover`, `Offer`, `Request`, `Decline`, `Acknowledge`, `NegativeAcknowledge`, `Release`, `Inform`, `Unknown`, `Malformed`, `Dropped`
- 書き込み間隔: 30 秒 (`DHCP_RELAY_DB_UPDATE_TIMER_VAL = 30`, `dhcp4relay_stats.h:12`)
- 専用スレッド: `DHCPCounter_table::db_update_loop()` が `start_db_updates()` 呼び出しで起動 (`dhcp4relay.cpp:1571`)
- 累積値: Redis の既存値を read してデルタ加算して write。再起動をまたいで値が単調増加する

### increment_counter 呼び出し箇所

```
dhcp4relay.cpp:591   relay_server_packet_handler: TX DROP (hop limit超過)
dhcp4relay.cpp:616   relay_server_packet_handler: TX DROP (Option82 discard)
dhcp4relay.cpp:628   relay_server_packet_handler: TX DROP
dhcp4relay.cpp:650   relay_server_packet_handler: TX <msg_type>
dhcp4relay.cpp:655   relay_server_packet_handler: TX DROP
dhcp4relay.cpp:787   relay_client_packet_handler: RX DROP (interface not ready)
dhcp4relay.cpp:795   relay_client_packet_handler: RX <msg_type>
dhcp4relay.cpp:808   relay_client_packet_handler: TX DROP (VLAN socket not ready)
dhcp4relay.cpp:821   relay_client_packet_handler: TX <msg_type>
dhcp4relay.cpp:824   relay_client_packet_handler: TX DROP
dhcp4relay.cpp:1024-1089: RX MALFORMED / DROP (各種パースエラー)
```

### VLAN ライフサイクルとカウンタ

- `initialize_interface(vlan)`: VLAN 追加時に全フィールドを 0 初期化してキャッシュに登録 (`dhcp4relay.cpp:842`)
- `remove_interface(vlan)`: VLAN 削除時にキャッシュからエントリを削除 (`dhcp4relay.cpp:846`)
- 注意: COUNTERS_DB 上の Redis エントリは `remove_interface()` では削除されない

### CONFIG_DB / APPL_DB / STATE_DB への書き込み

なし。STATE_DB は読み取り専用で subscribe のみ使用。
