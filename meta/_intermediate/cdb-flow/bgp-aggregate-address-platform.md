# BGP_AGGREGATE_ADDRESS — プラットフォーム差調査

Task F Phase H: `BGP_AGGREGATE_ADDRESS` テーブル適用時のプラットフォーム / 構成差を `bgpcfgd` (`sonic-buildimage/src/sonic-bgpcfgd`) と FRR 関連アセット (`sonic-buildimage/dockers/docker-fpm-frr`、`src/sonic-frr-mgmt-framework/frrcfgd`) から精読した結果。

## 結論

**プラットフォーム差なし**。`BGP_AGGREGATE_ADDRESS` の適用経路は FRR (ユーザ空間ルーティングデーモン) で完結し、ASIC SDK / SAI を直接呼び出さない。ASIC ベンダー・T0 / T1 / VOQ chassis・single-asic / multi-asic いずれの構成でも `bgpcfgd` の `AggregateAddressMgr` が CONFIG_DB を購読し FRR vtysh に `aggregate-address` コマンドを発行する経路は同一。

## 根拠

### 1. `AggregateAddressMgr` は無条件で登録される

`src/sonic-bgpcfgd/bgpcfgd/main.py` L105-106:

```python
# Bgp Aggregate Address Manager
AggregateAddressMgr(common_objs, "CONFIG_DB", BGP_AGGREGATE_ADDRESS_TABLE_NAME),
```

`managers[]` リストへ無条件 append。直後の `if device_info.is_chassis():` は別マネージャ (`ChassisAppDbMgr` for `BGP_DEVICE_GLOBAL`) のためのものであり、aggregate-address とは無関係。`is_multi_npu()` / ASIC ベンダー判定 / `device_info.get_platform()` 呼び出しも `AggregateAddressMgr` 登録パスには存在しない。

### 2. `managers_aggregate_address.py` 本体に platform 分岐なし

`src/sonic-bgpcfgd/bgpcfgd/managers_aggregate_address.py` を `platform|asic|chassis|multi_npu|multi_asic|vendor|namespace` で grep しても 0 ヒット。処理は

- CONFIG_DB の `BGP_AGGREGATE_ADDRESS` を購読 (`ConfigDBConnector` を引数なしで host CONFIG_DB に接続)
- prefix 妥当性検証 (`validate_prefix()`)
- BBR 状態 (`BGP_BBR` テーブル) と `bbr-required` を突き合わせ STATE_DB に `active`/`inactive` を記録
- 有効な場合 `vtysh` 経由で `aggregate-address <prefix> [summary-only] [as-set] ...` を FRR に投入

の 4 段で、いずれも ASIC / chassis 形態に依存しない。

### 3. `frr-mgmt-framework` 経路も同様にプラットフォーム非依存

`src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` で aggregate-address に関わるハンドラは:

- L98: `'BGP_GLOBALS_AF_AGGREGATE_ADDR': ['bgpd']` (daemon マッピング)
- L1313: `hdl_af_aggregate(...)`
- L1982-1983: `af_aggregate_key_map = [(['ip_prefix', '++as_set', '++summary_only', '+policy'], 'aggregate-address {2} {3:aggr-as-set} {4:aggr-summary-only} {5:aggr-policy}', hdl_af_aggregate)]`
- L2118: テーブル → key-map 登録
- L3169 / L3187: per-table 分岐

`frrcfgd.py` 全体を `platform|asic|chassis|multi_npu|multi_asic` で grep してもヒットなし (`Basic mode Configure for ip sla` メッセージのみで aggregate とは無関係)。FRR config 生成テンプレートも platform 分岐を持たない。

### 4. FRR 内部処理が ASIC 非依存

`aggregate-address` 適用は FRR `bgpd` のソフトウェア処理であり、集約ルートは BGP UPDATE で peer に広告される。SONiC では FRR が APPL_DB `ROUTE_TABLE` に行を書き、`bgporch` / `RouteOrch` が SAI route API を呼ぶが、これは aggregate に限らずすべての BGP ルートで共通の経路であり、テーブルとしての `BGP_AGGREGATE_ADDRESS` 自体には ASIC 別の差し替えがない。

### 5. multi-asic / VOQ chassis 構成での扱い

`BGP_AGGREGATE_ADDRESS` および `BGP_GLOBALS_AF_AGGREGATE_ADDR` は VRF / address-family ごとに per-namespace CONFIG_DB へ配置できるが、テーブルスキーマ・購読ロジック・FRR コマンド生成は host / asic0..N すべての namespace で同一の `bgpcfgd` (各 BGP docker インスタンス) が同じコードで処理する。chassis 環境でも line card 内 BGP container が自分の namespace の CONFIG_DB のみを購読し、特別な集約マネージャは追加されない。

### 6. ビルド時 platform オーバライドなし

`sonic-buildimage/device/<vendor>/<platform>/` 配下に aggregate-address を上書きする j2 / json / hwsku-d 由来の差分は存在しない (community master のスコープ内では検出されず)。`files/image_config/` にも aggregate / bgp-aggregate ディレクトリはない。

## まとめ

`BGP_AGGREGATE_ADDRESS` の経路は SAI / ASIC SDK を直接呼ばず、`bgpcfgd` → vtysh → FRR `bgpd` (ユーザ空間) で完結するため、ASIC ベンダー (Broadcom / Mellanox / Marvell / Innovium / Barefoot) ・物理形態 (T0 / T1 / T2 / VOQ chassis) ・single / multi-asic 構成のいずれにおいても挙動・適用範囲は同一。プラットフォーム別の例外条件は確認できない。
