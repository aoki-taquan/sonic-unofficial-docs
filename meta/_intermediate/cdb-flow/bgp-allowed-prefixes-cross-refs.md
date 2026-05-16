# BGP_ALLOWED_PREFIXES テーブル 暗黙参照スキャン (Phase C / Task F)

`docs/reference/config-db/bgp-allowed-prefixes.md` の暗黙参照 (`<!-- cross-refs -->`) ブロック裏付け資料。

ソースは:

- `sonic-net/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_allow_list.py`
- `sonic-net/sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/general/policies.conf.j2`

`BGP_ALLOWED_PREFIXES_*` テーブル変更時に `bgpcfgd` の `BGPAllowListMgr` および FRR 設定生成 Jinja テンプレが間接的に読み出す関連 CONFIG_DB エンティティと、`constants.yml` 由来のグローバル設定を列挙する。

## スキャン手順

```
grep -nE 'EMPTY_COMMUNITY|deployment_id|peer_group|neighbor_type|constants|CommunityList' \
    .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_allow_list.py

grep -nE 'CONFIG_DB__DEVICE_METADATA|community-list|constants\.bgp' \
    .cache/sonic-sources/sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/general/policies.conf.j2
```

## 検出された暗黙参照

### 1. FRR community-list (`allow_list_default_community`)

`BGP_ALLOWED_PREFIXES` の `default_action` 値は CONFIG_DB に直接 `permit` / `deny` として保存されるが、`BGPAllowListMgr.__get_default_action_community()` (`managers_allow_list.py:773-785`) により、適用時に **community 値** に変換される:

| `default_action` | 出力 community | 参照される FRR community-list |
|---|---|---|
| `permit` | `constants.bgp.allow_list.drop_community` (例: `5060:12345`) | `allow_list_default_community` |
| `deny` | `no-export` | `allow_list_default_community` |

community-list `allow_list_default_community` は `policies.conf.j2:31-32` で **テンプレ生成時に必ず定義** される (CONFIG_DB の `BGP_COMMUNITY_LIST` テーブルとは独立)。

| エンティティ | 種別 | 関係 | evidence |
|---|---|---|---|
| `allow_list_default_community` | FRR community-list (テンプレ生成) | `default_action` の効果を担う | `policies.conf.j2:31-32`, `managers_allow_list.py:773-785` |
| `BGP_COMMUNITY_LIST` (CONFIG_DB) | CONFIG_DB テーブル | **直接参照なし**。FRR の community-list は `policies.conf.j2` がテンプレ生成するため、CONFIG_DB の `BGP_COMMUNITY_LIST` とは別経路 | (grep 0 ヒット) |

> 注: `BGP_COMMUNITY_LIST` テーブルは別の `BgpCommunityMgr` が処理する経路で、`BGP_ALLOWED_PREFIXES` フローからは参照されない。ただし FRR レベルでは同一 BGP セッションに対して両 community-list が同居する可能性がある (隣接情報として記載)。

### 2. `DEVICE_METADATA` (CONFIG_DB)

`policies.conf.j2` が `CONFIG_DB__DEVICE_METADATA['localhost']` の 3 フィールドを読み、テンプレ分岐に使用:

| フィールド | 役割 | 参照箇所 |
|---|---|---|
| `type` | `SpineRouter` / `UpperSpineRouter` で route-map permit 12/13 (DEFAULT prefix 経路) を生成するか分岐 | `policies.conf.j2:41,64,104-105` |
| `subtype` | `UpstreamLC` で上記分岐をさらに絞り込む | `policies.conf.j2:41,64,104` |
| `switch_type` | `chassis-packet` で `set tag` を `route_do_not_send_appdb_tag` ↔ `route_eligible_for_fallback_to_default_tag` に切替 | `policies.conf.j2:48,71` |

> `DEVICE_METADATA.localhost.bgp_asn` は `BGP_ALLOWED_PREFIXES` フローでは**直接参照されない**。`policies.conf.j2` (general/) を `bgp_asn` で grep して 0 ヒット。`bgp_asn` を読むのは別の `bgpd.conf.j2` / `instance.conf.j2` 系テンプレで、ALLOW_LIST のルートマップは AS 番号に依存しない (community/tag ベース)。

| エンティティ | 種別 | 関係 | evidence |
|---|---|---|---|
| `DEVICE_METADATA.localhost.type` | CONFIG_DB フィールド | route-map permit 12/13 生成の前提条件 | `policies.conf.j2:41,64,104-105` |
| `DEVICE_METADATA.localhost.subtype` | CONFIG_DB フィールド | 同上 (UpstreamLC 限定) | `policies.conf.j2:41,64,104` |
| `DEVICE_METADATA.localhost.switch_type` | CONFIG_DB フィールド | `set tag` の選択 (chassis-packet 分岐) | `policies.conf.j2:48,71` |
| `DEVICE_METADATA.localhost.bgp_asn` | CONFIG_DB フィールド | **無関係** (ALLOW_LIST 経路は AS 番号非依存) | (grep 0 ヒット) |
| `DEVICE_METADATA.localhost.deployment_id` | CONFIG_DB フィールド | **直接参照なし**。ただし論理的に `BGP_ALLOWED_PREFIXES` の `<id>` キー値とローカル `deployment_id` が一致したときに自局向けポリシーになる (運用上の対応関係) | `managers_allow_list.py:63-69`, minigraph 由来 |

### 3. `BGP_GLOBALS` (CONFIG_DB)

`managers_allow_list.py` および `policies.conf.j2` (general/) を `BGP_GLOBALS` で grep して **0 ヒット**。`BGP_ALLOWED_PREFIXES` フローからは**直接参照されない**。

> `BGP_GLOBALS` は `bgpcfgd` の別マネージャ (`BGPCfgMgr` 系) が処理する経路で、FRR の `router bgp <asn>` ブロック側に流れる。ALLOW_LIST は peer-group / route-map レイヤで完結するため `BGP_GLOBALS` への依存はない。隣接テーブルとして関連リファレンスに留める。

### 4. peer-group / neighbor (FRR running-config 経由の動的解決)

`BGPAllowListMgr.__find_peer_group()` (`managers_allow_list.py:686-697`) は **CONFIG_DB を直接読まず、FRR `cfg_mgr.get_text()` (running-config テキスト) を正規表現で解析** して peer-group を抽出する:

| 検索パターン | 抽出対象 | 用途 |
|---|---|---|
| `^\s*neighbor (\S+) peer-group$` | peer-group 名 (`__extract_peer_group_names`) | 全 peer-group 列挙 (`managers_allow_list.py:601`) |
| `^\s*neighbor <pg> route-map (\S+) in$` | peer-group → in-route-map 対応 | `__get_peer_group_to_route_map` (`managers_allow_list.py:618`) |
| `^\s*call (\S+)$` | route-map call 先 → ALLOW_LIST route-map 名前空間 | `__get_route_map_calls` (`managers_allow_list.py:634`) |

最終的に `ALLOW_LIST_DEPLOYMENT_ID_%d_(NEIGHBOR_%s_)?V<af>` という命名規約で peer-group を絞り込み、`cfg_mgr.restart_peer_groups()` で対象 peer-group のみ soft clear する。

| エンティティ | 種別 | 関係 | evidence |
|---|---|---|---|
| `BGP_PEER_GROUP` (CONFIG_DB) | CONFIG_DB テーブル | **直接参照なし**。FRR running-config 経由で間接利用 | `managers_allow_list.py:601-607,686-697` |
| `BGP_NEIGHBOR` (CONFIG_DB) | CONFIG_DB テーブル | 同上 (peer-group が neighbor に紐付くため間接的) | 同上 |

> ALLOW_LIST 変更時に restart される peer-group は FRR の生 config から逆引きする設計のため、CONFIG_DB レベルでは `BGP_PEER_GROUP` / `BGP_NEIGHBOR` の **読み合いは発生しない**。ただし運用上は両テーブル経由で peer-group 名が定義されるため隣接リファレンスとして関連付ける。

### 5. `constants.yml` (CONFIG_DB 外部)

CONFIG_DB ではないが、`BGP_ALLOWED_PREFIXES` の挙動を決定する**最重要外部依存**:

| キー | 用途 | 参照箇所 |
|---|---|---|
| `bgp.allow_list.enabled` | 機能 ON/OFF (false なら SET/DEL 全 skip) | `managers_allow_list.py:699-707` |
| `bgp.allow_list.default_action` | `default_action` 省略時のフォールバック | `managers_allow_list.py:773-785` |
| `bgp.allow_list.drop_community` | `permit` の community 変換先 | `managers_allow_list.py:780`, `policies.conf.j2:25,28,32` |
| `bgp.allow_list.default_pl_rules.v4` | prefix-list 先頭 prepend (例: `deny 0.0.0.0/0 le 17`) | `managers_allow_list.py:265,709-723` |
| `bgp.allow_list.default_pl_rules.v6` | 同 v6 | 同上 |
| `bgp.allow_list.prefix_match_tag` | route-map `set tag` 行の生成有無 | `managers_allow_list.py:652-664` |

## まとめ — `bgp-allowed-prefixes.md` Phase C 記載対象

| カテゴリ | エンティティ | 種別 |
|---|---|---|
| 値変換先 (community-list, テンプレ生成) | `allow_list_default_community` | FRR community-list (`policies.conf.j2` 生成) |
| テンプレ分岐 (DEVICE_METADATA) | `DEVICE_METADATA.localhost.type` / `.subtype` / `.switch_type` | CONFIG_DB フィールド |
| 論理対応 (deployment_id) | `DEVICE_METADATA.localhost.deployment_id` | CONFIG_DB フィールド (自局判定) |
| FRR running-config 経由間接利用 | `BGP_PEER_GROUP` / `BGP_NEIGHBOR` | CONFIG_DB テーブル |
| グローバル外部依存 | `constants.yml` (`bgp.allow_list.*`) | CONFIG_DB 外 |

## 明示的に **無関係** と確認した参照候補

| 候補 | 確認内容 |
|---|---|
| `BGP_COMMUNITY_LIST` (CONFIG_DB) | `BGPAllowListMgr` から直接参照なし。`allow_list_default_community` は `policies.conf.j2` がテンプレ生成し、`BGP_COMMUNITY_LIST` 経由ではない |
| `BGP_GLOBALS` (CONFIG_DB) | `managers_allow_list.py` および ALLOW_LIST 経路の `policies.conf.j2` 両方を `BGP_GLOBALS` で grep して 0 ヒット |
| `DEVICE_METADATA.localhost.bgp_asn` | `policies.conf.j2` (general/) を `bgp_asn` で grep して 0 ヒット。ALLOW_LIST 経路は AS 番号非依存 (community/tag ベース) |
| `ROUTE_MAP_SET` (CONFIG_DB) | `BGPAllowListMgr` は **vtysh** に直接 route-map 文を流すため、`ROUTE_MAP_SET` テーブルとは別経路 |

このスキャン結果から `docs/reference/config-db/bgp-allowed-prefixes.md` の `<!-- cross-refs -->` ブロックを生成する。
