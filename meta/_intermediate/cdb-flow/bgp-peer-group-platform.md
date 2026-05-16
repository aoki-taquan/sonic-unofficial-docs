# BGP_PEER_GROUP — プラットフォーム差調査

Task F Phase H: `BGP_PEER_GROUP` テーブル適用時のプラットフォーム / 構成差を `frrcfgd.py`、`bgpcfgd/managers_bgp.py`、および FRR Jinja2 テンプレート群 (`bgpd/templates/*/peer-group.conf.j2`、`policies.conf.j2`) から精読した結果。

## 結論

**プラットフォーム差あり**。`BGP_PEER_GROUP` の適用は `DEVICE_METADATA.type`・`sub_role`・`switch_type`・`subtype` の組み合わせにより FRR へ発行されるコマンドが変化する。frrcfgd / bgpcfgd 本体の登録ロジックに条件分岐はないが、起動時に展開される Jinja2 テンプレート (`bgpd/templates/<peer_type>/peer-group.conf.j2`) が switch_type / type / sub_role に基づいた条件分岐を持つ。

---

## 根拠

### 1. bgpcfgd (managers_bgp.py) 本体の platform 分岐

`managers_bgp.py` を `platform|asic|chassis|multi_npu|multi_asic|vendor|namespace|switch_type|sub_role|type` で grep しても 0 ヒット。`BGPPeerGroupMgr` は `peer_type` (general / internal / voq_chassis / monitors / sentinels / dynamic) ごとに Jinja2 テンプレートディレクトリを切り替えるが、この `peer_type` 自体は CONFIG_DB の `BGP_PEER_GROUP.peer_type` フィールドで決まり、ハードウェア情報には依存しない。

### 2. frrcfgd.py の platform 分岐

`frrcfgd.py` の `DEVICE_METADATA` 参照箇所 (L2162) は `frr_mgmt_framework_config` フラグの読み取りのみで、`BGP_PEER_GROUP` ハンドラ内に `switch_type` / `sub_role` 参照はない。frrcfgd は個別の vtysh コマンドで peer-group 属性を投入する経路を持ち、Jinja2 テンプレートは使用しない。

### 3. Jinja2 テンプレートによる platform 差分 (bgpcfgd 起動時展開)

bgpcfgd は起動時および `frr_mgmt_framework_config=false` の場合に `bgpd/templates/<peer_type>/peer-group.conf.j2` を展開して FRR running-config に一括適用する。各テンプレートが参照する `DEVICE_METADATA` フィールドによる差分を以下に整理する。

#### 3a. `general/peer-group.conf.j2` — external peer (ToR / Spine など)

ソース: `dockers/docker-fpm-frr/frr/bgpd/templates/general/peer-group.conf.j2`

| `DEVICE_METADATA.type` | FRR コマンド差 |
|------------------------|---------------|
| `ToRRouter` | `neighbor PEER_V4/V6 allowas-in 1` (IPv4 + IPv6 AF) |
| `LeafRouter` かつ `BGP_BBR.status=enabled` | `neighbor PEER_V4/V6 allowas-in 1` |
| `SpineRouter && subtype=UpstreamLC` または `UpperSpineRouter` | `table-map SELECTIVE_ROUTE_DOWNLOAD_V4/V6`；anchor-route community-list + `TO_BGP_PEER permit 50/60` |
| その他 (デフォルト) | `allowas-in` なし、`table-map` なし |

#### 3b. `internal/peer-group.conf.j2` — iBGP / multi-ASIC internal peer

ソース: `dockers/docker-fpm-frr/frr/bgpd/templates/internal/peer-group.conf.j2`

| `DEVICE_METADATA` 条件 | FRR コマンド差 |
|------------------------|---------------|
| `switch_type=chassis-packet` | `neighbor INTERNAL_PEER_V4/V6 update-source Loopback4096` + `ttl-security hops 1` |
| `sub_role=BackEnd` | AF 内に `neighbor INTERNAL_PEER_V4/V6 route-reflector-client`；route-map に `set originator-id <Loopback4096>` |
| `switch_type=chassis-packet && subtype != DownstreamLC` | FALLBACK_COMMUNITY を `set tag route_eligible_for_fallback_to_default_tag` |
| その他 (single-ASIC) | `route-reflector-client` なし、`update-source` なし |

#### 3c. `voq_chassis/peer-group.conf.j2` — VoQ シャーシ内部 peer

ソース: `dockers/docker-fpm-frr/frr/bgpd/templates/voq_chassis/peer-group.conf.j2`

| `DEVICE_METADATA` 条件 | FRR コマンド差 |
|------------------------|---------------|
| `bgp_asn` フィールドあり | `neighbor VOQ_CHASSIS_V4/V6_PEER remote-as <bgp_asn>` |
| `type=ToRRouter` | `neighbor VOQ_CHASSIS_V4/V6_PEER allowas-in 1` |
| 全ケース共通 | `addpath-tx-all-paths`、`send-community` が常に付与 |

#### 3d. `monitors/peer-group.conf.j2` — BGP モニタ peer

ソース: `dockers/docker-fpm-frr/frr/bgpd/templates/monitors/peer-group.conf.j2`

| `DEVICE_METADATA` 条件 | FRR コマンド差 |
|------------------------|---------------|
| `switch_type=voq` (chassisdb.conf 存在) または `switch_type=chassis-packet` | `neighbor BGPMON update-source Loopback4096`；IPv6 AF ブロック有効化 |
| 非 VoQ・非 chassis-packet | `neighbor BGPMON update-source <Loopback0 IPv4>` |
| その他 | `update-source` なし、IPv6 AF なし |

### 4. `policies.conf.j2` による peer-group 関連ポリシー差分

peer-group に紐づく route-map も platform 依存で変化する。

#### `general/policies.conf.j2`

| 条件 | 差分 |
|------|------|
| `allow_list.enabled=true` | `FROM_BGP_PEER_V4/V6` に `ALLOW_LIST` call + community チェック挿入 |
| `SpineRouter && subtype=UpstreamLC` | `FROM_BGP_PEER_V4/V6` permit 12/13: default prefix + `set tag` (route_do_not_send / fallback) |
| `switch_type=chassis-packet` (SpineRouter UpstreamLC) | `set tag route_eligible_for_fallback_to_default_tag` |
| `SpineRouter UpstreamLC` または `UpperSpineRouter` | anchor-route community-list + `TAG_ANCHOR_COMMUNITY` route-map + `TO_BGP_PEER_V4/V6 permit 50/60` |

#### `internal/policies.conf.j2`

| 条件 | 差分 |
|------|------|
| `sub_role=BackEnd` | `FROM_BGP_INTERNAL_PEER_V4/V6 permit 1`: `set originator-id <Loopback4096 or bgp_router_id>` |
| `switch_type=chassis-packet` | DEVICE_INTERNAL_COMMUNITY / FALLBACK_COMMUNITY 処理、`local-preference 80` on NO_EXPORT |
| `switch_type=chassis-packet && subtype=DownstreamLC` | FALLBACK_COMMUNITY タグなし |
| `switch_type=chassis-packet && subtype != DownstreamLC` | `set tag route_eligible_for_fallback_to_default_tag` |
| その他 (single-asic) | `FROM_BGP_INTERNAL_PEER_V6 permit 1`: `set ipv6 next-hop prefer-global` のみ |

### 5. frrcfgd 経路での platform 非依存性

`frr_mgmt_framework_config=true` 時は frrcfgd が動的に peer-group 属性を vtysh 経由で設定する。この経路では Jinja2 テンプレートを経由せず、`bgp_neighbor_handler` が `platform` / `switch_type` / `sub_role` を参照する分岐を持たないため、frrcfgd 動的更新経路においては platform 差なし。

## まとめ表

| 構成 | peer_type | FRR 主要差 |
|------|-----------|-----------|
| ToRRouter (general) | external | `allowas-in 1` (V4/V6) |
| LeafRouter + BBR enabled (general) | external | `allowas-in 1` (V4/V6) |
| SpineRouter UpstreamLC / UpperSpineRouter (general) | external | `table-map SELECTIVE_ROUTE_DOWNLOAD`、anchor-route community ポリシー |
| BackEnd (internal) | internal | `route-reflector-client`、`set originator-id` |
| chassis-packet (internal) | internal | `update-source Loopback4096`、`ttl-security hops 1`、FALLBACK_COMMUNITY ポリシー |
| VoQ chassis (voq_chassis) | voq_chassis | `remote-as <bgp_asn>`、`addpath-tx-all-paths`、ToRRouter なら `allowas-in 1` |
| VoQ / chassis-packet (monitors) | monitors | `update-source Loopback4096`、IPv6 AF 有効 |
| 非 VoQ (monitors) | monitors | `update-source <Loopback0 IPv4>` |
| single-asic ToR / standard (general) | external | デフォルト (差分なし) |
