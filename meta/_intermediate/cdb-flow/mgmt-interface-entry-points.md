# mgmt-interface — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `MGMT_INTERFACE`

### CLI
- `config interface ip add/remove eth0 <ip/prefix> <gateway>`
  - ソース: `sonic-utilities/config/main.py (interface グループ)`

### minigraph / sonic-cfggen
- あり: `sonic-cfggen -m <minigraph.xml>` 実行時に本テーブルが生成・上書きされる

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- `sonic-cfggen -m` で minigraph から Management ポートの IP/GW を生成

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- `caclmgrd` / `mgmtstatsd` が eth0 の状態変化を反映
