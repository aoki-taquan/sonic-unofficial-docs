# device-metadata Phase 12 中間ファイル

## 対称読み対象 Jinja2 ブロック

### voq_chassis/policies.conf.j2

**ブロック 1** (L19-27): `subtype == 'UpstreamLC'`
- if 分岐: `route-map FROM_VOQ_CHASSIS_V4_PEER deny 3` → DEVICE_INTERNAL_FALLBACK_COMMUNITY を deny
- else 分岐: `route-map FROM_VOQ_CHASSIS_V4_PEER permit 3` → `set comm-list DEVICE_INTERNAL_FALLBACK_COMMUNITY delete` + `set tag {{ constants.bgp.route_eligible_for_fallback_to_default_tag }}` (=203)

**ブロック 2** (L54-62): 同条件 V6 版
- if 分岐: `route-map FROM_VOQ_CHASSIS_V6_PEER deny 4` → deny
- else 分岐: `route-map FROM_VOQ_CHASSIS_V6_PEER permit 4` → comm-list delete + `set tag 203`

### internal/policies.conf.j2

**外部ブロック** (L8-97): `sub_role == 'BackEnd'` / `elif switch_type == 'chassis-packet'` / `else`
- BackEnd 分岐: originator-id 設定のみ
- chassis-packet 分岐: community-list + route-map 生成 (nested blocks あり)
- else 分岐: V6 permit 1 (next-hop prefer-global) のみ

**ブロック 3** (L42-51): `subtype == 'DownstreamLC'` (chassis-packet 分岐内)
- if 分岐: `FROM_BGP_INTERNAL_PEER_V4 permit 3` → comm-list delete のみ (tag なし)
- else 分岐: `FROM_BGP_INTERNAL_PEER_V4 permit 3` → comm-list delete + `set tag 203`

**ブロック 4** (L67-76): 同条件 V6 版
- if 分岐: `FROM_BGP_INTERNAL_PEER_V6 permit 4` → comm-list delete のみ
- else 分岐: `FROM_BGP_INTERNAL_PEER_V6 permit 4` → comm-list delete + `set tag 203`

### general/peer-group.conf.j2

**ブロック 5** (L7-13): `type == 'ToRRouter'` / `elif type == 'LeafRouter'`
- if: `allowas-in 1` 設定
- elif LeafRouter: BGP_BBR status == 'enabled' のときのみ `allowas-in 1`
- else: 該当なし (allowas-in 設定なし)

**ブロック 6** (L17-19): `(type == 'SpineRouter' AND subtype == 'UpstreamLC') OR type == 'UpperSpineRouter'`
- if: `table-map SELECTIVE_ROUTE_DOWNLOAD_V4`
- else: 該当なし

**ブロック 7-8**: V6 版 (L22-34): 同上

## 統計

- 対称読みを行った Jinja ブロック数: **8 ブロック** (voq_chassis: 2, internal: 4, peer-group: 4 [うち V6 は V4 と同一パターン])
- else / elif 分岐の追加挙動を記載した row 数: **2 行** (UpstreamLC, DownstreamLC)
- constants.yml から新規解決した定数値数: **1** (`route_eligible_for_fallback_to_default_tag` = 203)

## 代表サンプル

### UpstreamLC (voq_chassis/policies.conf.j2:19-27)
- before: `subtype == 'UpstreamLC'` 時 route-map deny
- after: if: route-map deny 3/4 / else: route-map permit 3/4 + `set comm-list DEVICE_INTERNAL_FALLBACK_COMMUNITY delete` + `set tag 203`

### DownstreamLC (internal/policies.conf.j2:42-51)
- before: DownstreamLC 向けに comm-list delete 分岐
- after: if (DownstreamLC): permit 3/4 + comm-list delete のみ (tag なし) / else: permit 3/4 + comm-list delete + `set tag 203`

### peer-group.conf.j2 if/elif/else (L7-13)
- ToRRouter: allowas-in 1 / LeafRouter+BBR enabled: allowas-in 1 / else: 該当なし

## 定数解決

| constants 参照 | 実値 (constants.yml) |
|---|---|
| `constants.bgp.route_eligible_for_fallback_to_default_tag` | `203` |
