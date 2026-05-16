# DHCPV4_RELAY — ハードコード定数調査 (Phase E)

調査日: 2026-05-16  
調査対象: `sonic-dhcp-relay/dhcp4relay/src/dhcp4relay.h`, `dhcprelayd.py`

## 調査根拠

`sonic-dhcp-relay` リポ `dhcp4relay/src/dhcp4relay.h` 全行精読。
`sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/dhcprelayd/dhcprelayd.py` 精読。

## 発見した定数

### プロトコル定数 (dhcp4relay.h)

| 定数名 | 値 | 行番号 | 意味 |
|--------|-----|--------|------|
| `RELAY_PORT` | `67` | dhcp4relay.h:24 | DHCPv4 サーバ・リレー間 UDP ポート (RFC 2131) |
| `CLIENT_PORT` | `68` | dhcp4relay.h:25 | DHCPv4 クライアント向け UDP ポート |
| `HOP_LIMIT` | `4` | dhcp4relay.h:26 | relay-forward の最大 hop count (BPF フィルタ前段で使用) |
| `DHCPv4_OPTION_LIMIT` | `255` | dhcp4relay.h:27 | 処理対象オプションコードの上限値 |
| `RAWSOCKET_RECV_SIZE` | `1048576` (1 MiB) | dhcp4relay.h:28 | クライアント側 raw socket 受信バッファサイズ |
| `CLIENT_IF_PREFIX` | `"Ethernet"` | dhcp4relay.h:29 | クライアント I/F 判定プレフィックス |
| `BUFFER_SIZE` | `9200` バイト | dhcp4relay.h:35 | DHCPv4 メッセージシリアライズ用バッファ（ジャンボフレーム MTU 9000 対応） |
| `MAX_DHCP_PKT_SIZE` | `1472` バイト | dhcp4relay.h:36 | 最大 DHCP パケットサイズ (1500 - IP+UDP ヘッダ) |
| `MAX_HOP_COUNT` | `16` | dhcp4relay.h:39 | `relay_config.max_hop_count` struct のデフォルト値 |
| `OPTION_RELAY_MSG` | `82` | dhcp4relay.h:57 | DHCPv4 Option 82 (Relay Agent Information) コード |

### 動作定数 (dhcprelayd.py)

| 定数名 | 値 | 行番号 | 意味 |
|--------|-----|--------|------|
| `DEFAULT_SELECT_TIMEOUT` | `5000` ms | dhcprelayd.py:22 | swsscommon Select タイムアウト |
| 起動待機 sleep | `5` 秒 | dhcprelayd.py:67 | dhcrelay プロセス起動待ち固定 sleep |
| dhcp_server_ip ポーリング上限 | `10` 回 | dhcprelayd.py:377 | STATE_DB から dhcp_server IP 取得の最大試行回数 |
| dhcp_server_ip ポーリング間隔 | `10` 秒 | dhcprelayd.py:383 | 試行間の sleep |

### YANG-実装 discrepancy (max_hop_count)

YANG default は `4`、C++ struct `relay_config.max_hop_count` は `MAX_HOP_COUNT = 16` で初期化 (dhcp4relay.h:120)。
DB から `max_hop_count` フィールドが未設定の場合、struct デフォルト `16` が使われる。
YANG の `stoi()` 例外時も struct 値 `16` のまま続行 (WARNING ログのみ、dhcp4relay.cpp 参照)。

## 変更可否

すべての定数はコンパイル時に固定。CONFIG_DB・環境変数・設定ファイルからは変更不可。
`max_hop_count` のみ `DHCPV4_RELAY` テーブルフィールドで上書き可能 (YANG uint8 1..16)。
