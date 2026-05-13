# 値依存挙動分析: MIRROR_SESSION

## Phase 1: YANG フィールド全列挙

- `name` (string, key): pattern `[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,31})`, length 1..32
- `type` (enum): `ERSPAN`/`SPAN`, default `ERSPAN`
- `src_ip` (ip-address): ERSPAN 時必須
- `dst_ip` (ip-address): ERSPAN 時必須
- `gre_type` (hex/dec uint16): default `0x88be`
- `dscp` (uint8): range 0..63
- `ttl` (uint8): range 0..255
- `queue` (uint8): egress queue
- `dst_port` (leafref PORT.name / "CPU"): SPAN 時
- `src_port` (string 1..2048): ソースポートリスト
- `direction` (enum): `RX`/`TX`/`BOTH`, default `BOTH`
- `policer` (leafref POLICER.name)

## Phase 2: per-value explicit grep

- `mirrororch.cpp`: `MIRROR_SESSION_STATUS_ACTIVE = "active"` / `"inactive"`
- `mirrororch.cpp`: dscp default=8, ttl default=255, queue default=0
- `mirrororch.cpp`: `entry.queue >= m_maxNumTC` → `"Failed to get valid queue"` + task_invalid_entry
- `mirrororch.cpp`: session の nexthop が解決できない → inactive (route attach 待ち)

## Phase 3: 専用ファイル確認

- `sonic-swss/orchagent/mirrororch.cpp`: type=ERSPAN → routeOrch へ dstIp を attach。nexthop 解決で active
- type=SPAN → dst_port の物理ポート解決で active。LAG src_port 空は inactive
- `STATE_DB MIRROR_SESSION_TABLE`: session 状態 ("active"/"inactive") を反映

## Phase 5: 値依存挙動マトリクス

| フィールド | 値 | 挙動 |
|-----------|-----|------|
| `type` | `ERSPAN` (default) | GRE/IP ヘッダ付きで dst_ip へ転送。routeOrch に dstIp を attach して nexthop 解決 |
| `type` | `SPAN` | ローカル物理ポート (dst_port) に転送。nexthop 解決なし |
| `direction` | `RX` | 受信パケットのみミラー |
| `direction` | `TX` | 送信パケットのみミラー |
| `direction` | `BOTH` (default) | 送受信両方をミラー |
| `gre_type` | `0x88be` (default) | ERSPAN Type II (Cisco) GRE EtherType |
| `gre_type` | `0x8949` | ERSPAN Type III (Broadcom) GRE EtherType |
| `queue` | 0 (default) | best-effort queue でミラーパケット送出 |
| `queue` | ≥ m_maxNumTC | task_invalid_entry — HW TC 数超過 |
| `policer` | 指定あり | ミラートラフィックにレート制限を適用 |
| `policer` | 未存在 leafref | task_need_retry — policer 追加後に再処理 |

セッション状態は STATE_DB `MIRROR_SESSION_TABLE` の `status` フィールド ("active"/"inactive") で確認。
