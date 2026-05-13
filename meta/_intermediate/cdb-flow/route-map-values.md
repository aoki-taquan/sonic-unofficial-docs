# ROUTE_MAP — 値依存挙動分析

## Phase 1: YANG フィールド全列挙

- `route_operation`: enum `PERMIT` / `DENY`
- `match_interface`: union leafref
- `match_prefix_set` / `match_ipv6_prefix_set` / `match_next_hop_set`: leafref `PREFIX_SET.name`
- `match_protocol`: 文字列（bgp/connected/ospf/ospf3/static）
- `match_src_vrf`: union（`default` / leafref `VRF.name`）
- `match_neighbor`: leaf-list union
- `match_tag`: leaf-list uint32
- `match_med` / `match_local_pref`: uint32
- `match_origin`: 文字列
- `match_community`: leafref `COMMUNITY_SET.name`
- `match_ext_community`: leafref `EXTENDED_COMMUNITY_SET.name`
- `match_as_path`: leafref `AS_PATH_SET.name`
- `call_route_map`: leafref `ROUTE_MAP_SET.name`
- `set_origin`: 文字列
- `set_local_pref` / `set_med` / `set_metric`: uint32
- `set_metric_action`: enum `metric-action-type`
- `set_next_hop`: 文字列
- `set_ipv6_next_hop_global` / `set_ipv6_next_hop_prefer_global`: 文字列 / boolean
- `set_repeat_asn` / `set_asn` / `set_asn_list`: numeric / 文字列
- `set_community_inline` / `set_community_ref`: leaf-list / leafref
- `set_ext_community_inline` / `set_ext_community_ref`: leaf-list / leafref
- `set_tag`: uint32

## Phase 2: per-value 挙動

### `route_operation` 値別挙動
| 値 | 挙動 |
|----|------|
| `PERMIT` | match した場合に経路を許可し、set アクションを適用。 |
| `DENY` | match した場合に経路を拒否（DROP）。set アクションは無視。 |

### `set_metric_action` 値別挙動
| 値 | 挙動 |
|----|------|
| `METRIC_SET_VALUE` | MED を `set_metric` の値に設定。 |
| `METRIC_ADD_VALUE` | MED を `set_metric` 分加算。 |
| `METRIC_SUBTRACT_VALUE` | MED を `set_metric` 分減算。 |
| `METRIC_SET_RTT` | MED を RTT 値に設定。 |
| `METRIC_ADD_RTT` | MED に RTT を加算。 |
| `METRIC_SUBTRACT_RTT` | MED から RTT を減算。 |

### BGPRouteMapMgr の key 制限
| key 値 | 挙動 |
|--------|------|
| `FROM_SDN_SLB_ROUTES` | 有効。SDN SLB ユースケース用。 |
| `FROM_SDN_APPLIANCE_ROUTES` | 有効。SDN Appliance ユースケース用。 |
| その他 | `log_err("BGPRouteMapMgr:: Invalid key for route-map %s")` → 拒否。汎用 route-map は bgpcfgd テンプレート経由で管理。 |

## Phase 3: ソース確認

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_rm.py`: `ROUTE_MAPS = ["FROM_SDN_SLB_ROUTES", "FROM_SDN_APPLIANCE_ROUTES"]` で処理対象を限定。`community_id` は `<0-65535>:<0-65535>` 形式チェック。
- `managers_rm.py:76-81`: `deployment_id_asn_map` が constants に存在しない場合はスキップ。

## enum 有無

- `route_operation`: YANG enum `PERMIT` / `DENY`
- `set_metric_action`: YANG enum `metric-action-type` (METRIC_SET_VALUE / METRIC_ADD_VALUE / METRIC_SUBTRACT_VALUE / METRIC_SET_RTT / METRIC_ADD_RTT / METRIC_SUBTRACT_RTT)
- `match_protocol`: enum なし（文字列）
