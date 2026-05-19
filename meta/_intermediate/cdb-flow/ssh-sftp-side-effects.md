# ssh-sftp — Phase F 副次 DB 書込 調査証跡

## 調査対象ソース

- `sonic-host-services/scripts/hostcfgd`
- `sonic-host-services/host_modules/file_service.py`

## 主な知見

`SSH_SERVER|POLICIES` を書き込んだ後、`hostcfgd` が起動する副次処理は**すべてファイルシステム操作とプロセス再起動**であり、DB への副次書込みは検出されなかった。

## ファイルシステムへの副次書込み

### /etc/ssh/sshd_config

`SshServer.set_policies()` は `copy2(SSH_CONFG, SSH_CONFG_TMP)` → 設定置換 → `sshd -T` バリデーション → `os.rename(tmp, SSH_CONFG)` のフローで `/etc/ssh/sshd_config` を更新する (hostcfgd:1110-1161)。

`Subsystem sftp` 行はこのフローで変更されない (`SSH_CONFIG_NAMES` にキーなし)。

### /etc/pam.d/pam-limits-conf および /etc/security/limits.conf

`PamLimitsCfg.render_conf_file()` が `SSH_SERVER|POLICIES.max_sessions` 設定時に以下を更新する (hostcfgd:1456-1479):

- `/etc/pam.d/pam-limits-conf` — `pam_limits.j2` テンプレートから生成
- `/etc/security/limits.conf` — `limits.conf.j2` テンプレートから生成 (`max_sessions` 値が埋め込まれる)

これは `ssh_handler()` 内で `pamLimitsCfg.update_config_file()` を呼び出す副次処理 (hostcfgd:2299)。

## プロセス再起動

`systemctl restart ssh` が `set_policies()` 成功時に呼ばれる (hostcfgd:1154-1155)。これは SSH サービス (sshd) の再起動であり DB 操作ではない。

## DB スキャン結果

| DB | 書込みの有無 | 根拠 |
|----|------------|------|
| APPL_DB | なし | `hostcfgd` の `SshServer` / `PamLimitsCfg` はいずれも DB 書込みを行わない |
| STATE_DB | なし | 同上 |
| ASIC_DB | なし | SSH は SAI 非経由 |
| FLEX_COUNTER_DB | なし | 同上 |
| COUNTERS_DB | なし | 同上 |
| LOGLEVEL_DB | なし | hostcfgd は syslog 経由でログを出力するのみ |
| CONFIG_DB | なし | `SSH_SERVER` テーブル自体への書き戻しなし |

## 参照コード箇所

- `hostcfgd:1110-1161` — `SshServer.set_policies()`: `/etc/ssh/sshd_config` 更新と `systemctl restart ssh`
- `hostcfgd:1408-1479` — `PamLimitsCfg.update_config_file()` / `render_conf_file()`: `/etc/pam.d/pam-limits-conf` / `/etc/security/limits.conf` 更新
- `hostcfgd:2297-2299` — `ssh_handler()`: `policies_update()` + `pamLimitsCfg.update_config_file()` の呼び出し
- `hostcfgd:81-84` — ファイルパス定数: `PAM_LIMITS_CONF_TEMPLATE`, `LIMITS_CONF_TEMPLATE`, `PAM_LIMITS_CONF`, `LIMITS_CONF`
