# 値依存挙動分析: MCLAG_DOMAIN / MCLAG_INTERFACE / MCLAG_UNIQUE_IP

## Phase 1: YANG フィールド全列挙

### MCLAG_DOMAIN
- `domain_id` (uint16, key): range 1..4095
- `source_ip` (inet:ipv4-address): ICCP ソース IP
- `peer_ip` (inet:ipv4-address): ICCP ピア IP
- `peer_link` (union leafref): PORT.name または PORTCHANNEL.name
- `keepalive_interval` (uint16): range 1..60, default 1 [秒]
- `session_timeout` (uint16): range 1..3600, default 30 [秒]
- must: `(keepalive_interval * 3) <= session_timeout`

### MCLAG_INTERFACE
- `domain_id` (leafref): MCLAG_DOMAIN.domain_id
- `if_name` (leafref): PORTCHANNEL.name
- `if_type` (string): プレースホルダ

### MCLAG_UNIQUE_IP
- `if_name` (string): pattern `Vlan<id>`
- `unique_ip` (enum `enable`): 有効化フラグ

## Phase 2: per-value explicit grep

- `sonic-mclag.yang`: `must "(keepalive_interval * 3) <= session_timeout"` — タイムアウト比制約
- `mclaglink.cpp`: 差分比較で変化フィールドのみ iccpd へ送信 (`attrBmap`)
- `mclaglink.cpp`: 存在しないドメインへの DEL → `"Domain [%d] deletion - domain not found"` WARN

## Phase 3: 専用ファイル確認

- `sonic-swss/mclagsyncd/mclaglink.cpp`: MCLAG_DOMAIN 変更 → iccpd へ CFG メッセージ転送
- max-elements: 1 (MCLAG_DOMAIN_LIST) — ドメインは 1 件のみ

## Phase 5: 値依存挙動マトリクス

| フィールド | 値 | 挙動 |
|-----------|-----|------|
| `keepalive_interval` | 1 (default) | 1秒ごとに ICCP keepalive 送信 |
| `keepalive_interval` | N (1..60) | N 秒ごとに送信。session_timeout ≥ N*3 が必要 |
| `session_timeout` | 30 (default) | 30秒 ICCP 応答なしでセッション断 |
| `session_timeout` | < keepalive_interval*3 | YANG must 制約違反 → バリデーション拒否 |
| `unique_ip` | `enable` | 当該 VLAN IF に対して ToR 間で異なる IP アドレスを許可 |
| `if_type` (MCLAG_INTERFACE) | 任意文字列 | プレースホルダ。実際の動作に影響なし (エントリ存在でメンバー登録) |

enum: `unique_ip` = `enable` のみ (無効化はエントリ削除)。
