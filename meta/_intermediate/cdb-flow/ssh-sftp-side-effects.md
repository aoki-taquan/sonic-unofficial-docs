# SSH SFTP サブシステム — 副次書込調査 (Phase F)

## 調査対象
- `sonic-host-services/scripts/hostcfgd`
- 対象クラス: `SshServer`, `PamLimitsCfg`
- 範囲: SFTP サブシステムに関連する副次書込経路

## 概要

`SSH_SFTP` テーブルは存在せず、SFTP サブシステムは CONFIG_DB の管理外。
Phase F の調査対象は「`SSH_SERVER|POLICIES` 変更時に hostcfgd が副次的に書込む先があるか」に限定される。
その書込チェーンは `ssh-config-base` と同一経路を通るが、SFTP サブシステム自体には一切書込まない。

## 呼び出しチェーン (SFTP 視点)

```
CONFIG_DB subscribe('SSH_SERVER') → ssh_handler(key, op, data)    [L2478, L2297-2301]
  ├─ sshscfg.policies_update(key, data)           [L2298]
  │   └─ set_policies(ssh_policies)               [L1110-1160]
  │       ├─ copy2(SSH_CONFG, SSH_CONFG_TMP)      [L1113]  ← /etc/ssh/sshd_config 全体をコピー
  │       │   ※ Subsystem sftp 行はここで引き継がれる（変更なし）
  │       ├─ SSH_CONFIG_NAMES のフィールドのみ書き換え [L1142]  ← Subsystem キーなし → SFTP 行は不変
  │       ├─ sshd -T -f SSH_CONFG_TMP  (検証)    [L1150]
  │       │   ├─ OK: os.rename(SSH_CONFG_TMP, SSH_CONFG)   [L1152]
  │       │   │        systemctl restart ssh                [L1154]
  │       │   └─ NG: os.remove(SSH_CONFG_TMP)              [L1160]
  │       └─ max_sessions は continue でスキップ（PAM管理）
  └─ pamLimitsCfg.update_config_file()            [L2299]
      └─ read_max_sessions_config()               [L1434]
          └─ render_conf_file()                   [L1456-1479]
              ├─ open(PAM_LIMITS_CONF, 'w')       [L1466]  ← /etc/pam.d/pam-limits-conf
              └─ open(LIMITS_CONF, 'w')           [L1474]  ← /etc/security/limits.conf
```

## 副次書込先一覧

| 書込先 | ファイル / サービス | 書込者 | 条件 |
|-------|------------------|-------|------|
| ファイルシステム | `/etc/ssh/sshd_config` | `SshServer.set_policies()` | sshd -T 検証成功後（Subsystem sftp 行はそのまま保持） |
| サービス再起動 | `ssh.service` (systemd) | `run_cmd(['systemctl', 'restart', 'ssh'])` | sshd -T 検証成功後 |
| ファイルシステム | `/etc/pam.d/pam-limits-conf` | `PamLimitsCfg.render_conf_file()` | PAM limits 更新 |
| ファイルシステム | `/etc/security/limits.conf` | `PamLimitsCfg.render_conf_file()` | max_sessions 変化時 |
| APPL_DB | なし | — | — |
| STATE_DB | なし | — | — |
| ASIC_DB | なし | — | — |

## DB 書込なし根拠

`SshServer.set_policies()` および `PamLimitsCfg.render_conf_file()` はファイルシステムとサービス管理のみを操作し、swsscommon DB API を呼び出さない。
`HostConfigDaemon` は `state_db_conn` を保持するが、SSH ハンドラーチェーンから STATE_DB への書込は行われない（`state_db_conn` は FIPS 統計専用, L2160）。

SFTP サブシステム自体には副次書込経路が存在せず、`set_policies()` 内で Subsystem 行への変更操作は一切発生しない。

## 証跡コード箇所

- `sonic-host-services/scripts/hostcfgd` L1110-1160: `SshServer.set_policies()`
- `sonic-host-services/scripts/hostcfgd` L67-75: `SSH_CONFIG_NAMES`（Subsystem キーなし）
- `sonic-host-services/scripts/hostcfgd` L1150-1160: `sshd -T` 検証ゲートおよびロールバック
- `sonic-host-services/scripts/hostcfgd` L1152-1155: `systemctl restart ssh`
- `sonic-host-services/scripts/hostcfgd` L1418-1479: `PamLimitsCfg.update_config_file()` / `render_conf_file()`
- `sonic-host-services/scripts/hostcfgd` L2297-2301: `ssh_handler`
- `sonic-host-services/scripts/hostcfgd` L2160: `state_db_conn` = FIPS 用途専用
