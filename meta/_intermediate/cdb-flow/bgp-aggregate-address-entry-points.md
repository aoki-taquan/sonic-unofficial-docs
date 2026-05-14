# bgp-aggregate-address — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `BGP_AGGREGATE_ADDRESS`

### CLI
- `vtysh` 経由: `aggregate-address <prefix>` (FRR コンフィグ → bgpcfgd が CONFIG_DB へ書き戻し)
  - ソース: `sonic-buildimage/src/sonic-frr/patch (bgpcfgd)`

### minigraph / sonic-cfggen
- なし

### REST / gNMI (sonic-mgmt-common)
- sonic-mgmt-common OpenConfig BGP ポリシー経由

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- なし

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- `bgpcfgd` が FRR running-config を読み CONFIG_DB と同期
