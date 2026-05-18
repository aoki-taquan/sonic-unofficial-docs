# ssh-server Phase D — 失敗挙動マトリクス

調査対象: `sonic-net/sonic-host-services/scripts/hostcfgd`  
SshServer クラス (L1045-1175) および PamLimitsCfg クラス (L1408-1460)

## set_policies() 失敗経路

| 失敗条件 | 検出箇所 | 結果 |
|---------|---------|------|
| `ports` が空リスト | `handle_ports_set()` L1091-1093 | `LOG_ERR` + `return` (sshd_config.tmp を /etc/ssh/sshd_config に反映しない) |
| `port_num` が整数型 (str でない) | `handle_ports_set()` L1095-1097 | `LOG_ERR` + `return False` → `set_policies()` も `return` |
| ポート番号が範囲外 (< 1 or > 65535) | `handle_ports_set()` L1098-1100 | `LOG_ERR` + `return False` → `set_policies()` も `return` |
| 整数フィールドが範囲外 | `set_policies()` L1130-1131 | `LOG_ERR` + `continue` (当該フィールドのみスキップ、他フィールドは適用継続) |
| 不明キー (SSH_CONFIG_NAMES 外) | `set_policies()` L1148-1149 | `LOG_ERR` + スキップ |
| `sshd -T -f <tmp>` 検証失敗 (returncode != 0) | `set_policies()` L1160-1163 | `LOG_ERR` + `os.remove(SSH_CONFG_TMP)` → 変更破棄、/etc/ssh/sshd_config は旧値維持 |
| `systemctl restart ssh` 失敗 | `run_cmd()` L123-131 | `LOG_ERR` + `return` (sshd_config は既に更新済み、sshd はリロードされていない不整合) |
| `/etc/ssh/sshd_config` コピー失敗 | `copy2()` L1151 | Python 例外が hostcfgd プロセス全体に伝播 (未 try/except) |

## PamLimitsCfg.update_config_file() 失敗経路

| 失敗条件 | 検出箇所 | 結果 |
|---------|---------|------|
| `SSH_SERVER` テーブル未存在 | L1422-1426 (try/except KeyError) | 例外捕捉後 `pass`、`ssh_server_policies = {}` で処理継続 |
| `DEVICE_METADATA` と `SSH_SERVER` 両方不在 | `update_config_file()` L1430 | `return` (early return、PAM limits 未更新) |
| `render_conf_file()` でファイル書き込み失敗 | Python 例外が伝播 (未 try/except) | hostcfgd 例外ハンドラへ |

## 注意事項

1. `ports` 設定失敗時: `handle_ports_set()` が `return` した場合、`set_policies()` はその後の処理をすべてスキップして `return` する。`sshd_config.tmp` には `Port` 行を削除した状態のファイルが残るが、`sshd -T` 検証は実行されないため /etc/ssh/sshd_config への反映はなし。
2. 整数フィールド範囲外エラーは `continue` (スキップ) のため、他フィールドは sshd_config.tmp に適用される。その結果 `sshd -T` を通過した場合は範囲外フィールドを除いた設定が有効になる (部分適用)。
3. `systemctl restart ssh` 失敗後は sshd_config が更新済みにもかかわらず sshd プロセスが旧設定で稼働し続ける不整合状態になる。手動で `systemctl restart ssh` を実行して回復する必要がある。

Evidence:
- `sonic-host-services/scripts/hostcfgd L1091-1108` (handle_ports_set)
- `sonic-host-services/scripts/hostcfgd L1119-1168` (set_policies メインループと sshd -T ゲート)
- `sonic-host-services/scripts/hostcfgd L1422-1436` (PamLimitsCfg.update_config_file)
