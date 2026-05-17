# SERIAL_CONSOLE / SSH_SERVER — Phase F 副次 DB 書込スキャンノート

対象テーブル: `SERIAL_CONSOLE`, `SSH_SERVER`
Consumer: `hostcfgd` / `SerialConsoleCfg`, `SshServer`, `PamLimitsCfg` (`sonic-host-services/scripts/hostcfgd`)
スキャン範囲: SerialConsoleCfg.update_serial_console_cfg(), SshServer.set_policies(),
            SshServer.modify_conf_file(), PamLimitsCfg.update_config_file(),
            PamLimitsCfg.render_conf_file() 全行精読

---

## 副次 DB 書込の有無

CONFIG_DB `SERIAL_CONSOLE` / `SSH_SERVER` テーブルの変更を受けた `hostcfgd` ハンドラが
副次的に **DB へ書き込む操作は存在しない**。副作用はすべて Linux ホスト OS の
設定ファイル書き換えおよびシステムサービス制御に閉じる。

### grep 結果（`set(`/`hset`/`Producer`/`Notification` 対 SerialConsoleCfg / SshServer / PamLimitsCfg）

- `SerialConsoleCfg` クラス (hostcfgd:2013-2043): DB 書込呼出 0 件。`run_cmd` による
  `service serial-config restart` のみ。
- `SshServer` クラス (hostcfgd:1030-1170): DB 書込呼出 0 件。`os.rename(SSH_CONFG_TMP, SSH_CONFG)`
  および `systemctl restart ssh` のみ。
- `PamLimitsCfg` クラス (hostcfgd:1404-1480): DB 書込呼出 0 件。`open(PAM_LIMITS_CONF, 'w')`
  および `open(LIMITS_CONF, 'w')` のファイル書込のみ。

---

## 副次ファイルシステム書込一覧

| 書込先 (ファイル/サービス) | トリガー | ハンドラ | evidence |
|--------------------------|----------|----------|----------|
| `/etc/ssh/sshd_config` | `SSH_SERVER\|POLICIES` 変化 | `SshServer.set_policies()` → `os.rename(SSH_CONFG_TMP, SSH_CONFG)` | hostcfgd L1150-1153 |
| `systemctl restart ssh` | `/etc/ssh/sshd_config` 更新成功後 | `SshServer.modify_conf_file()` → `run_cmd(['systemctl', 'restart', 'ssh'])` | hostcfgd L1154 |
| `service serial-config restart` | `SERIAL_CONSOLE\|POLICIES` 変化 (キャッシュ差分) | `SerialConsoleCfg.update_serial_console_cfg()` → `run_cmd(['sudo', 'service', 'serial-config', 'restart'])` | hostcfgd L2035 |
| `/etc/pam.d/pam-limits-conf` | `SSH_SERVER\|POLICIES.max_sessions` 変化 | `PamLimitsCfg.render_conf_file()` → `open(PAM_LIMITS_CONF, 'w')` | hostcfgd L1466 |
| `/etc/security/limits.conf` | `SSH_SERVER\|POLICIES.max_sessions` 変化 | `PamLimitsCfg.render_conf_file()` → `open(LIMITS_CONF, 'w')` | hostcfgd L1471 |

---

## 副次 DB 書込なしの確認

| DB | 有無 | 根拠 |
|----|------|------|
| APPL_DB | なし | `SerialConsoleCfg` / `SshServer` / `PamLimitsCfg` 全クラスに `ProducerStateTable` / `Table.set()` 呼出なし |
| STATE_DB | なし | `hostcfgd` の `STATE_DB` 書込は `FipsCfg` (hostcfgd:1759-1821) と `RestartWaiter` のみ。対象クラスは `state_db_conn` を保持しない |
| COUNTERS_DB | なし | `hostcfgd` 全体に COUNTERS_DB 書込なし。CLI セッション設定は SAI 非経由 |
| ASIC_DB / FLEX_COUNTER_DB | なし | `hostcfgd` は SAI/orchagent 非経由。カーネル・デーモン設定のみ |
