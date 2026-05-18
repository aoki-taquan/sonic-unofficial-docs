# SSH_SERVER — Phase F 副次 DB 書込スキャンノート

対象テーブル: `SSH_SERVER`
Consumer: `hostcfgd` / `SshServer` + `PamLimitsCfg` (`sonic-host-services/scripts/hostcfgd`)
スキャン範囲: `SshServer.set_policies()`, `PamLimitsCfg.update_config_file()`, `PamLimitsCfg.render_conf_file()`, `ssh_handler()` 全行精読

---

## 副次 DB 書込の有無

`SSH_SERVER` テーブルの変更に伴う副次 DB 書込は **存在しない**。

### スキャン根拠

`SshServer.set_policies()` (hostcfgd:L1110-1159):
- `copy2()` / `os.rename()` / `subprocess.run()` / `run_cmd()` のみ呼び出し
- `ConfigDBConnector` / `DBConnector` / `NotificationProducer` / `ProducerStateTable` の書込呼出: **0 件**
- `swsscommon` 書込系 API (`set(`/`hset`/`produce`/`publish`) の呼出: **0 件**

`PamLimitsCfg.render_conf_file()` (hostcfgd:L1456-1479):
- `jinja2.Environment.get_template().render()` → `open(PAM_LIMITS_CONF, 'w')` / `open(LIMITS_CONF, 'w')` のみ
- DB 書込: **0 件**

`ssh_handler()` (hostcfgd:L2297-2301):
- `self.sshscfg.policies_update()` → `set_policies()` (ファイル書込のみ)
- `self.pamLimitsCfg.update_config_file()` → `render_conf_file()` (ファイル書込のみ)
- DB 書込: **0 件**

`hostcfgd` 全体での `STATE_DB` 書込:
- `FipsCfg` クラス (`hostcfgd:L1759-1821`) のみが `state_db_conn` を使用
- `SshServer` / `PamLimitsCfg` は `state_db_conn` を保持しない

---

## 副次影響（ファイルシステム）

副作用はすべて Linux ホスト OS の設定ファイル書き換えに閉じる:

| 書込先ファイル | 処理クラス | 契機 |
|-------------|----------|------|
| `/etc/ssh/sshd_config` | `SshServer.set_policies()` | `SSH_SERVER|POLICIES` SET 時 |
| `/etc/ssh/sshd_config.tmp` (中間) | `SshServer.set_policies()` | `sshd -T` 検証中の一時ファイル（検証後 rename または削除） |
| `/etc/security/limits.conf` | `PamLimitsCfg.render_conf_file()` | `max_sessions` 変更時（`ssh_handler` → `update_config_file` 経由）|
| `/etc/pam.d/pam-limits-conf` | `PamLimitsCfg.render_conf_file()` | 同上 |

---

## サマリ

| 副次 DB | 書込有無 | 根拠 |
|---|---|---|
| APPL_DB | なし | `SshServer` / `PamLimitsCfg` 内に Producer/Table 書込呼出 0 件 (hostcfgd:L1110-1479 grep `set(`/`hset`/`Producer`/`Notification` → 0 ヒット) |
| STATE_DB | なし | `SshServer` / `PamLimitsCfg` は `state_db_conn` を保持しない。STATE_DB 参照は `FipsCfg` のみ (hostcfgd:L1759-1821) |
| COUNTERS_DB | なし | `hostcfgd` 全体に COUNTERS_DB 参照なし |
| ASIC_DB / FLEX_COUNTER_DB / LOGLEVEL_DB | なし | SAI 非経由。SSH_SERVER を購読する orchagent は存在しない |
