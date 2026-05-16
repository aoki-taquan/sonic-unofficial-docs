# BGP_ALLOWED_PREFIXES — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_allow_list.py` (route-map / prefix-list 名テンプレート、seq 範囲、AF 定数)
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/general/policies.conf.j2` (FROM_BGP_PEER_V4/V6 / ALLOW_LIST_DEPLOYMENT_ID_0 テンプレート、`allow_list_default_community`、seq 65535)

---

## 1. route-map / prefix-list / community 名テンプレート (managers_allow_list.py L16-21)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `PL_NAME_TMPL` | `"PL_ALLOW_LIST_DEPLOYMENT_ID_%d_COMMUNITY_%s_V%s"` | community 単位の prefix-list 名 (deployment_id, community, v4/v6) | managers_allow_list.py L16 |
| `PL_NAME_TMPL_WITH_NEIGH` | `"PL_ALLOW_LIST_DEPLOYMENT_ID_%d_NEIGHBOR_%s_COMMUNITY_%s_V%s"` | neighbor_type を含む prefix-list 名 | managers_allow_list.py L17 |
| `COMMUNITY_NAME_TMPL` | `"COMMUNITY_ALLOW_LIST_DEPLOYMENT_ID_%d_COMMUNITY_%s"` | community-list 名 (deployment_id, community) | managers_allow_list.py L18 |
| `COMMUNITY_NAME_TMPL_WITH_NEIGH` | `"COMMUNITY_ALLOW_LIST_DEPLOYMENT_ID_%d_NEIGHBOR_%s_COMMUNITY_%s"` | neighbor_type を含む community-list 名 | managers_allow_list.py L19 |
| `RM_NAME_TMPL` | `"ALLOW_LIST_DEPLOYMENT_ID_%d_V%s"` | deployment 単位 route-map 名 (v4/v6) | managers_allow_list.py L20 |
| `RM_NAME_TMPL_WITH_NEIGH` | `"ALLOW_LIST_DEPLOYMENT_ID_%d_NEIGHBOR_%s_V%s"` | neighbor_type を含む route-map 名 | managers_allow_list.py L21 |

> deployment_id=0 (テンプレ既定) では、`ALLOW_LIST_DEPLOYMENT_ID_0_V4` / `ALLOW_LIST_DEPLOYMENT_ID_0_V6` という固定名が `policies.conf.j2` (L17,L20,L24,L27) で参照される。

---

## 2. FROM_BGP_PEER テンプレート (policies.conf.j2 L34-79)

`route-map FROM_BGP_PEER_V4` / `FROM_BGP_PEER_V6` は **固定 5 段構成** (permit 10/11/12/13/100):

| seq | 役割 | switch_type='chassis-packet' 時の分岐 |
|-----|------|---------------------------------------|
| 10  | `call ALLOW_LIST_DEPLOYMENT_ID_0_V{4,6}` + `on-match next` (deployment_id=0 の allow-list を呼び出す) | 分岐なし |
| 11  | `match community allow_list_default_community` (community-list 名はハードコード) | UpstreamLC な SpineRouter 以外では permit 12/13 ブロック自体が出力されず素通り |
| 12  | `match ip{,v6} address prefix-list DEFAULT_IPV{4,6}` (デフォルト経路マッチ) | 同上 |
| 13  | `set tag <appdb_tag|fallback_to_default_tag>` + `set community internal_fallback_community additive` | tag が `route_do_not_send_appdb_tag` → `route_eligible_for_fallback_to_default_tag` に切替 |
| 100 | 終端 permit (素通り) | 分岐なし |

加えて V6 のみ permit 1 で `on-match next` + `set ipv6 next-hop prefer-global` (L90-92, IPv6 next-hop preference)。

| 関連定数 (j2 から参照) | ソース | 備考 |
|------------------------|--------|------|
| `DEFAULT_IPV4` prefix-list | policies.conf.j2 L5 | `permit 0.0.0.0/0` (固定) |
| `DEFAULT_IPV6` prefix-list | policies.conf.j2 L6 | `permit ::/0` (固定) |
| `allow_list_default_community` (community-list 名) | policies.conf.j2 L31-32 | 固定文字列。`no-export` と `constants.bgp.allow_list.drop_community` (`5060:12345`) の 2 メンバを permit |
| `constants.bgp.route_do_not_send_appdb_tag` | policies.conf.j2 L48,L71 | 非 chassis-packet 用 tag (constants.yml 由来) |
| `constants.bgp.route_eligible_for_fallback_to_default_tag` | policies.conf.j2 L50,L73 | chassis-packet LC 用 tag |
| `constants.bgp.internal_fallback_community` | policies.conf.j2 L52,L75 | seq 13 で additive 付与する community |

> permit 12/13 ブロックは `type=='SpineRouter' and subtype=='UpstreamLC'` でのみ出力 (policies.conf.j2 L41-42, L64-65)。それ以外のロールでは ALLOW_LIST 不一致経路は seq 11 → seq 100 で素通り。

---

## 3. route-map seq 番号定数 (managers_allow_list.py L22-25, L441-450)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `ROUTE_MAP_ENTRY_WITH_COMMUNITY_START` | `10` | community 付きエントリの seq 範囲下限 | managers_allow_list.py L22 |
| `ROUTE_MAP_ENTRY_WITH_COMMUNITY_END` | `29990` | community 付きエントリの seq 範囲上限 | managers_allow_list.py L23 |
| `ROUTE_MAP_ENTRY_WITHOUT_COMMUNITY_START` | `30000` | community なしエントリの seq 範囲下限 | managers_allow_list.py L24 |
| `ROUTE_MAP_ENTRY_WITHOUT_COMMUNITY_END` | `65530` | community なしエントリの seq 範囲上限 | managers_allow_list.py L25 |
| default action 末尾 seq | `65535` (ハードコード) | `route-map ALLOW_LIST_DEPLOYMENT_ID_*_V{4,6} permit 65535` (default_action 用エントリ) | managers_allow_list.py L441,L450,L463,L476,L481,L511,L556 / policies.conf.j2 L17,L20,L24,L27 |
| seq 増分 | `10` | `__find_next_seq_number` は `range(start, end, 10)` で 10 刻み割当 | managers_allow_list.py L585 |

> seq 65535 は「default action 用 末尾ルール」(`# please don't remove. 65535 entries are default rules`、policies.conf.j2 L11) として `bgpcfgd` 起動時に j2 で先行投入され、`managers_allow_list.py` の `__get_default_action_community` (L463-481) が後から `set community` を書換える。

---

## 4. address-family 定数 (managers_allow_list.py L28-29)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `V4` | `"v4"` | address-family enum: IPv4 識別子 | managers_allow_list.py L28 |
| `V6` | `"v6"` | address-family enum: IPv6 識別子 | managers_allow_list.py L29 |
| `EMPTY_COMMUNITY` | `"empty"` | community 未指定キー時のセンチネル文字列 (`PL_ALLOW_LIST_DEPLOYMENT_ID_%d_COMMUNITY_empty_V%s` 等で展開) | managers_allow_list.py L15 |

---

## 5. prefix mask デフォルト (managers_allow_list.py L744)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `prefix_mask_default` (IPv4) | `32` | `__to_prefix_list` 内で `le`/`ge` 修飾子なしの IPv4 prefix のマスク長 (host route) と比較。マスク長が 32 未満なら `le 32` を自動付与 | managers_allow_list.py L744 |
| `prefix_mask_default` (IPv6) | `128` | 同上の IPv6 版 (host route)。マスク長が 128 未満なら `le 128` を自動付与 | managers_allow_list.py L744 |

> 例: `10.0.0.0/8` → `permit 10.0.0.0/8 le 32` / `2001:db8::/32` → `permit 2001:db8::/32 le 128` / `192.0.2.1/32` (=host) → `permit 192.0.2.1/32` (補完なし)。

---

## 6. prefix_match_tag (managers_allow_list.py L657-664, L434-435)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `prefix_match_tag` | `constants["bgp"]["allow_list"]["prefix_match_tag"]` の値 (未定義時は `None`) | community のないエントリに `set tag <prefix_match_tag>` を付与。`None` の場合は `set tag` 行を生成しない | managers_allow_list.py L657-664, L434-435 |

> 同名のクラス属性 (L46 で `__init__` 内で初期化) と j2 側の `route_do_not_send_appdb_tag` / `route_eligible_for_fallback_to_default_tag` は別概念。`prefix_match_tag` は `managers_allow_list.py` が community なしの route-map entry に貼る tag で、`policies.conf.j2` 内の `FROM_BGP_PEER_V*` seq 13 の tag とは独立。

---

## 特記事項

1. **seq 65535 はテンプレート時点で固定埋め込み**: `policies.conf.j2` L17,L20,L24,L27 で `permit 65535` を bgpd 起動時に投入し、CONFIG_DB に `BGP_ALLOWED_PREFIXES` が 1 件も書かれていない状態でも `ALLOW_LIST_DEPLOYMENT_ID_0_V4/V6` route-map に「default action」エントリが存在する。`managers_allow_list.py` の `__get_default_action_community` (L463-481) は SET 時にこの 65535 エントリを再書換する。
2. **seq 65535 は `ROUTE_MAP_ENTRY_WITHOUT_COMMUNITY_END = 65530` の外側**: 動的割当 (`__find_next_seq_number`) は 65530 で打ち止めなので、65535 と動的エントリが衝突することはない。
3. **`PL_NAME_TMPL` の `COMMUNITY_%s` 部分**: community が未指定のキー (例: `BGP_ALLOWED_PREFIXES|DEPLOYMENT_ID|0`) では `EMPTY_COMMUNITY` (`"empty"`) が展開され、`PL_ALLOW_LIST_DEPLOYMENT_ID_0_COMMUNITY_empty_V4` のような prefix-list 名が生成される。
4. **`allow_list_default_community` community-list 名はハードコード**: `policies.conf.j2` L31-32, L39, L62 でリテラル展開され、`managers_allow_list.py` 側にも対応する定数定義はない。設定で変更不可。
5. **`DEFAULT_IPV4` / `DEFAULT_IPV6` prefix-list 名もハードコード**: policies.conf.j2 L5-6 でテンプレ生成時に固定投入。`FROM_BGP_PEER_V*` seq 12 (UpstreamLC SpineRouter のみ) で参照される。
6. **`le` 自動補完は `le`/`ge` 文字列マッチで判定**: `'le' in prefix or 'ge' in prefix` (L739) なので、prefix 文字列中の任意箇所に `le` / `ge` の 2 文字が含まれると補完がスキップされる。IPv6 アドレスに `le`/`ge` の文字列が偶然含まれる可能性は低いが要注意。

---

## 出典

- `sonic-net/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_allow_list.py` L15-29, L46, L434-435, L441-481, L511, L556, L580-585, L657-664, L736-754
- `sonic-net/sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/general/policies.conf.j2` L1-95
