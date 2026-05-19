# SSH SFTP サブシステム 副次書込調査 (Phase F)

生成日: 2026-05-19  
対象ページ: `docs/reference/config-db/ssh-sftp.md`  
調査コミット: sonic-host-services `c5bbbe8b07b96f078fa4b761316627404b01bd04`

---

## 1. 概要

`SSH_SFTP` テーブルは存在せず、`Subsystem sftp` 行は CONFIG_DB 管理外の OS テンプレートに固定されている。SFTP サブシステム自体のエントリ変化に起因する副次書込は存在しない。

ただし `SSH_SERVER|POLICIES` の変化が `hostcfgd` 経由で `/etc/ssh/sshd_config` と PAM limits ファイルを更新するため、SFTP セッションに間接的に影響する副次処理が発生する。

---

## 2. 副次書込先一覧

| 副次書込先 | ファイル / サービス | 書込者 | 条件 |
|---|---|---|---|
| ファイルシステム | `/etc/ssh/sshd_config` | `SshServer.set_policies()` | `SSH_SERVER|POLICIES` 変化時・sshd -T 検証成功後 |
| サービス再起動 | `ssh.service` (systemd) | `run_cmd(['systemctl', 'restart', 'ssh'])` | sshd -T 検証成功後 |
| ファイルシステム | `/etc/pam.d/pam-limits-conf` | `PamLimitsCfg.render_conf_file()` | `max_sessions` 変化時 |
| ファイルシステム | `/etc/security/limits.conf` | `PamLimitsCfg.render_conf_file()` | `max_sessions` 変化時 |
| APPL_DB | なし | — | — |
| STATE_DB | なし | — | — |
| ASIC_DB | なし | — | — |

---

## 3. sshd_config 更新と SFTP 行への影響

`SshServer.set_policies()` (`hostcfgd L1110-1160`) が実行されるたびに:

1. `copy2(SSH_CONFG, SSH_CONFG_TMP)` で現行 sshd_config を tmp へコピー
2. `SSH_CONFIG_NAMES` のキーのみを tmp に書き込む（`Subsystem` キーは辞書に存在しない）
3. `sshd -T -f SSH_CONFG_TMP` で検証
4. 検証成功時: `os.rename(tmp → SSH_CONFG)` + `systemctl restart ssh`
5. 検証失敗時: `os.remove(tmp)` でロールバック（sshd_config 変化なし）

ステップ 1 のコピーにより `Subsystem sftp /usr/lib/openssh/sftp-server` 行は常に引き継がれる。`SSH_SERVER` 設定変更後も SFTP サブシステムの有効状態に変化はない。

---

## 4. SSH サービス再起動による SFTP セッション切断

`systemctl restart ssh` は sshd の完全再起動を伴う。既存の SSH/SFTP セッションはすべて切断される点に注意。

---

## 5. DB 書込なし根拠

`SshServer.set_policies()` および `PamLimitsCfg.render_conf_file()` はいずれもファイルシステムとサービス管理のみを操作し、swsscommon DB API を呼び出さない。`HostConfigDaemon` が保持する `state_db_conn` は FIPS 統計専用であり、SSH ハンドラーチェーンから STATE_DB への書込は行われない（`hostcfgd:2160`）。

---

## 6. evidence

- `sonic-host-services/scripts/hostcfgd` L67-75: `SSH_CONFIG_NAMES`（`Subsystem` キーなし）
- `sonic-host-services/scripts/hostcfgd` L1110-1160: `SshServer.set_policies()`
- `sonic-host-services/scripts/hostcfgd` L1418-1479: `PamLimitsCfg.update_config_file()` / `render_conf_file()`
- `sonic-host-services/scripts/hostcfgd` L2297-2301: `ssh_handler`
- `sonic-host-services/scripts/hostcfgd` L2160: `state_db_conn` = FIPS 用途専用
