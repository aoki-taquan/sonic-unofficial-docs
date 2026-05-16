# Phase A — BGP_INTERNAL_NEIGHBOR コード由来の暗黙デフォルト

## 対象ファイル

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-bgp-internal-neighbor.yang`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-bgp-common.yang`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py`
- `sonic-buildimage/src/sonic-config-engine/minigraph.py`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/internal/instance.conf.j2`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/internal/peer-group.conf.j2`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/internal/policies.conf.j2`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/internal/additional_loopbacks.conf.j2`

## YANG 構造サマリ

`sonic-bgp-internal-neighbor.yang` は `sonic-bgp-cmn-neigh` grouping を `uses` し、以下の refine を追加する:

- `asn`: DEVICE_METADATA の `bgp_asn` と一致すること (`must` 制約) + `asn >= 1`
- `local_addr`: `mandatory true` + neighbor と同一 AF であること

`sonic-bgp-cmn-neigh` grouping のフィールド: `asn`, `holdtime`, `keepalive`, `local_addr`, `name`, `nhopself`, `rrclient`, `admin_status`

## フィールド別デフォルト分析

### 1. `asn`

| 種別 | 値 | 根拠 |
|------|----|------|
| YANG `default` | なし（必須相当だが mandatory ではない） | `sonic-bgp-common.yang` L537: range `0..4294967295` |
| YANG `must` 制約 | DEVICE_METADATA の `bgp_asn` と一致 | `sonic-bgp-internal-neighbor.yang` L43 |
| YANG `must` 制約 | `>= 1` | `sonic-bgp-internal-neighbor.yang` L46 |
| minigraph 生成 | peer の `<ASN>` 要素から取得 | `minigraph.py` L1414-1417 |
| filter_bad_asn | ASN 未設定 or 0 のエントリは BGP_INTERNAL_NEIGHBOR から除外 | `minigraph.py` L1424-1427 |

**結論**: YANG に default 値なし。0 は `must >=1` で YANG バリデーション拒否。minigraph 生成時はピアの ASN 要素が欠落 or 0 の場合 `filter_bad_asn()` でエントリ丸ごと除外される。つまり `asn` 未設定エントリは CONFIG_DB に入らない（silent drop）。

### 2. `local_addr`

| 種別 | 値 | 根拠 |
|------|----|------|
| YANG mandatory | `true`（refine で設定） | `sonic-bgp-internal-neighbor.yang` L51 |
| YANG `must` | neighbor と同一 AF (IPv4 or IPv6) | `sonic-bgp-internal-neighbor.yang` L52-55 |
| bgpcfgd 処理 | 欠如時は `log_warn` のみ、peer 追加は続行 | `managers_bgp.py` L194-195 |
| bgpcfgd 正規化 | `netaddr.IPNetwork(str(...)).ip` でホスト部のみ抽出 | `managers_bgp.py` L197 |
| bgpcfgd ガード | interface 解決不能時は `return False`（再試行待ち） | `managers_bgp.py` L198-201 |

**結論**: YANG は mandatory だが bgpcfgd は `log_warn` のみで処理続行する乖離あり（YANG-実装 discrepancy）。interface が未設定状態では peer 確立が延期される（書込み順依存）。

### 3. `holdtime`

| 種別 | 値 | 根拠 |
|------|----|------|
| YANG `default` | なし（uint16、範囲制限なし） | `sonic-bgp-common.yang` L545 |
| instance.conf.j2 ハードコード | `timers 3 10`（keepalive=3、holdtime=10） | `instance.conf.j2` L6 |
| minigraph fallback | `180` | `minigraph.py` L1315-1316 |

**結論**: YANG にデフォルト値なし。bgpcfgd テンプレートは CONFIG_DB の `holdtime` フィールドを **無視**し、`timers 3 10` をハードコードで FRR に発行する（dead field）。minigraph は `180` を書き込むが bgpcfgd テンプレートが上書きするため実際には無効。

### 4. `keepalive`

| 種別 | 値 | 根拠 |
|------|----|------|
| YANG `default` | なし（uint16） | `sonic-bgp-common.yang` L549 |
| instance.conf.j2 ハードコード | `3`（timers 3 10 の keepalive 部分） | `instance.conf.j2` L6 |
| minigraph fallback | `60` | `minigraph.py` L1317-1320 |

**結論**: `holdtime` と同様、YANG デフォルトなし、bgpcfgd テンプレートが `3` にハードコード、minigraph 値は実質 dead field。

### 5. `name`

| 種別 | 値 | 根拠 |
|------|----|------|
| YANG `default` | なし（optional string） | `sonic-bgp-common.yang` L559 |
| bgpcfgd テンプレート | `neighbor {{ neighbor_addr }} description {{ bgp_session['name'] }}` | `instance.conf.j2` L5 |
| bgpcfgd tag 生成 | `data['name'] if 'name' in data else nbr` | `managers_bgp.py` L226 |
| check_neig_meta ガード | `name` が DEVICE_NEIGHBOR_METADATA に未登録の場合 `return False` | `managers_bgp.py` L221-223 |

**結論**: YANG default なし、optional。`check_neig_meta` は BGP_INTERNAL_NEIGHBOR では `False`（`main.py` L88: 第5引数 `False`）なので `name` の DEVICE_NEIGHBOR_METADATA チェックは実施しない。`name` 欠如時は neighbor アドレスを tag として使用する。

### 6. `nhopself`

| 種別 | 値 | 根拠 |
|------|----|------|
| YANG 型 | `uint8 {range "0..1"}` | `sonic-bgp-common.yang` L564-567 |
| YANG `default` | なし | `sonic-bgp-common.yang` |
| instance.conf.j2 | 参照なし（`nhopself` フィールドを読まない） | `instance.conf.j2` 全行精読 |
| peer-group.conf.j2 | `BackEnd` sub_role 時は `next-hop-self force`（nhopself 値依存ではなくプラットフォーム依存） | `instance.conf.j2` L13-15, L21-23 |
| minigraph 生成 | `nhopself = 1 if session.find(...NextHopSelf...) is not None else 0` | `minigraph.py` L1321 |

**結論**: YANG default なし。bgpcfgd テンプレートは `nhopself` フィールド値を**読まない**（dead field）。代わりに `DEVICE_METADATA.sub_role == 'BackEnd'` または `switch_type == 'chassis-packet'` の場合に `next-hop-self force` をプラットフォーム依存でハードコード。minigraph が書き込む `nhopself` 値は CONFIG_DB には存在するが bgpcfgd では完全無視。

### 7. `rrclient`

| 種別 | 値 | 根拠 |
|------|----|------|
| YANG 型 | `uint8 {range "0..1"}` | `sonic-bgp-common.yang` L571-574 |
| YANG `default` | なし | `sonic-bgp-common.yang` |
| instance.conf.j2 条件分岐 | `if 'rrclient' in bgp_session and bgp_session['rrclient'] | int != 0` | `instance.conf.j2` L26-28 |
| peer-group.conf.j2 条件分岐 | `BackEnd` 時はピアグループ単位でも RRC 設定 | `peer-group.conf.j2` L11-13, L25-27 |
| minigraph 生成 | `rrclient = 1 if session.find(...RRClient...) is not None else 0` | `minigraph.py` L1312 |

**結論**: YANG default なし。テンプレートは `rrclient` を実際に読む（有効 field）。デフォルト（0）は `int != 0` 条件で route-reflector-client を生成しない。1 の場合のみ `route-reflector-client` が追加される。

### 8. `admin_status`

| 種別 | 値 | 根拠 |
|------|----|------|
| YANG 型 | `stypes:admin_status`（`up`/`down`） | `sonic-bgp-common.yang` L578 |
| YANG `default` | なし | `sonic-bgp-common.yang` |
| minigraph 生成 | 内部セッションは常に `'up'` を設定 | `minigraph.py` L1347-1353, L1367-1368, L1377-1379 |
| bgpcfgd update_peer | `admin_status` フィールドが存在すれば `change_admin_status()` へ委譲 | `managers_bgp.py` L315 |
| bgpcfgd update_peer | `admin_status` 以外のフィールド更新は LOG_ERR で drop | `managers_bgp.py` L319-320 |

**結論**: YANG default なし。minigraph 生成時は常に `'up'`（chassis-packet / 内部両ルーター のケースいずれも `admin_status = 'up'` を強制設定）。ランタイム更新は `admin_status` のみ対応。

## ハードコード・プラットフォーム依存まとめ

### peer-group.conf.j2 ハードコード（常時適用）

| 設定 | FRR コマンド | 条件 |
|------|-------------|------|
| soft-reconfiguration inbound | `neighbor INTERNAL_PEER_V4 soft-reconfiguration inbound` | 常時 |
| allowas-in 1 | `neighbor INTERNAL_PEER_V4 allowas-in 1` | 常時 |
| send-community | `neighbor INTERNAL_PEER_V4 send-community` | 常時 |
| route-map FROM_BGP_INTERNAL_PEER_V4 in | 常時 | 常時 |
| route-map TO_BGP_INTERNAL_PEER_V4 out | 常時 | 常時 |

### instance.conf.j2 ハードコード

| 設定 | FRR コマンド | 条件 |
|------|-------------|------|
| timers | `timers 3 10` | 常時（CONFIG_DB の holdtime/keepalive 無視） |
| timers connect | `timers connect 10` | 常時（CONFIG_DB の conn_retry 無視） |

### プラットフォーム依存（DEVICE_METADATA 値で分岐）

| 条件 | 効果 | テンプレート |
|------|------|-------------|
| `sub_role == 'BackEnd'` | ピアグループに `route-reflector-client` 付与 | `peer-group.conf.j2` L11-13, L25-27 |
| `sub_role == 'BackEnd'` | 個別 neighbor に `next-hop-self force` 付与 | `instance.conf.j2` L13-15, L21-23 |
| `switch_type == 'chassis-packet'` | 個別 neighbor に `next-hop-self force` 付与 | `instance.conf.j2` L13-15, L21-23 |
| `switch_type == 'chassis-packet'` | INTERNAL_PEER_V4/V6 の `update-source Loopback4096` + `ttl-security hops 1` | `peer-group.conf.j2` L7-9, L20-23 |
| Loopback4096 追加 | `additional_loopbacks.conf.j2`: Loopback4096 を loopbacks リストに追加 | `managers_bgp.py` L146: dep追加 |

### policies.conf.j2 プラットフォーム依存

| 条件 | ルートマップ挙動 |
|------|----------------|
| `sub_role == 'BackEnd'` | FROM_BGP_INTERNAL_PEER_V4 permit 1: `set originator-id` に Loopback4096 IPv4 or `bgp_router_id` |
| `switch_type == 'chassis-packet'` | `constants.bgp.internal_community` を community-list として設定、tag や local-preference 付与 |
| `switch_type == 'chassis-packet'` かつ `subtype == 'DownstreamLC'` | fallback community tag の処理が分岐 |
| それ以外 | FROM_BGP_INTERNAL_PEER_V4 は permit 100 のみ（フィルタなし） |

## YANG-実装 Discrepancy

| フィールド | YANG 定義 | bgpcfgd 実装 | 乖離種別 |
|-----------|----------|-------------|---------|
| `holdtime` | uint16（default なし） | テンプレートで無視、`timers 3 10` をハードコード | dead field |
| `keepalive` | uint16（default なし） | テンプレートで無視、`timers 3 10` をハードコード | dead field |
| `nhopself` | uint8 0..1 | テンプレートで完全無視、sub_role/switch_type で代替 | dead field + プラットフォーム依存乖離 |
| `local_addr` | mandatory true | bgpcfgd は warn のみで処理続行 | YANG-実装 discrepancy |

## Dead Consumer 分析

`BGP_INTERNAL_NEIGHBOR` の唯一の consumer は `BGPPeerMgrBase(peer_type="internal")` (`main.py` L88)。

- `check_neig_meta=False`（第5引数）であるため DEVICE_NEIGHBOR_METADATA チェックなし
- `check_deployment_id` は constants 依存（constants に `use_deployment_id` がなければ False）
- Loopback4096 依存あり（`main.py` L146: peer_type == 'internal' のとき dep 追加）

## evidence

- `sonic-bgp-internal-neighbor.yang`: `sonic-net/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-bgp-internal-neighbor.yang`
- `sonic-bgp-common.yang`: `sonic-net/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-bgp-common.yang`
- `managers_bgp.py`: `sonic-net/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`
- `main.py`: `sonic-net/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py`
- `minigraph.py`: `sonic-net/sonic-buildimage/src/sonic-config-engine/minigraph.py`
- `instance.conf.j2`: `sonic-net/sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/internal/instance.conf.j2`
- `peer-group.conf.j2`: `sonic-net/sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/internal/peer-group.conf.j2`
- `policies.conf.j2`: `sonic-net/sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/internal/policies.conf.j2`
