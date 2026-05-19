# ip-mcast-route — Phase E 調査メモ (hardcoded constants)

調査日: 2026-05-19
対象ソース:
- sonic-net/sonic-swss orchagent/p4orch/ip_multicast_manager.cpp (HEAD)
- sonic-net/sonic-swss orchagent/p4orch/l3_multicast_manager.cpp (HEAD)

## 検出定数

### ip_multicast_manager.cpp (namespace p4orch)

| 定数名 | 型 | 値 | 用途 |
|--------|----|----|------|
| `kRifMemberMacAddress` | `constexpr char*` | `"00:00:00:00:00:01"` | RPF group 向け RIF の `SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS` に固定設定 (L596) |
| `SAI_PACKET_ACTION_FORWARD` | SAI enum | L61, L376 | IPMC エントリのパケットアクション — 変更不可 |
| `SAI_IPMC_ENTRY_TYPE_XG` | SAI enum | L704 | IPMC エントリタイプ — any-source (XG) 固定 |
| source IP `0` | uint32/IPv6-zero | L712,L719 | IPMC エントリの送信元 IP — any-source を示すゼロ埋め |

### l3_multicast_manager.cpp (namespace p4orch)

コードコメント（L48-52）に「これらはプレースホルダ値。リンクローカル IP はどんな値でも構わない。デフォルト MAC は MAC 書き換えを行わない場合は無視される」と明記されている。

| 定数名 | 型 | 値 | 用途 |
|--------|----|----|------|
| `kLinkLocalIpv4Address` | `constexpr char*` | `"169.254.0.1"` | SAI neighbor entry / next hop オブジェクトの IP アドレスフィールドに固定設定 (L167, L189) |
| `kNeighborMacAddress` | `constexpr char*` | `"00:00:00:00:00:01"` | MULTICAST_ROUTER_INTERFACE_TABLE 内部エントリのデフォルト `dst_mac` (L641) |
| `kDefaultMyMacAddress` | `constexpr char*` | `"00:00:00:00:00:01"` | SAI my-mac エントリの `SAI_MY_MAC_ATTR_MAC_ADDRESS` に固定設定 (L1415) |
| `kDefaultMyMacAddressMask` | `constexpr char*` | `"00:00:00:00:00:00"` | SAI my-mac エントリの `SAI_MY_MAC_ATTR_MAC_ADDRESS_MASK` に固定設定 (L1416) — 全ビット0のマスクで任意 MAC にマッチ |

## 考察

- これらはすべてコード中に埋め込まれており、CONFIG_DB フィールド・YANG スキーマ・環境変数による上書きは不可能
- `kLinkLocalIpv4Address` / `kNeighborMacAddress` は SAI オブジェクト構造上「必須だが実際には無視される」プレースホルダであり、データプレーンの転送に影響しない
- `kDefaultMyMacAddressMask` がオールゼロ → SAI my-mac ACL エントリが全 MAC にマッチするワイルドカードとして機能する
- `SAI_IPMC_ENTRY_TYPE_XG` 固定により ASM (Any-Source Multicast) のみサポート。SSM (Source-Specific Multicast) は本実装では対応不可
