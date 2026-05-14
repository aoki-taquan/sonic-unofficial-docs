# dhcp-server-ipv4 — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `DHCP_SERVER_IPV4`

### CLI
- `config dhcp-server ipv4 add/del <gateway>`
- `config dhcp-server ipv4 enable/disable <gateway>`
  - ソース: `sonic-utilities/config/main.py (dhcp-server グループ)`

### minigraph / sonic-cfggen
- なし

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- なし

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- なし
