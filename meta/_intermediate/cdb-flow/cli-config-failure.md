# SERIAL_CONSOLE / SSH_SERVER — Phase D 失敗モード・エラー処理スキャンノート

対象テーブル: `SERIAL_CONSOLE`, `SSH_SERVER`
Consumer: `hostcfgd` / `SerialConsoleCfg`, `SshServer`, `PamLimitsCfg` (`sonic-host-services/scripts/hostcfgd`)
スキャン範囲: set_policies(), handle_ports_set(), update_config_file(), render_conf_file(),
            update_serial_console_cfg(), ssh_handler(), serial_console_config_handler() 全行精読

---

## 検出した失敗モード・エラー処理

### 1. ports 範囲外 — sshd_config 更新中断・無更新

- `handle_ports_set()` (hostcfgd:1093-1108) はポート番号を `int()` 変換後 `1..65535` 範囲チェックを行う。
- 範囲外の場合 `syslog(LOG_ERR, "Ssh port <N> out of range")` を出力し `return False`。
- 呼び出し元 `set_policies()` (hostcfgd:1116-1119) は `handle_ports_set()` が False を返した場合に `syslog(LOG_ERR, "Failed to update sshd config files - wrong port configuration")` を出力して即時 `return`。
- **影響**: sshd_config 一時ファイルへの書き込みが中断。一時ファイルの cleanup は行われず、`os.rename()` が呼ばれないため既存 `/etc/ssh/sshd_config` が保持される（安全フォールバック）。
- evidence: `hostcfgd:1093-1101`, `hostcfgd:1116-1119`

### 2. 数値フィールド範囲外 — 当該フィールドのみスキップ・処理継続

- `set_policies()` (hostcfgd:1122-1125): `SSH_INT_VALUES` に含まれるフィールド（`authentication_retries`, `login_timeout`, `inactivity_timeout`, `max_sessions`）が `SSH_MIN_VALUES` / `SSH_MAX_VALUES` 範囲外の場合、`syslog(LOG_ERR, "Ssh {} {} out of range")` を出力し `continue`（当該フィールドを skip）。
- **影響**: 範囲外フィールドのみ sshd_config に書き込まれない。他フィールドの処理は継続するため部分適用が発生する可能性がある。
- evidence: `hostcfgd:1122-1125`

### 3. 未知フィールドキー — ログ出力のみ、処理継続

- `set_policies()` (hostcfgd:1147-1148): `SSH_CONFIG_NAMES` マップにも `max_sessions` リストにも含まれないキーは `syslog(LOG_ERR, "Failed to update sshd config file - wrong key {}")` を出力するが `continue` せず処理を継続（`for` ループが次のキーに進む）。
- **影響**: 未知フィールドは sshd_config に書き込まれないが処理は継続する。
- evidence: `hostcfgd:1147-1148`

### 4. sshd -T 検証失敗 — 一時ファイル削除、既存 sshd_config 保持

- `set_policies()` (hostcfgd:1150-1160): 全フィールド処理後に `subprocess.run(['sudo', 'sshd', '-T', '-f', SSH_CONFG_TMP])` で一時ファイルを検証。
- `returncode != 0` の場合: `syslog(LOG_ERR, "Failed to update sshd config file - sshd -T returned {code} with error {stderr}")` を出力し、`os.remove(SSH_CONFG_TMP)` で一時ファイルを削除。`os.rename()` は呼ばれないため `/etc/ssh/sshd_config` は変更されない。
- **影響**: 設定不正時はサービス継続性が保護される（既存 sshd_config 保持）。ただし CONFIG_DB に不正値が書き込まれた状態が継続し、hostcfgd の次回ロード時にも同じ検証失敗が繰り返される。
- evidence: `hostcfgd:1150-1160`

### 5. systemctl restart ssh 失敗 — ログ出力のみ、sshd_config は更新済み

- `set_policies()` (hostcfgd:1153-1157): `sshd -T` 検証成功後 `os.rename()` で sshd_config を更新してから `run_cmd(['systemctl', 'restart', 'ssh'], log_err=True, raise_exception=True)` を呼ぶ。
- `systemctl restart ssh` が失敗した場合: `Exception` をキャッチし `syslog(LOG_ERR, "Failed to update sshd config file")` を出力する。
- **影響**: sshd_config ファイルは更新済みだが sshd プロセスは再起動されていない。DB 値と実際の sshd 設定が**不一致**になる（sshd_config は新しいが、実行中の sshd は旧設定を維持）。次回の `set_policies()` 呼び出しで sshd_config が再更新されて `systemctl restart ssh` が再実行される。
- evidence: `hostcfgd:1152-1157`

### 6. serial-config.service restart 失敗 — キャッシュ未更新、DB 値不反映

- `update_serial_console_cfg()` (hostcfgd:2034-2040): `run_cmd(['sudo', 'service', 'serial-config', 'restart'], True, True)` が失敗した場合、`Exception` をキャッチし `syslog(LOG_ERR, "Failed to update {key} serial-config.service config")` を出力して `return`。
- キャッシュ更新 (`self.cache.update({key: data})`) は `try` ブロックの外（L2040）にあるため、`return` により**キャッシュが更新されない**。
- **影響**: 次回同じフィールドに同じ値が書き込まれた場合、`self.cache.get(key, {}) != data` が True のまま再試行される。serial-config.service が起動していない環境では無限再試行が発生する可能性がある。
- evidence: `hostcfgd:2031-2040`

### 7. PamLimitsCfg.render_conf_file() — テンプレート展開・ファイル書き込み失敗

- `render_conf_file()` (hostcfgd:1456-1479): jinja2 テンプレート展開・ファイル書き込みを `try/except Exception` で囲み、失敗時は `syslog(LOG_ERR, "modify pam_limits config file failed with exception: {}")` を出力する。
- **影響**: PAM limits ファイルが更新されない。`max_sessions` の制限が未反映のまま継続する。
- evidence: `hostcfgd:1476-1479`

### 8. PamLimitsCfg.update_config_file() — SSH_SERVER テーブル不在時の KeyError 抑制

- `update_config_file()` (hostcfgd:1424-1428): `get_table('SSH_SERVER')` を `try/except KeyError` で囲み、テーブル不在時は `ssh_server_policies = {}` のまま処理を継続する（例外を再 raise しない）。
- さらに `if "localhost" not in device_metadata and "POLICIES" not in ssh_server_policies: return` で双方不在時 early return する（hostcfgd:1430-1431）。
- **影響**: SSH_SERVER テーブルが CONFIG_DB に存在しない状態（工場出荷直後等）では PAM limits は無変更のまま維持される（安全な無操作）。
- evidence: `hostcfgd:1424-1431`

---

## 失敗モードサマリ

| # | 失敗箇所 | 検出条件 | ログ | 影響 | 回復方法 |
|---|---------|---------|------|------|---------|
| 1 | `handle_ports_set()` | ports 範囲外 (1-65535 外) | LOG_ERR "Ssh port out of range" | sshd_config 更新中断・既存値保持 | 正値を CONFIG_DB に再設定 |
| 2 | `set_policies()` 数値チェック | 数値範囲外 | LOG_ERR "Ssh {} out of range" | 当該フィールドのみスキップ（部分適用） | 正値を CONFIG_DB に再設定 |
| 3 | `set_policies()` 未知キー | SSH_CONFIG_NAMES にないキー | LOG_ERR "wrong key {}" | 未知キーのみ無視、処理継続 | CONFIG_DB から不正キーを削除 |
| 4 | `sshd -T` 検証失敗 | 一時 sshd_config が不正 | LOG_ERR "sshd -T returned {code}" | 一時ファイル削除、既存 sshd_config 保持 | DB 値を正値に修正 |
| 5 | `systemctl restart ssh` 失敗 | ssh サービス起動失敗 | LOG_ERR "Failed to update sshd config file" | sshd_config は更新済み、実行 sshd は旧設定維持 | `systemctl restart ssh` を手動実行 |
| 6 | `serial-config.service restart` 失敗 | サービス不在 / 起動失敗 | LOG_ERR "Failed to update {key} serial-config.service config" | キャッシュ未更新、設定未反映・再試行ループ | serial-config をインストール / 手動起動 |
| 7 | `render_conf_file()` テンプレート失敗 | jinja2 例外 / 書き込み権限なし | LOG_ERR "modify pam_limits config file failed" | PAM limits 未更新、max_sessions 未反映 | hostcfgd 再起動 + テンプレートファイル確認 |
| 8 | SSH_SERVER テーブル不在 | CONFIG_DB に SSH_SERVER なし | (ログなし・safe early return) | PAM limits 無変更（安全な無操作） | なし（設計上の正常系） |
