# dhcp-server-ipv6 — Phase E: ハードコード定数調査

調査日: 2026-05-16
対象: `DHCP_SERVER_IPV6` テーブル（未実装）/ dhcp6relay プロセス
主要ソース:
- `sonic-net/sonic-dhcp-relay@dhcp6relay/src/relay.h` (7316417034fee6a6c6002490362c9bc75eeafde1)
- `sonic-net/sonic-dhcp-relay@dhcp6relay/src/relay.cpp` (同上)

---

## 調査方針

`DHCP_SERVER_IPV6` テーブル自体は未実装だが、DHCPv6 に直接関係する定数は
**dhcp6relay**（`sonic-dhcp-relay` リポジトリ）の `relay.h` にハードコードされている。
将来の `DHCP_SERVER_IPV6` 実装においても同一ポート・hop 上限が継承されると見込まれるため
ここに記録する。

---

## 1. UDP ポート定数 (relay.h L22-23)

| 定数名 | 値 | 用途 | ソース |
|--------|----|------|--------|
| `RELAY_PORT` | `547` | DHCPv6 サーバ／リレー間 UDP ポート (RFC 8415 §7.2) | relay.h L22 |
| `CLIENT_PORT` | `546` | DHCPv6 クライアント向け UDP ポート (RFC 8415 §7.2) | relay.h L23 |

BPF フィルタは `"udp and port 547"` を使用。`dhcp6relay` は L2 ソケットを開きポート 547 宛の
パケットを直接キャプチャする (`relay.cpp:403`)。

---

## 2. ホップ上限 (relay.h L24)

| 定数名 | 値 | 用途 | ソース |
|--------|----|------|--------|
| `HOP_LIMIT` | `8` | RELAY-FORWARD の hop_count がこの値以上のパケットはドロップ | relay.h L24 |

コメントに "reduced from 32 to 8 as stated in RFC8415" と明記されている。
ドロップ時は `syslog(LOG_WARNING, ...)` を出力する (`relay.cpp:747-751`)。
新規クライアントパケットは hop_count=0 で開始し、中継ごとに +1 される (`relay.cpp:692, 758`)。

---

## 3. その他の主要定数 (relay.h L25-37)

| 定数名 | 値 | 用途 | ソース |
|--------|----|------|--------|
| `DHCPv6_OPTION_LIMIT` | `147` | サポートする DHCPv6 オプション上限 (IANA Option Codes 準拠) | relay.h L25 |
| `RAWSOCKET_RECV_SIZE` | `1048576` (1 MiB) | L2 ソケット受信バッファサイズ上限 (`/proc/sys/net/core/rmem_max` 以下) | relay.h L27 |
| `CLIENT_IF_PREFIX` | `"Ethernet"` | クライアント向けインターフェース名プレフィックス | relay.h L28 |
| `BUFFER_SIZE` | `9200` | パケット処理バッファサイズ（ジャンボフレーム対応） | relay.h L29 |
| `OPTION_RELAY_MSG` | `9` | DHCPv6 Option 9 (Relay Message) | relay.h L33 |
| `OPTION_INTERFACE_ID` | `18` | DHCPv6 Option 18 (Interface-ID、RFC 3315) | relay.h L34 |
| `OPTION_CLIENT_LINKLAYER_ADDR` | `79` | DHCPv6 Option 79 (Client Link-Layer Address、RFC 6939) | relay.h L35 |
| `BATCH_SIZE` | `64` | イベントループ 1 回あたりのバッチ処理数 | relay.h L37 |

---

## 特記事項

1. **DHCP_SERVER_IPV6 未実装**: ポート 547/546 は dhcp6relay が使用するものであり、
   将来の IPv6 サーバ実装でも同一ポートを使う予定（RFC 8415 準拠）。
2. **HOP_LIMIT=8 は RFC8415 準拠**: 旧実装では 32 だったが RFC8415 に合わせて削減済み。
   この値は CONFIG_DB から上書きできない完全なハードコード定数。
3. **RAWSOCKET_RECV_SIZE**: システム上限 (`rmem_max`) 以下でないとソケット作成が失敗する。
   デフォルト値 1048576 は多くの Linux カーネルデフォルトと一致する。

---

## Evidence

- `sonic-net/sonic-dhcp-relay@dhcp6relay/src/relay.h:22-37` (SHA: 7316417034fee6a6c6002490362c9bc75eeafde1)
- `sonic-net/sonic-dhcp-relay@dhcp6relay/src/relay.cpp:403, 692, 747-751, 758` (同上)
