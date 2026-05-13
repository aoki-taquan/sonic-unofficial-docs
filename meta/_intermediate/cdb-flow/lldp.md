# CONFIG_DB 例外条件分析: LLDP

## Consumer

- `lldpmgrd` (`sonic-buildimage/dockers/docker-lldp/lldpmgrd`): `LLDP|GLOBAL` を購読し、`hello_timer` / `mode` 等を `lldpcli` コマンドに変換して lldpd へ反映する。
- `lldpd`: 実際のフレーム送受信。

## 例外条件

### 1. mode に不正値 → lldpcli 拒否
- `mode` フィールドに `rx_and_tx` / `rx_only` / `tx_only` / `disabled` 以外の文字列が設定された場合、`lldpcli` が不正コマンドエラーを返す。CONFIG_DB へは書けるが lldpd には反映されない。

### 2. hello_timer が 0 または負 → lldpd デフォルト（30 秒）で動作
- `hello_timer` に 0 以下を設定した場合、lldpd が設定を無視してデフォルト 30 秒で動作する可能性がある。YANG 上の range バリデーションが有効な場合は mgmt-framework で拒否される。

### 3. mode=rx_only では自ノード情報が対向に伝わらない
- `mode=receive` / `rx_only` を設定すると自装置の LLDP TLV を送出しない。対向スイッチのトポロジービューに当該ノードが見えなくなる副作用がある（仕様通りだが意図しない誤設定になりやすい）。

### 4. LLDP|GLOBAL エントリが存在しない場合
- エントリが存在しない場合は lldpd がデフォルト設定（hello=30s, mode=tx_and_rx）で起動する。エントリを削除しても lldpd の実行中設定はリセットされず、再起動後にデフォルトへ戻る。
