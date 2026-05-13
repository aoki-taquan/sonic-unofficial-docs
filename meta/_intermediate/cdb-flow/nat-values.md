# 値依存挙動分析: NAT_GLOBAL / NAT_POOL / NAT_BINDINGS

## Phase 1: YANG フィールド全列挙

### NAT_GLOBAL
- `admin_mode` (admin_mode enum): default `disabled`
- `nat_timeout` (uint32): range 300..432000, default 600 [秒]
- `nat_tcp_timeout` (uint32): range 300..432000, default 86400 [秒]
- `nat_udp_timeout` (uint16): range 120..600, default 300 [秒]

### NAT_POOL
- `name` (string, key): length 1..32
- `nat_ip` (IP range, mandatory)
- `nat_port` (port range string): format `start-end`

### NAT_BINDINGS
- `name` (string, key): length 1..32
- `nat_pool` (leafref NAT_POOL.name, mandatory)
- `nat_type` (enum): `snat`/`dnat`, default `dnat` (YANG); natmgrd は `snat` デフォルトで動作
- `twice_nat_id` (uint16): range 1..9999

## Phase 2: per-value explicit grep

- `natorch.cpp`: `admin_mode = disabled` → `"NAT Feature is not yet enabled, skipped adding ..."` WARN + キュー保持
- `natorch.cpp`: `enableNatFeature()` 後にキュー内エントリを順次処理
- `natorch.cpp`: `NAT_GLOBAL` key != "Values" → `"Invalid key format"` ERROR
- `sonic-nat.yang`: `nat_type default dnat`

## Phase 3: 専用ファイル確認

- `sonic-swss/cfgmgr/natmgrd.cpp`: NAT_GLOBAL → APPL_DB APP_NAT_GLOBAL_TABLE へ転送
- `sonic-swss/orchagent/natorch.cpp`: APPL_DB 消費 → SAI NAT objects
- max-elements: 16 (NAT_POOL), 16 (NAT_BINDINGS)

## Phase 5: 値依存挙動マトリクス

| フィールド | 値 | 挙動 |
|-----------|-----|------|
| `admin_mode` | `disabled` (default) | NAT 無効。pool/binding/static エントリは受け付けるがハードウェアに降ろさない (キュー保持) |
| `admin_mode` | `enabled` | NAT 有効化。キュー内の全エントリを ASIC に反映。conntrack エントリの aging 開始 |
| `nat_timeout` | 600 (default) | 非 TCP/UDP NAT セッションを 600秒でタイムアウト |
| `nat_tcp_timeout` | 86400 (default) | TCP セッションを 24時間でタイムアウト |
| `nat_udp_timeout` | 300 (default) | UDP セッションを 5分でタイムアウト |
| `nat_type` (BINDINGS) | `snat` | 送信元 IP を変換 (内→外方向) |
| `nat_type` (BINDINGS) | `dnat` (default) | 宛先 IP を変換 (外→内方向) |
| `twice_nat_id` | 1..9999 | 同 ID の snat/dnat エントリをペアとして twice NAT 処理 |
| `nat_pool` エントリ上限 | 17件目 | YANG max-elements=16 でバリデーション拒否 |

enum: `admin_mode`=enabled/disabled、`nat_type`=snat/dnat。
