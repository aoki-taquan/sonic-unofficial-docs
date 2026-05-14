# auto-techsupport-feature — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `AUTO_TECHSUPPORT_FEATURE`

### CLI
- `config auto-techsupport feature enable/disable <feature>`
- `config auto-techsupport feature rate-limit-interval <feature> <secs>`
- `config auto-techsupport feature available-mem-threshold <feature> <pct>`
  - ソース: `sonic-utilities/config/plugins/auto_techsupport.py`

### minigraph / sonic-cfggen
- なし

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- `init_cfg.json.j2` の `AUTO_TECHSUPPORT_FEATURE` セクションでデフォルト feature リスト (bgp, swss, syncd 等) が注入される

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- なし
