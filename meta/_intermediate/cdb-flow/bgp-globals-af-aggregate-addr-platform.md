# BGP_GLOBALS_AF_AGGREGATE_ADDR — プラットフォーム差調査

Task F Phase H: `BGP_GLOBALS_AF_AGGREGATE_ADDR` テーブル適用時のプラットフォーム / 構成差を `sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`（一次経路）および `sonic-bgpcfgd/bgpcfgd/`（補助経路） から精読した結果。

## 結論

**プラットフォーム差なし**。`BGP_GLOBALS_AF_AGGREGATE_ADDR` の適用経路は FRR (ユーザ空間ルーティングデーモン) で完結し、ASIC SDK / SAI を直接呼び出さない。ASIC ベンダー (Broadcom / Mellanox / Marvell / Innovium / Barefoot) ・物理形態 (T0 / T1 / T2 / VOQ chassis) ・single-asic / multi-asic 構成のいずれでも、`frrcfgd` の `hdl_af_aggregate()` が CONFIG_DB を購読し FRR vtysh に `address-family <afi> <safi>` → `aggregate-address` コマンドを発行する経路は同一。

## 根拠

### 1. 一次経路は `frr-mgmt-framework` のみ

`BGP_GLOBALS_AF_AGGREGATE_ADDR` を参照するのは `DEVICE_METADATA.frr_mgmt_framework_config=true` 経路の `frrcfgd.py` のみ。

- `src/sonic-bgpcfgd/` 配下を `BGP_GLOBALS_AF_AGGREGATE_ADDR` で grep → **0 ヒット**（`bgpcfgd` テンプレ経路はこのテーブルを購読しない。テンプレ経路は別テーブル `BGP_AGGREGATE_ADDRESS` を使う）
- `dockers/docker-fpm-frr/` 配下を `BGP_GLOBALS_AF_AGGREGATE_ADDR` で grep → **0 ヒット**（docker テンプレに platform 別差し替えなし）

このため、対象経路は `src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` の `hdl_af_aggregate` 一本に閉じる。

### 2. `frrcfgd.py` 全体に platform 分岐なし

`frrcfgd.py` 全体を `platform|asic|chassis|multi_npu|multi_asic|namespace|vendor` で grep した結果のヒットは

```
3384:  syslog.syslog(syslog.LOG_INFO, 'Basic mode Configure for ip sla {}'.format(sla_id))
```

のみで、`asic` は文字列 "Basic" の部分一致による偽陽性。aggregate-address・address-family の処理パスには ASIC / chassis / multi-asic 判定が一切存在しない。

### 3. `BGP_GLOBALS_AF_AGGREGATE_ADDR` ハンドラ位置と内容

`frrcfgd.py` の関連箇所:

- L98: `'BGP_GLOBALS_AF_AGGREGATE_ADDR': ['bgpd']`（daemon マッピング、bgpd 固定）
- L1313: `def hdl_af_aggregate(daemon, cmd_str, op, st_idx, args, data):`
- L1982-1983: `af_aggregate_key_map = [(['ip_prefix', '++as_set', '++summary_only', '+policy'], '{no:no-prefix}aggregate-address {2} {3:aggr-as-set} {4:aggr-summary-only} {5:aggr-policy}', hdl_af_aggregate)]`
- L2118: テーブル → key-map 登録
- L2257: `af_aggr_table = self.config_db.get_table('BGP_GLOBALS_AF_AGGREGATE_ADDR')` （起動時 reconcile）
- L2317: `('BGP_GLOBALS_AF_AGGREGATE_ADDR', self.bgp_table_handler_common)` （subscribe）
- L3169, L3187: per-table 分岐（AF 配下の集約再投入処理）

いずれも純粋に CONFIG_DB → vtysh 文字列生成のロジックで、`device_info.get_platform()` / `is_chassis()` / `is_multi_npu()` 相当の呼び出しは無い。

### 4. FRR 内部処理が ASIC 非依存

`aggregate-address` 適用は FRR `bgpd` のソフトウェア処理。集約ルートは BGP UPDATE で peer に広告され、その結果として APPL_DB `ROUTE_TABLE` 経由で `RouteOrch` が SAI route API を呼ぶが、これは aggregate 経由かどうかに関わらず全 BGP ルート共通の経路。テーブル `BGP_GLOBALS_AF_AGGREGATE_ADDR` 自体に ASIC 別の差し替えは存在しない。

### 5. multi-asic / VOQ chassis 構成での扱い

`BGP_GLOBALS_AF_AGGREGATE_ADDR` は VRF / address-family ごとに per-namespace CONFIG_DB へ配置されうるが、テーブルスキーマ・購読ロジック・FRR コマンド生成は host / asic0..N すべての namespace で同一の `frrcfgd` インスタンスが同じコードで処理する。chassis 環境でも line card 内 BGP container が自分の namespace の CONFIG_DB のみを購読し、特別な AF aggregate マネージャは追加されない。

### 6. ビルド時 platform オーバライドなし

`sonic-buildimage/device/<vendor>/<platform>/` 配下に `BGP_GLOBALS_AF_AGGREGATE_ADDR` を上書きする j2 / json / hwsku-d 由来の差分は存在しない（community master スコープ内では検出されず）。

## まとめ

`BGP_GLOBALS_AF_AGGREGATE_ADDR` の経路は SAI / ASIC SDK を直接呼ばず、`frrcfgd` → vtysh → FRR `bgpd` (ユーザ空間) で完結するため、ASIC ベンダー・物理形態・single / multi-asic 構成のいずれにおいても挙動・適用範囲は同一。プラットフォーム別の例外条件は確認できない。
