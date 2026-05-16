# BGP_ALLOWED_PREFIXES — プラットフォーム差調査

Task F Phase H: `BGP_ALLOWED_PREFIXES` テーブル適用時のプラットフォーム/構成差を `sonic-bgpcfgd` (`managers_allow_list.py`) と `dockers/docker-fpm-frr/` の FRR テンプレート群から精読した結果。

## 結論

**ASIC・ベンダー依存はないが、`switch_type` (chassis-packet) と `type/subtype` (SpineRouter / UpstreamLC) で FRR route-map 生成テンプレートが分岐する**。BGP_ALLOWED_PREFIXES の値解釈やテーブル処理ロジック自体はプラットフォーム非依存だが、ALLOW_LIST 由来の route-map がぶら下がる `FROM_BGP_PEER_V4/V6` ポリシーの末尾処理が VOQ chassis 構成 (chassis-packet) で差し替わる。

## 根拠

### 1. テーブル処理層 (`managers_allow_list.py`) は完全にプラットフォーム非依存

`src/sonic-bgpcfgd/bgpcfgd/managers_allow_list.py` を `platform|asic|chassis|namespace|sub_role|switch_type|hwsku|multi_npu|multi_asic` で grep して 0 ヒット。

- `BGPAllowListMgr` は CONFIG_DB の `BGP_ALLOWED_PREFIXES*` テーブル変化を受け、FRR vtysh コマンドを発行するのみ。ASIC SDK・SAI を一切経由しない。
- `default_action` / `prefixes_v4` / `prefixes_v6` の値検証 (`__is_default_action_valid` / `__is_prefix_value_valid` 等) も IPv4/IPv6 文字列構文のみを見て、プラットフォーム属性を参照しない。
- `__to_prefix_list` による `le 32` / `le 128` の暗黙補完も IP family 判定のみで分岐し、ASIC 種別やマルチ ASIC 構成の影響を受けない。

### 2. constants.yml はプラットフォーム共通

`files/image_config/constants/constants.yml` の `bgp.allow_list` ブロック (`default_action: permit`, `drop_community: 5060:12345`, `default_pl_rules.v4/v6`) は image 単位で 1 つ。`PLATFORM=` / `HWSKU=` 別に上書きされる仕組みは存在しない (`grep -rn allow_list files/device/ files/build_templates/` 0 ヒット)。

### 3. FRR テンプレートに `switch_type == 'chassis-packet'` 分岐あり

`dockers/docker-fpm-frr/frr/bgpd/templates/general/policies.conf.j2` の 48 行と 71 行で以下の分岐が存在する:

```jinja2
{% if CONFIG_DB__DEVICE_METADATA['localhost']['switch_type'] != 'chassis-packet' %}
  set tag {{ constants.bgp.route_do_not_send_appdb_tag }}
{% else %}
  set tag {{ constants.bgp.route_eligible_for_fallback_to_default_tag }}
{% endif %}
  set community {{ constants.bgp.internal_fallback_community }} additive
```

これは `route-map FROM_BGP_PEER_V4 permit 13` / `FROM_BGP_PEER_V6 permit 13` の末尾処理で、ALLOW_LIST が未マッチ (`allow_list_default_community`) かつ DEFAULT prefix-list にもマッチしなかった経路へのタグ付け。

- 非 chassis-packet (通常の ToR / leaf / spine): `route_do_not_send_appdb_tag` を付与し、APPL_DB への route 送出を抑止
- chassis-packet (VOQ chassis 上の packet line card): `route_eligible_for_fallback_to_default_tag` を付与し、line card 間のフォールバック用 default に流用可能とマーク

つまり ALLOW_LIST 機能そのものは両構成で有効だが、**マッチしなかった経路の後段ハンドリングが chassis-packet で異なる**。

### 4. `type == 'SpineRouter' and subtype == 'UpstreamLC'` で route-map 拡張ブロック自体が出現

`policies.conf.j2:41,64` の外側 `{% if ... type=='SpineRouter' and subtype=='UpstreamLC' %}` でガードされているため、route-map permit 12/13 (DEFAULT_IPV4/V6 マッチ → tag/community 付与) は **UpstreamLC な SpineRouter (典型的に T2 supervisor / upper-spine LC)** でのみ生成される。

それ以外のロール (T0 ToR, T1 leaf, 通常 SpineRouter 等) では `FROM_BGP_PEER_V4 permit 11` で `match community allow_list_default_community` のあと即 `permit 100` に落ち、追加の DEFAULT prefix-list 判定や fallback tag は生成されない。

### 5. multi-asic / namespace 観点

- `bgpcfgd` はマルチ ASIC 環境では `asic0..N` namespace 単位で 1 プロセスずつ起動する。`BGP_ALLOWED_PREFIXES` 自体は各 namespace の CONFIG_DB に独立に書かれるが、テーブル処理ロジックは同一バイナリのため**処理内容に差は出ない**。
- VOQ chassis の supervisor / line card で `switch_type` が `chassis-packet` (packet LC) か `voq` (voq LC) かによって 3 で説明した route-map 末尾の tag が変わる。

### 6. ベンダー / ASIC SDK 依存なし

BGP_ALLOWED_PREFIXES → FRR prefix-list / route-map → BGP UPDATE フィルタリングの経路は完全にユーザー空間 (FRR bgpd + zebra) で完結し、SAI / ASIC SDK を経由しない。Broadcom / Mellanox / Marvell / Innovium 等の ASIC ベンダー差や、`HWSKU` 値による分岐はテンプレートにもマネージャにも存在しない (`grep -rn -E 'allow_list|ALLOWED_PREFIXES' files/device/ dockers/ src/sonic-bgpcfgd/` でベンダー固有ヒット 0)。

## まとめ

| 観点 | 差の有無 | 内容 |
|------|---------|------|
| ASIC ベンダー (Broadcom / Mellanox / Marvell 等) | なし | FRR 経路で完結、SAI 非経由 |
| HwSku | なし | テンプレ・マネージャに hwsku 参照 0 |
| multi-asic (`is_multi_npu`) | 実質なし | 各 namespace で同一処理が独立に走るのみ |
| `switch_type == 'chassis-packet'` | **あり** | `FROM_BGP_PEER_V4/V6 permit 13` で `set tag` の値が `route_do_not_send_appdb_tag` → `route_eligible_for_fallback_to_default_tag` に切り替わる (`policies.conf.j2:48,71`) |
| `type=='SpineRouter' and subtype=='UpstreamLC'` | **あり** | route-map permit 12/13 自体がこのロールでのみ生成 (`policies.conf.j2:41,64`) |
| BGP_ALLOWED_PREFIXES の値解釈・検証 | なし | `managers_allow_list.py` はプラットフォーム属性を一切参照しない |
