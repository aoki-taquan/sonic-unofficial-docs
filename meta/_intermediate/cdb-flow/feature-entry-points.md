# feature — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `FEATURE`

### CLI
- `config feature state <feature> enabled/disabled`
- `config feature autorestart <feature> enabled/disabled`
  - ソース: `sonic-utilities/config/feature.py`

### minigraph / sonic-cfggen
- なし

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- `init_cfg.json.j2` の `FEATURE` セクションでプラットフォーム対応フィーチャーがデフォルト値付きで注入

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- `featured` デーモンが systemd サービス状態を監視し FEATURE テーブルと同期
