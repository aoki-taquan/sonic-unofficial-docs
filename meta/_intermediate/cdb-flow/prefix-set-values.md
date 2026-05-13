# PREFIX_SET — 値依存挙動分析

## Phase 1: YANG フィールド全列挙

- `name` (key): 文字列（prefix set 名）
- `mode`: enum `IPv4` / `IPv6`。デフォルト `IPv4`。
- `PREFIX_LIST.sequence_number`: uint32 1..4294967295
- `PREFIX_LIST.action`: enum `permit` / `deny`
- `PREFIX_LIST.masklength_range`: 文字列 `exact` または `lo..hi` 形式
- `PREFIX_NOSEQ_LIST.action`: enum `permit` / `deny`

## Phase 2: per-value 挙動

### `mode` 値別挙動
| 値 | 挙動 |
|----|------|
| `IPv4` | デフォルト。FRR の `ip prefix-list` に展開。IPv6 prefix を混在させると FRR が syntax エラー。 |
| `IPv6` | FRR の `ipv6 prefix-list` に展開。IPv4 prefix との混在は FRR エラー。 |

### `action` 値別挙動（PREFIX_LIST / PREFIX_NOSEQ_LIST 共通）
| 値 | 挙動 |
|----|------|
| `permit` | プレフィクスを許可。FRR に `permit` で展開。 |
| `deny` | プレフィクスを拒否。FRR に `deny` で展開。 |

### `masklength_range` 値別挙動
| 値 | 挙動 |
|----|------|
| `exact` | プレフィクス長を完全一致で評価。FRR に `ge <len> le <len>` なし。 |
| `lo..hi` 形式 | 範囲指定。FRR の `ge lo le hi` に変換。 |

## Phase 3: ソース確認

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-routing-policy-sets.yang`: `mode` の enum 定義、`action` の `routing-policy-action-type` typedef、`masklength_range` の pattern 制約。
- bgpcfgd 直接 consumer なし。`frr-mgmt-framework` または `sonic-cfggen` が展開。

## enum 有無

- `mode`: YANG enum `IPv4` / `IPv6`
- `action`: YANG enum `permit` / `deny`
- `masklength_range`: enum なし（文字列パターン制約）
