# ssh-config-base — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/ssh-config-base.md` Phase C 追加分。
`SSH_SERVER|POLICIES` テーブルに対して `hostcfgd` の `SshServer` クラスおよび `PamLimitsCfg` クラスが持つ暗黙参照関係を整理する。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-host-services/scripts/hostcfgd` | `SshServer` (L1045–1175)、`PamLimitsCfg` (L1408–1480)、`HostConfigDaemon.__init__` (L2191–2277)、`ssh_handler` (L2297–2299)、`config_db.subscribe('SSH_SERVER', ...)` (L2478) |

## YANG leafref

`sonic-ssh-server.yang` は `SSH_SERVER|POLICIES` のフィールドに対して他テーブルへの leafref を持たない。全依存は実装レベルの暗黙参照。

## 暗黙参照 (実装レベル)

### 1. CONFIG_DB `DEVICE_METADATA|localhost` (PAM limits 更新の前提条件)

- **参照先テーブル**: `CONFIG_DB DEVICE_METADATA` キー `localhost`
- **参照方向**: 読み取り（`PamLimitsCfg.update_config_file()` 内）
- **条件**: early-return ガード (`hostcfgd` L1430)
- **意味**: `SSH_SERVER|POLICIES` と `DEVICE_METADATA|localhost` の両方が不在の場合、PAM limits の書き込みをスキップして即時 return する。通常デプロイでは `DEVICE_METADATA|localhost` は必ず存在するが、テスト・ミニマル構成では注意が必要。
- **evidence**: `hostcfgd` L1430

### 2. `/etc/ssh/sshd_config` (書き込み先ファイル)

- **参照先**: ファイルシステム `/etc/ssh/sshd_config`
- **参照方向**: 読み取り + 書き込み（`SshServer.set_policies()` 内）
- **条件**: 常時。ファイルが存在しない / 読み取り不可の場合は更新失敗
- **意味**: `set_policies()` は `copy2(sshd_config → sshd_config.tmp)` を実行してから差分更新する。ファイルが存在しなければ例外が発生し hostcfgd のエラーログに記録される。
- **evidence**: `hostcfgd` L1113 (`copy2`)、L1142 (`modify_single_file_inplace`)

### 3. `/etc/security/limits.conf` および `/etc/pam.d/pam-limits-conf` (PAM limits 書き込み先)

- **参照先**: ファイルシステム `/etc/security/limits.conf`、`/etc/pam.d/pam-limits-conf`
- **参照方向**: 書き込み（`PamLimitsCfg.render_conf_file()` 内）
- **条件**: `update_config_file()` が early-return しないとき（SSH_SERVER または DEVICE_METADATA が存在する場合）
- **意味**: `max_sessions` の実効値（`None` or 整数）が Jinja2 テンプレート経由でレンダリングされる。ディレクトリが存在しない場合は例外をキャッチして ERR ログのみ記録。
- **evidence**: `hostcfgd` L1460–1475 (`render_conf_file`)

### 4. `ssh.service` (systemd unit)

- **参照先**: `ssh.service` (systemd unit)
- **参照方向**: `systemctl restart ssh` 呼び出し
- **条件**: `sshd -T` 検証成功後（`set_policies()` 末尾）
- **意味**: `systemctl restart ssh` が失敗した場合、sshd_config の更新は完了しているが sshd プロセスへの反映は行われない。
- **evidence**: `hostcfgd` L1152–1155 (`os.rename` + `systemctl restart ssh`)

### 5. `/usr/sbin/sshd` バイナリ (設定検証ゲート)

- **参照先**: `/usr/sbin/sshd` (外部バイナリ)
- **参照方向**: `sshd -T -f <tmp>` 実行（検証のみ）
- **条件**: `set_policies()` の全フィールド反映後
- **意味**: `sshd -T` の返り値が非 0 の場合、一時ファイルを削除して全フィールドをロールバックする。YANG に定義された値でも古い OpenSSH バージョンでは検証失敗の可能性がある。
- **evidence**: `hostcfgd` L1150–1160 (`subprocess.run sshd -T`)

## 参照関係サマリ

```
CONFIG_DB SSH_SERVER|POLICIES
  ↓ (subscribe / get_table)
hostcfgd SshServer + PamLimitsCfg

暗黙参照:
  ├─ [暗黙] CONFIG_DB DEVICE_METADATA|localhost  — PAM limits early-return ガード (L1430)
  ├─ [暗黙] /etc/ssh/sshd_config                 — 読み書き対象ファイル (L1113, L1142)
  ├─ [暗黙] /etc/security/limits.conf            — PAM limits 書き込み先 (L1468–1475)
  ├─ [暗黙] /etc/pam.d/pam-limits-conf           — PAM モジュール設定書き込み先 (L1460–1466)
  ├─ [暗黙] systemd ssh.service                  — systemctl restart ssh (L1152–1155)
  └─ [暗黙] /usr/sbin/sshd バイナリ              — sshd -T 検証ゲート (L1150–1160)
```

## evidence

- `sonic-host-services/scripts/hostcfgd` L1045–1175 (`SshServer.set_policies`, `modify_conf_file`)
- `sonic-host-services/scripts/hostcfgd` L1408–1480 (`PamLimitsCfg.update_config_file`, `render_conf_file`)
- `sonic-host-services/scripts/hostcfgd` L2191–2277 (`HostConfigDaemon.__init__`, `sshscfg.load`)
- `sonic-host-services/scripts/hostcfgd` L2297–2299 (`ssh_handler`)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ssh-server.yang` — leafref 定義なし確認
