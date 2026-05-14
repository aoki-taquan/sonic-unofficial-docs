# heartbeat — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `HEARTBEAT`

### CLI
- なし (CLI 書き込みパスなし)

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
- `system-health` / `watchdog` 系デーモンが定期的に heartbeat タイムスタンプを書き込む。CLI 書き込みパスなし
