# BGP_NEIGHBOR_AF — プラットフォーム差調査

Task F Phase H: `BGP_NEIGHBOR_AF` テーブル適用時のプラットフォーム / 構成差を `frrcfgd.py` (`sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd`) と FRR テンプレート群 (`sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/*/policies.conf.j2`) から精読した結果。

## 結論

**プラットフォーム差なし**。`BGP_NEIGHBOR_AF` の適用経路は FRR (ユーザ空間ルーティングデーモン) で完結し、SAI / ASIC SDK を直接呼び出さない。ASIC ベンダー・T0 / T1 / VOQ chassis・single-asic / multi-asic いずれの構成でも `frrcfgd` の `BGPConfigDaemon` が CONFIG_DB を購読し FRR vtysh に `address-family ... / neighbor <addr> ...` コマンドを発行する経路は同一。

## 根拠

### 1. `frrcfgd.py` に platform / asic 分岐なし

`sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` 全体を以下のキーワードで grep しても 0 ヒット（BGP_NEIGHBOR_AF 処理に関係するヒットなし）:

- `platform`, `hwsku`, `HWSKU`, `sonic_platform`, `asic_type`, `multi_npu`, `multi_asic`, `is_chassis`, `is_multi_npu`, `get_platform`

唯一 `DEVICE_METADATA` 参照 (L2162, L2295) は `bgp_asn` と `docker_routing_config_mode` の取得のみに使用されており、BGP_NEIGHBOR_AF ハンドラとは無関係。

`bgp_table_handler_common` (L2306) への `BGP_NEIGHBOR_AF` 登録は無条件であり、`if` ガードなし。

### 2. `nbr_af_key_map` / ハンドラに platform 分岐なし

`nbr_af_key_map` (L2111) と `bgp_table_handler_common()` (L3918-3930) はフィールド値と DELETE/SET の 2 分岐のみを持ち、ベンダー・ASIC 形態・スイッチタイプによる条件分岐は存在しない。

### 3. `policies.conf.j2` は BGP_NEIGHBOR_AF を参照しない

調査対象 (`sentinels`, `monitors`, `dynamic`, `general`, `internal`, `voq_chassis` の全バリアント):

- いずれのテンプレートも `BGP_NEIGHBOR_AF` キーワードを含まない
- `internal/policies.conf.j2` および `voq_chassis/policies.conf.j2` は `DEVICE_METADATA['localhost']['sub_role']` / `switch_type` / `subtype` で分岐するが、これは route-map / community-list の生成に関するものであり、BGP_NEIGHBOR_AF 適用とは独立している
- `general/policies.conf.j2` は `allow_list` 設定によって route-map を生成するが、BGP_NEIGHBOR_AF フィールドには依存しない

### 4. multi-asic / VOQ chassis 構成での扱い

`BGP_NEIGHBOR_AF` は VRF 単位で per-namespace CONFIG_DB へ配置できるが、各 BGP コンテナ (asic0..N) 内の `frrcfgd` インスタンスが同一コードで処理する。chassis 環境でも LINE CARD 内 BGP container が自分の namespace の CONFIG_DB のみを購読し、特別な AF マネージャは追加されない。

### 5. FRR 処理が ASIC 非依存

`address-family` ブロック内の `neighbor <addr> activate` / `route-map` / `maximum-prefix` 等の AF 設定は FRR `bgpd` ユーザ空間で完結する。SAI / ASIC SDK への直接呼び出しはなく、BGP 経路学習の後続処理 (`bgporch` / `RouteOrch`) はすべての BGP ルートで共通の経路であり BGP_NEIGHBOR_AF 自体に ASIC 別差し替えはない。

### 6. ビルド時 platform オーバライドなし

`sonic-buildimage/device/<vendor>/<platform>/` 配下に BGP_NEIGHBOR_AF / neighbor-af を上書きする j2 / json / hwsku-d 由来の差分は存在しない (community master スコープ内では検出されず)。

## まとめ

`BGP_NEIGHBOR_AF` の処理経路は `frrcfgd` → vtysh → FRR `bgpd` (ユーザ空間) で完結するため、ASIC ベンダー (Broadcom / Mellanox / Marvell / Innovium / Barefoot) ・物理形態 (T0 / T1 / T2 / VOQ chassis) ・single / multi-asic 構成のいずれにおいても挙動・適用範囲は同一。プラットフォーム別の例外条件は確認できない。
