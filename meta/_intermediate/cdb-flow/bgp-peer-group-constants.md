# BGP_PEER_GROUP ハードコード定数分析 (Phase E)

生成日: 2026-05-16
対象ページ: `docs/reference/config-db/bgp-peer-group.md`

## 分析ソース

| ファイル | パス |
|---------|------|
| frrcfgd.py | `src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` |
| managers_bgp.py | `src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` |
| general/peer-group.conf.j2 | `dockers/docker-fpm-frr/frr/bgpd/templates/general/peer-group.conf.j2` |
| general/policies.conf.j2 | `dockers/docker-fpm-frr/frr/bgpd/templates/general/policies.conf.j2` |
| internal/peer-group.conf.j2 | `dockers/docker-fpm-frr/frr/bgpd/templates/internal/peer-group.conf.j2` |
| internal/policies.conf.j2 | `dockers/docker-fpm-frr/frr/bgpd/templates/internal/policies.conf.j2` |
| voq_chassis/peer-group.conf.j2 | `dockers/docker-fpm-frr/frr/bgpd/templates/voq_chassis/peer-group.conf.j2` |
| voq_chassis/policies.conf.j2 | `dockers/docker-fpm-frr/frr/bgpd/templates/voq_chassis/policies.conf.j2` |
| monitors/peer-group.conf.j2 | `dockers/docker-fpm-frr/frr/bgpd/templates/monitors/peer-group.conf.j2` |

## 検出定数一覧

### 1. peer-group 名（テンプレートにハードコード）

bgpcfgd はテンプレートディレクトリを `peer_type` で選択し、テンプレート内にある固定名の peer-group を生成する。

| テンプレートディレクトリ | peer-group 名 | 選択条件 |
|---------------------|-------------|---------|
| `general/` | `PEER_V4`, `PEER_V6` | `peer_type == 'external'` / `general` |
| `internal/` | `INTERNAL_PEER_V4`, `INTERNAL_PEER_V6` | `peer_type == 'internal'` |
| `BGPMON/` (monitors/) | `BGPMON` | BGP Monitor neighbor |
| `voq_chassis/` | `VOQ_CHASSIS_V4_PEER`, `VOQ_CHASSIS_V6_PEER` | VoQ chassis peer |

### 2. route-map 名（ポリシーテンプレート内）

route-map 名は CONFIG_DB の `BGP_PEER_GROUP_AF.route_map_in` / `route_map_out` とは独立し、テンプレートにハードコードされる。

| テンプレート | inbound route-map | outbound route-map |
|-----------|-----------------|------------------|
| general | `FROM_BGP_PEER_V4` / `FROM_BGP_PEER_V6` | `TO_BGP_PEER_V4` / `TO_BGP_PEER_V6` |
| internal | `FROM_BGP_INTERNAL_PEER_V4` / `FROM_BGP_INTERNAL_PEER_V6` | `TO_BGP_INTERNAL_PEER_V4` / `TO_BGP_INTERNAL_PEER_V6` |
| BGPMON | `FROM_BGPMON` | `TO_BGPMON` |
| voq_chassis | `FROM_VOQ_CHASSIS_V4_PEER` / `FROM_VOQ_CHASSIS_V6_PEER` | `TO_VOQ_CHASSIS_V4_PEER` / `TO_VOQ_CHASSIS_V6_PEER` |

### 3. keepalive / holdtime デフォルト（frrcfgd 経路）

frrcfgd.py L1874 の `comb_attr_list` 制約:

```python
(['keepalive', 'holdtime'], '{no:no-prefix}neighbor {} timers {} {}'),
```

`keepalive` と `holdtime` が **両方** CONFIG_DB に存在しない場合、FRR タイマーコマンドは生成されず、FRR のデフォルト値（keepalive=60秒、holdtime=180秒）が適用される。

### 4. peer-group 固定属性（bgpcfgd テンプレート経由）

#### general テンプレート固定値
- `soft-reconfiguration inbound`: 常時
- `allowas-in 1`: ToRRouter / LeafRouter+BBR enabled 時
- `table-map SELECTIVE_ROUTE_DOWNLOAD_V4/V6`: SpineRouter UpstreamLC または UpperSpineRouter 時

#### internal テンプレート固定値
- `allowas-in 1`: 常時
- `soft-reconfiguration inbound`: 常時
- `send-community`: 常時
- `route-reflector-client`: BackEnd sub_role 時
- `update-source Loopback4096`: chassis-packet switch_type 時
- `ttl-security hops 1`: chassis-packet switch_type 時

#### BGPMON テンプレート固定値
- `maximum-prefix 1`: 常時（IPv4/IPv6）
- `send-community`: 常時
- `update-source Loopback4096`: VoQ または chassis-packet 時

#### voq_chassis テンプレート固定値
- `addpath-tx-all-paths`: 常時（IPv4/IPv6）
- `soft-reconfiguration inbound`: 常時
- `send-community`: 常時
- `allowas-in 1`: ToRRouter 時

### 5. policies.conf.j2 の `constants.bgp.*` 注入値

runtime 定数（`constants.json` 経由）。テスト参照値は bgpcfgd テストデータから。

#### general テンプレート
| 定数キー | テスト値 | 用途 |
|---------|---------|------|
| `allow_list.drop_community` | `12345:12345` | allow_list deny 時の community |
| `route_eligible_for_fallback_to_default_tag` | `203` | UpstreamLC SpineRouter の fallback tag |
| `route_do_not_send_appdb_tag` | `202` | UpstreamLC SpineRouter の no-appdb tag |
| `internal_fallback_community` | `1111:2222` | INTERNAL_FALLBACK_COMMUNITY |
| `local_anchor_route_community` | `12345:555` | LOCAL_ANCHOR_ROUTE_COMMUNITY |
| `anchor_route_community` | `12345:666` | ANCHOR_ROUTE_COMMUNITY |
| `anchor_contributing_route_community` | `12345:777` | ANCHOR_CONTRIBUTING_ROUTE_COMMUNITY |

#### voq_chassis テンプレート
| 定数キー | テスト値 | 用途 |
|---------|---------|------|
| `internal_community` | `12345:556` | DEVICE_INTERNAL_COMMUNITY |
| `internal_fallback_community` | `1111:2222` | DEVICE_INTERNAL_FALLBACK_COMMUNITY |
| `local_anchor_route_community` | `12345:555` | LOCAL_ANCHOR_ROUTE_COMMUNITY |
| `internal_community_match_tag` | `101` | DEVICE_INTERNAL_COMMUNITY match tag |
| `route_eligible_for_fallback_to_default_tag` | `203` | fallback tag（非 UpstreamLC） |
| local-preference (NO_EXPORT) | `80` | set local-preference 固定値 |

## frrcfgd 経路との差異

frrcfgd 経路（`frr_mgmt_framework_config=true`）では：
- peer-group 名は CONFIG_DB の `BGP_PEER_GROUP|<vrf>|<name>` のキー値をそのまま使用（ハードコードなし）
- `route_map_in` / `route_map_out` は `BGP_PEER_GROUP_AF` フィールド値を使用
- keepalive/holdtime は CONFIG_DB フィールド値（両方揃い時のみ投入）

bgpcfgd 経路（`frr_mgmt_framework_config=false` または未設定）では：
- テンプレートにハードコードされた peer-group 名・route-map 名が使われる
- テンプレートが条件付きで固定設定（allowas-in、soft-reconfiguration 等）を投入
