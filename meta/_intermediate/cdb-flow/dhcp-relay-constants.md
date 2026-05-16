# DHCP_RELAY — Phase E: ハードコード定数

> **調査根拠**: `sonic-dhcp-relay/dhcp6relay/src/relay.h`, `config_interface.cpp`, `relay.cpp`, `wait_for_intf.sh.j2` 全行精読 (2026-05-15)

## ソース定義一覧

### relay.h — マクロ定数

| 定数名 | 値 | 定義箇所 | 意味 |
|-------|-----|---------|------|
| `RELAY_PORT` | `547` | relay.h:22 | DHCPv6 サーバ・リレー間の UDP ポート (RFC 3315) |
| `CLIENT_PORT` | `546` | relay.h:23 | DHCPv6 クライアント向け UDP ポート |
| `HOP_LIMIT` | `8` | relay.h:24 | relay-forward の最大 hop count (RFC 8415 準拠、旧値 32 から変更) |
| `DHCPv6_OPTION_LIMIT` | `147` | relay.h:25 | 処理対象 DHCPv6 オプションコードの上限 |
| `RAWSOCKET_RECV_SIZE` | `1048576` (1 MiB) | relay.h:27 | クライアント側 raw socket の受信バッファサイズ (`/proc/sys/net/core/rmem_max` 依存) |
| `CLIENT_IF_PREFIX` | `"Ethernet"` | relay.h:28 | クライアント I/F 判定プレフィックス (受信時に Ethernet* でない I/F は別処理) |
| `BUFFER_SIZE` | `9200` (バイト) | relay.h:29 | DHCPv6 メッセージのシリアライズ用バッファサイズ。Jumbo frame 対応 (9000 + ヘッダ余裕) |
| `BATCH_SIZE` | `64` | relay.h:37 | SubscriberStateTable pops() の一回あたり最大エントリ数 |
| `OPTION_RELAY_MSG` | `9` | relay.h:33 | DHCPv6 OPTION_RELAY_MSG コード (RFC 3315 §22.10) |
| `OPTION_INTERFACE_ID` | `18` | relay.h:34 | DHCPv6 OPTION_INTERFACE_ID コード (RFC 3315 §22.18) |
| `OPTION_CLIENT_LINKLAYER_ADDR` | `79` | relay.h:35 | DHCPv6 Option 79 コード (RFC 6939 — Client Link-Layer Address) |

### config_interface.cpp — コード内定数

| 定数名 | 値 | 定義箇所 | 意味 |
|-------|-----|---------|------|
| `DEFAULT_TIMEOUT_MSEC` | `1000` ms | config_interface.cpp:6 | `swssSelect.select()` のタイムアウト (1 秒) |
| `option_79_default` | `true` | config_interface.cpp:117 | `rfc6939_support` 未設定時のデフォルト — Option 79 有効 |
| `interface_id_default` (非 DualToR) | `false` | config_interface.cpp:118 | `interface_id` 未設定・非 DualToR 環境のデフォルト |
| `interface_id_default` (DualToR) | `true` | config_interface.cpp:121 | `dual_tor_sock` 存在時に上書き (DualToR 判定は j2 テンプレート) |

### relay.cpp — コード内定数

| 定数名 | 値 | 定義箇所 | 意味 |
|-------|-----|---------|------|
| VLAN ソケット bind retry 回数 | `6` | relay.cpp:641 (`retry < 6`) | `prepare_vlan_sockets()` の最大リトライ |
| VLAN ソケット bind retry 間隔 | `5` 秒 | relay.cpp:640 (`sleep(5)`) | リトライ間の待機時間 |
| LLA チェックタイマー周期 | `60` 秒 | relay.cpp:1305 (`tv.tv_sec = 60`) | LLA 未準備 VLAN の定期再チェック間隔 |
| libevent base | EV_PERSIST | relay.cpp:1301 | LLA チェックタイマーは永続イベント |

### wait_for_intf.sh.j2 — 起動待機定数

| 定数 | 値 | 定義箇所 | 意味 |
|-----|-----|---------|------|
| STATE_DB ポーリング間隔 | `1` 秒 | wait_for_intf.sh.j2:18 | `INTERFACE_TABLE|<intf>|state == ok` ポーリング間隔 |
| インタフェース ready 後の追加待機 | `10` 秒 | wait_for_intf.sh.j2:51 | STATE_DB ok 確認後に dhcp6relay 起動前に待つ固定 sleep |

## 補足

- `HOP_LIMIT=8` は RFC 8415 の勧告に基づき 32 から変更（コメント `//HOP_LIMIT reduced from 32 to 8 as stated in RFC8415`）。relay-forward の hop_count がこの値以上のパケットは `LOG_INFO "Dropping relay-forward message..."` で silent drop される。
- `BUFFER_SIZE=9200` はジャンボフレーム (MTU 9000) を考慮したマジックナンバー。パケットがこのサイズを超えるとシリアライズ失敗 (`LOG_WARNING "Failed to marshal...packet size %lu over limit"`)。
- `DEFAULT_TIMEOUT_MSEC=1000` は `constexpr auto` で定義されており、コンパイル時定数。外部から変更不可。
- DualToR 判定は `dhcpv6-relay.agents.j2:16` の `DEVICE_METADATA.localhost.subtype == "DualToR"` チェックで決まり、`-u Loopback0` 引数が付くと `dual_tor_sock` が生成される。これが `interface_id_default` を `true` に変える唯一のパス。
