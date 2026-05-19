# SSH_SERVER|POLICIES — 副次書込調査 (Phase F)

## 調査対象
- `sonic-host-services/scripts/hostcfgd`
- 対象クラス: `SshServer`, `PamLimitsCfg`

## ssh_handler 呼び出しチェーン

```
CONFIG_DB subscribe('SSH_SERVER') → ssh_handler(key, op, data)    [L2478, L2297-2301]
  ├─ sshscfg.policies_update(key, data)           [L2298]
  │   └─ set_policies(ssh_policies)               [L1110-1160]
  │       ├─ copy2(SSH_CONFG, SSH_CONFG_TMP)      [L1113]  ← /etc/ssh/sshd_config をコピー
  │       ├─ modify_single_file_inplace(SSH_CONFG_TMP, ...) × n  [L1142]  ← tmp に書込
  │       ├─ sshd -T -f SSH_CONFG_TMP  (検証)    [L1150]
  │       │   ├─ OK: os.rename(SSH_CONFG_TMP, SSH_CONFG)   [L1152]  ← /etc/ssh/sshd_config 更新
  │       │   │        systemctl restart ssh                [L1154]  ← ssh.service 再起動
  │       │   └─ NG: os.remove(SSH_CONFG_TMP)              [L1160]  ← ロールバック
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
| ファイルシステム | `/etc/ssh/sshd_config` | `SshServer.set_policies()` | sshd -T 検証成功後 |
| サービス再起動 | `ssh.service` (systemd) | `run_cmd(['systemctl', 'restart', 'ssh'])` | sshd -T 検証成功後 |
| ファイルシステム | `/etc/pam.d/pam-limits-conf` | `PamLimitsCfg.render_conf_file()` | PAM limits 更新 |
| ファイルシステム | `/etc/security/limits.conf` | `PamLimitsCfg.render_conf_file()` | max_sessions 変化時 |
| APPL_DB | なし | — | — |
| STATE_DB | なし | — | — |
| ASIC_DB | なし | — | — |

## DB 書込なし根拠

`SshServer.set_policies()` および `PamLimitsCfg.render_conf_file()` はいずれもファイルシステムとサービス管理のみを操作し、swsscommon DB API を呼び出さない。
`HostConfigDaemon` は `state_db_conn` を保持するが、SSH ハンドラーチェーンから STATE_DB への書込は行われない（`state_db_conn` は FIPS 統計専用）。

## 証跡コード箇所

- `sonic-host-services/scripts/hostcfgd` L1110-1160: `SshServer.set_policies()`
- `sonic-host-services/scripts/hostcfgd` L1150-1160: `sshd -T` 検証ゲートおよびロールバック
- `sonic-host-services/scripts/hostcfgd` L1152-1155: `systemctl restart ssh`
- `sonic-host-services/scripts/hostcfgd` L1418-1479: `PamLimitsCfg.update_config_file()` / `render_conf_file()`
- `sonic-host-services/scripts/hostcfgd` L2297-2301: `ssh_handler`
- `sonic-host-services/scripts/hostcfgd` L2160: `state_db_conn` = FIPS 用途専用
