# PREFIX_LIST (BGP) — 値依存挙動分析

## Phase 1: YANG フィールド全列挙

- `prefix_type` (key): 任意文字列（リスト名）。サポートされる値は `ANCHOR_PREFIX` / `SUPPRESS_PREFIX` のみ。それ以外は `log_warn` でスキップ。
- `ip-prefix` (key): `stypes:sonic-ip4-prefix` / `sonic-ip6-prefix` の union。CIDR 形式。
- `family`: enum `IPv4` / `IPv6`。`must` 制約で `ip-prefix` との整合性チェック。

## Phase 2: per-value 挙動

### `prefix_type` 値別挙動
| 値 | 挙動 |
|----|------|
| `ANCHOR_PREFIX` | SpineRouter/UpstreamLC または UpperSpineRouter のみ許可。他デバイスは `log_warn` してスキップ。FRR の anchor prefix list に展開。 |
| `SUPPRESS_PREFIX` | 全デバイスタイプで許可。FRR の suppress prefix list に展開。 |
| その他 | `log_warn("PrefixListMgr:: Prefix type '...' is not supported")` → スキップ。FRR への設定生成は行われない。 |

### `family` 値別挙動
| 値 | 挙動 |
|----|------|
| `IPv4` | `ip-prefix` に `.` を含む YANG `must` 制約。FRR の `ip prefix-list` に展開。 |
| `IPv6` | `ip-prefix` に `:` を含む YANG `must` 制約。FRR の `ipv6 prefix-list` に展開。 |

## Phase 3: ソース確認

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_prefix_list.py`: `PREFIX_TYPE_CONFIG` dict で `ANCHOR_PREFIX` / `SUPPRESS_PREFIX` を定義。`generate_prefix_list_config()` が type_cfg を取得し、None の場合は `log_warn` してスキップ。
- `sonic-bgpcfgd/bgpcfgd/managers_prefix_list.py:49-55`: `_is_device_allowed()` でデバイスタイプ制限を実装。

## Phase 4: 複合条件

- `prefix_type=ANCHOR_PREFIX` かつ `device_type=LeafRouter`: 拒否される。SpineRouter/UpstreamLC か UpperSpineRouter のみ許可。
- `ip-prefix` 形式不正: `netaddr.IPNetwork()` が `NotRegisteredError` / `AddrFormatError` / `AddrConversionError` → `log_warn` してスキップ。

## enum 有無

- `prefix_type`: enum ではなく文字列だが事実上 `ANCHOR_PREFIX` / `SUPPRESS_PREFIX` の 2 値のみ有効
- `family`: YANG enum `IPv4` / `IPv6`
