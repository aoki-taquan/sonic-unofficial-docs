# SSH_SERVER (base) — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-19 (chore/q67-f-ssh-config-base-failure)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-net/sonic-host-services/scripts/hostcfgd`

### SET 処理における失敗経路（SshServer.set_policies）

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `ports` リストが空 (`len(values_list) == 0`) | `handle_ports_set()` L1091 | `return False` → `set_policies()` がその時点で `return`。他フィールドも適用されない | LOG_ERR: "Failed to update sshd config files - wrong port configuration" | `hostcfgd:1091,1117-1119` |
| `ports` 内のポート番号が整数型 (`isinstance(port_num, int)`) | `handle_ports_set()` L1093 | `return False` → 同上 | LOG_ERR: "port num value {} in wrong format" | `hostcfgd:1094-1095` |
| `ports` 内のポート番号が `1`〜`65535` の範囲外 | `handle_ports_set()` L1097-1099 | `return False` → 同上 | LOG_ERR: "Ssh port {} out of range" | `hostcfgd:1100` |
| 整数フィールド (`authentication_retries` 等) が min/max 範囲外 | `set_policies()` L1122-1124 | そのフィールドのみ `continue`（スキップ）。残フィールドは適用続行 | LOG_ERR: "Ssh {} {} out of range" | `hostcfgd:1124` |
| 未知のキー（`SSH_CONFIG_NAMES` に無く `max_sessions` でもない） | `set_policies()` L1148 | そのフィールドのみスキップ（処理継続） | LOG_ERR: "Failed to update sshd config file - wrong key {}" | `hostcfgd:1148` |
| `sshd -T -f sshd_config.tmp` が非ゼロで失敗 | `set_policies()` L1150-1160 | `sshd_config.tmp` を削除してロールバック。今回の全変更が破棄される | LOG_ERR: "Failed to update sshd config file - sshd -T returned {} with error {}" | `hostcfgd:1159-1160` |
| `systemctl restart ssh` が例外 | `set_policies()` L1152-1157 | 例外を catch して ERR ログのみ。sshd_config は置換済みだが ssh サービス未再起動 | LOG_ERR: "Failed to update sshd config file" | `hostcfgd:1154-1157` |
| `copy2(SSH_CONFG, SSH_CONFG_TMP)` が `OSError` | `set_policies()` L1113 | 例外が伝播（未捕捉）。`set_policies()` 全体が中断 | スタックトレースが syslog へ | `hostcfgd:1113` |

### PAM limits 失敗経路（PamLimitsCfg.render_conf_file）

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `jinja2.TemplateError` など Jinja2 テンプレートレンダリング例外 | `render_conf_file()` L1459-1478 | `except Exception` で捕捉して ERR ログのみ。PAM limits ファイル未更新 | LOG_ERR: "modify pam_limits config file failed with exception: {}" | `hostcfgd:1478` |
| `open(PAM_LIMITS_CONF, 'w')` / `open(LIMITS_CONF, 'w')` が `OSError` | `render_conf_file()` L1469, L1476 | `except Exception` で捕捉して ERR ログのみ | LOG_ERR: 同上 | `hostcfgd:1478` |
| `SSH_SERVER` テーブルへの `get_table()` で `KeyError` | `update_config_file()` L1425-1427 | `except KeyError` で捕捉して silent skip。`ssh_server_policies = {}` のまま | なし | `hostcfgd:1426-1427` |

### ロールバック粒度まとめ

- **フィールド単位の失敗**（範囲外値・未知キー）: そのフィールドのみ `continue` でスキップ。他フィールドは `sshd_config.tmp` に書き込まれ、`sshd -T` 成功後に本番へ反映される。
- **`ports` フィールド失敗**: `set_policies()` 全体が `return`。今回の全フィールドが破棄される（前回の `sshd_config` が維持）。
- **`sshd -T` 検証失敗**: `sshd_config.tmp` を削除してロールバック。全変更が破棄される。
- **`systemctl restart ssh` 失敗**: `sshd_config` は書き換わっているが ssh サービスが旧設定で動作し続ける（不整合状態）。

### grep カバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `LOG_ERR` (SshServer) | 5 | `hostcfgd:1095, 1100, 1118, 1124, 1148, 1157, 1159` |
| `LOG_ERR` (PamLimitsCfg) | 1 | `hostcfgd:1478` |
| `except KeyError` (silent) | 1 | `hostcfgd:1426-1427` |
| `sshd -T` ロールバック | 1 | `hostcfgd:1159-1160` |
| `os.remove(SSH_CONFG_TMP)` | 1 | `hostcfgd:1160` |

<!-- /failure -->
