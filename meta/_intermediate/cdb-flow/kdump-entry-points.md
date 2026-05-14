# kdump — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `KDUMP`

### CLI
- `config kdump enable/disable`
- `config kdump memory <size>`
- `config kdump num-dumps <n>`
  - ソース: `sonic-utilities/config/kdump.py`

### minigraph / sonic-cfggen
- なし

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- `init_cfg.json.j2` の `KDUMP` セクションでデフォルト値 (`enabled: false`, `memory: 0M-2G:256M,2G-4G:320M,...`) が注入

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- `hostcfgd` の kdump ハンドラが kernel crashkernel 設定と同期
