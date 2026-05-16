# BGP_GLOBALS — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/bgp-globals.md` Phase C 追加分。
YANG leafref として明示されているもの以外の、実装上の暗黙参照を網羅する。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` | frrcfgd の BGP_GLOBALS ハンドラ (`bgp_global_handler`) |
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-bgp-global.yang` | YANG 定義 |
| `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` | bgpcfgd (参照: BGP_GLOBALS への参照なし) |

## YANG 明示 leafref (参考)

| leaf | leafref 先 |
|------|-----------|
| `vrf_name` (BGP_GLOBALS_LIST) | union: `"default"` 固定文字列 または `VRF.VRF_LIST.name` へのリーフリファレンス |
| `vrf_name` (BGP_GLOBALS_AF_LIST) | `BGP_GLOBALS.BGP_GLOBALS_LIST.vrf_name` |
| `vrf_name` (BGP_GLOBALS_AF_AGGREGATE_ADDR_LIST) | `BGP_GLOBALS.BGP_GLOBALS_LIST.vrf_name` |
| `vrf_name` (BGP_GLOBALS_AF_NETWORK_LIST) | `BGP_GLOBALS.BGP_GLOBALS_LIST.vrf_name` |
| `import_vrf` (BGP_GLOBALS_AF_LIST) | `BGP_GLOBALS.BGP_GLOBALS_LIST.vrf_name`（self と異なる VRF を指定） |

## 暗黙参照 (leafref 超え)

### 1. DEVICE_METADATA["localhost"]["bgp_asn"]
- **参照先フィールド**: `DEVICE_METADATA|localhost|bgp_asn`
- **参照元**: `frrcfgd.py` L2162-2166, L2445-2446, `metadata_handler()` L2367-2374
- **意味**: `default` VRF の場合、`BGP_GLOBALS` に `local_asn` が未設定でも `DEVICE_METADATA.localhost.bgp_asn` をフォールバックとして使用する（`__get_vrf_asn()` L2445）。frrcfgd 起動時に読み込み、`metadata_handler` が変更を購読して `metadata_asn` を更新する。
- **証跡**: `frrcfgd.py:2162-2166` (初期化), `frrcfgd.py:2444-2446` (`__get_vrf_asn` フォールバック)

### 2. DEVICE_METADATA["localhost"]["docker_routing_config_mode"]
- **参照先フィールド**: `DEVICE_METADATA|localhost|docker_routing_config_mode`
- **参照元**: `frrcfgd.py` L2167-2170
- **意味**: frrcfgd 起動時に読み込み、`config_mode` として保持。`"unified"` モードの場合のみ BGP_GLOBALS テーブルを vtysh 経由でプログラムする。`separated` モードでは挙動が異なる。
- **証跡**: `frrcfgd.py:2167-2170` (初期化), `frrcfgd.py:2344`

### 3. VRF テーブル（VNI マッピング）
- **参照先テーブル**: `VRF`
- **参照元**: `frrcfgd.py` L2271-2273; `vrf_handler()` L2413
- **意味**: frrcfgd は起動時に `VRF` テーブル全体を読み込み `vrf_vni_map` を構築する。BGP_GLOBALS の VRF キーが参照する VRF が `VRF` テーブルに `vni` を持つ場合、VNI 設定が zebra に渡される。VRF が削除されると `no vni` コマンドが発行される。
- **証跡**: `frrcfgd.py:2271-2273`, `frrcfgd.py:2413-2440`

### 4. ROUTE_REDISTRIBUTE（local_asn 設定時の再適用）
- **参照先テーブル**: `ROUTE_REDISTRIBUTE`
- **参照元**: `frrcfgd.py` L2704
- **意味**: `BGP_GLOBALS` の `local_asn` フィールドが新規設定されると（`prog_asn == True`）、frrcfgd は同 VRF 内の `ROUTE_REDISTRIBUTE` テーブルを再適用する（`__apply_dep_vrf_table(vrf, 'ROUTE_REDISTRIBUTE')`）。local_asn が確定してから redistribution を確実に FRR へ反映するための依存再実行。
- **証跡**: `frrcfgd.py:2702-2704`

### 5. BGP_NEIGHBOR / BGP_NEIGHBOR_AF（local_asn 設定時の再適用）
- **参照先テーブル**: `BGP_NEIGHBOR`、`BGP_NEIGHBOR_AF`
- **参照元**: `frrcfgd.py` L2849-2853
- **意味**: ピアグループ / neighbor 処理のハンドラ内で、VRF の local_asn が確定した後に `BGP_NEIGHBOR` と `BGP_NEIGHBOR_AF` を再適用する（`__apply_dep_vrf_table`）。BGP_GLOBALS.local_asn が先に存在しないと neighbor が反映されない依存関係の逆側として、local_asn 設定後に neighbor を引き込む。
- **証跡**: `frrcfgd.py:2847-2853`

### 6. BGP_GLOBALS_EVPN 系サブテーブル（EVPN VNI/RT）
- **参照先テーブル**: `BGP_GLOBALS_EVPN_VNI`、`BGP_GLOBALS_EVPN_RT`、`BGP_GLOBALS_EVPN_VNI_RT`
- **参照元**: `frrcfgd.py` L2308-2310; `tbl_to_key_map` L2106-2140
- **意味**: これら3テーブルは `frrcfgd` 内で BGP_GLOBALS と同じ VRF-based テーブル群として管理され、`__vrf_based_table()` で local_asn の存在を確認する。BGP_GLOBALS に当該 VRF の `local_asn` がなければこれらのテーブルも skip される。
- **証跡**: `frrcfgd.py:2100-2103`, `frrcfgd.py:2659`

## 参照関係サマリ

```
BGP_GLOBALS
  ├─ [YANG leafref]  VRF.VRF_LIST.name                (vrf_name フィールド, union 中)
  ├─ [YANG leafref]  BGP_GLOBALS_AF.vrf_name           (AF サブテーブルの親キー)
  ├─ [YANG leafref]  BGP_GLOBALS_AF_AGGREGATE_ADDR     (サブテーブルの親キー)
  ├─ [YANG leafref]  BGP_GLOBALS_AF_NETWORK            (サブテーブルの親キー)
  ├─ [暗黙] DEVICE_METADATA.localhost.bgp_asn          (default VRF の local_asn フォールバック)
  ├─ [暗黙] DEVICE_METADATA.localhost.docker_routing_config_mode  (unified/separated 動作切替)
  ├─ [暗黙] VRF.vni                                    (VRF-VNI マッピング, zebra 連携)
  ├─ [暗黙] ROUTE_REDISTRIBUTE (同 VRF)               (local_asn 設定後に再適用)
  ├─ [暗黙] BGP_NEIGHBOR / BGP_NEIGHBOR_AF (同 VRF)   (local_asn 設定後に再適用)
  └─ [暗黙] BGP_GLOBALS_EVPN_VNI / _EVPN_RT / _EVPN_VNI_RT  (local_asn 依存でスキップ/許可)
```

## evidence 一覧

| 参照先 | frrcfgd.py 行番号 | 内容 |
|--------|-------------------|------|
| `DEVICE_METADATA.localhost.bgp_asn` | L2162-2166, L2374, L2445-2446 | 起動時読込、metadata_handler、__get_vrf_asn フォールバック |
| `DEVICE_METADATA.localhost.docker_routing_config_mode` | L2167-2170, L2344 | 起動時読込、unified/separated 判定 |
| `VRF` (vni) | L2271-2273, L2413-2440 | vrf_vni_map 構築、VNI 設定/削除 |
| `ROUTE_REDISTRIBUTE` | L2704 | local_asn 設定後の __apply_dep_vrf_table |
| `BGP_NEIGHBOR` / `BGP_NEIGHBOR_AF` | L2849-2853 | local_asn 設定後の dependent テーブル再適用 |
| `BGP_GLOBALS_EVPN_VNI` 等 | L2100-2103, L2308-2310, L2659 | VRF-based テーブルとして local_asn チェック共有 |
