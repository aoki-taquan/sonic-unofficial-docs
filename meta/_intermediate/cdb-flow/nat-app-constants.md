# nat-app-constants — Phase E 調査ノート

対象テーブル (APPL_DB): NAT_TABLE / NAPT_TABLE / NAT_TWICE_TABLE / NAPT_TWICE_TABLE / NAT_GLOBAL_TABLE / NAT_DNAT_POOL_TABLE

## ソース確認済みファイル

- `sonic-swss/orchagent/natorch.h` L36-38
- `sonic-swss/cfgmgr/natmgr.h` L33-127

## natorch.h 定数 (orchagent 側)

| 定数 | 値 | 用途 |
|-----|-----|------|
| `VALUES` | `"Values"` | NAT_GLOBAL_TABLE の固定キー文字列 |
| `NAT_HITBIT_N_CNTRS_QUERY_PERIOD` | `5` (秒) | NAT カウンタ/ヒットビット問い合わせタイマ周期 |
| `NAT_CONNTRACK_TIMEOUT_PERIOD` | `86400` (秒) | conntrack タイムアウト通知タイマ周期 (1 日) |
| `NAT_HITBIT_QUERY_MULTIPLE` | `6` | ヒットビット問い合わせ頻度倍率。`5秒 * 6 = 30秒` ごとにヒットビット取得 |

## natmgr.h 定数 (cfgmgr / natmgrd 側)

### タイムアウト値の上下限・デフォルト

| 定数 | 値 | 対応フィールド |
|-----|-----|-------------|
| `NAT_TIMEOUT_MIN` | `300` | `nat_timeout` 下限 |
| `NAT_TIMEOUT_MAX` | `432000` | `nat_timeout` 上限 (5 日) |
| `NAT_TIMEOUT_DEFAULT` | `600` | `nat_timeout` デフォルト |
| `NAT_TIMEOUT_LOW` | `0` | `nat_timeout` 無効値 (ゼロ) |
| `NAT_TCP_TIMEOUT_MIN` | `300` | `nat_tcp_timeout` 下限 |
| `NAT_TCP_TIMEOUT_MAX` | `432000` | `nat_tcp_timeout` 上限 (5 日) |
| `NAT_TCP_TIMEOUT_DEFAULT` | `86400` | `nat_tcp_timeout` デフォルト (1 日) |
| `NAT_UDP_TIMEOUT_MIN` | `120` | `nat_udp_timeout` 下限 |
| `NAT_UDP_TIMEOUT_MAX` | `600` | `nat_udp_timeout` 上限 (10 分) |
| `NAT_UDP_TIMEOUT_DEFAULT` | `300` | `nat_udp_timeout` デフォルト (5 分) |

### エントリ構造定数

| 定数 | 値 | 用途 |
|-----|-----|------|
| `STATIC_NAT_KEY_SIZE` | `1` | STATIC_NAT テーブルキーセグメント数 |
| `STATIC_NAPT_KEY_SIZE` | `3` | STATIC_NAPT テーブルキーセグメント数 |
| `POOL_TABLE_KEY_SIZE` | `1` | NAT_POOL テーブルキーセグメント数 |
| `BINDING_TABLE_KEY_SIZE` | `1` | NAT_BINDINGS テーブルキーセグメント数 |
| `L3_INTERFACE_KEY_SIZE` | `2` | IP プレフィックス付きインタフェースキーサイズ |
| `L3_INTERFACE_ZONE_SIZE` | `1` | ゾーン設定用ポート単位インタフェースキーサイズ |
| `TWICE_NAT_ID_MIN` | `1` | `twice_nat_id` 最小値 |
| `TWICE_NAT_ID_MAX` | `9999` | `twice_nat_id` 最大値 |
| `L4_PORT_MIN` | `1` | L4 ポート番号最小値 |
| `L4_PORT_MAX` | `65535` | L4 ポート番号最大値 |
| `IP_ADDR_MASK_LEN_MIN` | `1` | IP マスク長最小値 |
| `IP_ADDR_MASK_LEN_MAX` | `32` | IP マスク長最大値 |
| `NAT_ENTRY_REFRESH_PERIOD` | `86400` | conntrack エントリリフレッシュ通知周期 (1 日) |
| `MATCH_IP_PROTOCOL_ICMP` | `1` | ICMP プロトコル番号定数 |
| `MATCH_IP_PROTOCOL_TCP` | `6` | TCP プロトコル番号定数 |
| `MATCH_IP_PROTOCOL_UDP` | `17` | UDP プロトコル番号定数 |
