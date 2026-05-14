# bgp-globals — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `BGP_GLOBALS`

### CLI
- `config bgp graceful-restart enable/disable`
- `vtysh` 経由 bgpcfgd が多くのグローバル設定を書き戻し
  - ソース: `sonic-utilities/config/main.py, sonic-frr bgpcfgd`

### minigraph / sonic-cfggen
- あり: `sonic-cfggen -m <minigraph.xml>` 実行時に本テーブルが生成・上書きされる

### REST / gNMI (sonic-mgmt-common)
- sonic-mgmt-common OpenConfig BGP global 経由

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- なし

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- `bgpcfgd` が FRR running-config を読み CONFIG_DB と同期
