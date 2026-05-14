# mclag-domain — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `MCLAG_DOMAIN`

### CLI
- `config mclag add/del <domain-id> --local_ip <ip> --peer_ip <ip> --peer_link <port>`
  - ソース: `sonic-utilities/config/mclag.py`

### minigraph / sonic-cfggen
- なし

### REST / gNMI (sonic-mgmt-common)
- sonic-mgmt-common xfmr_mclag.go 経由 (OpenConfig MCLAG)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- なし

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- なし
