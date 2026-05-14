# bgp-neighbor — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `BGP_NEIGHBOR`

### CLI
- `config bgp startup/shutdown all`
- `vtysh` 経由 neighbor コマンド群 (bgpcfgd が CONFIG_DB へ書き戻し)
  - ソース: `sonic-utilities/config/main.py, sonic-frr bgpcfgd`

### minigraph / sonic-cfggen
- あり: `sonic-cfggen -m <minigraph.xml>` 実行時に本テーブルが生成・上書きされる

### REST / gNMI (sonic-mgmt-common)
- sonic-mgmt-common OpenConfig BGP neighbor 経由

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- なし

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- `bgpcfgd` が FRR running-config を CONFIG_DB と同期
