# ssh-server — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/ssh-server.md` Phase C 追加分。
`SSH_SERVER|POLICIES` テーブルに対して `hostcfgd` の `SshServer` クラスおよび `PamLimitsCfg` クラスが持つ暗黙参照関係を整理する。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-host-services/scripts/hostcfgd` | `SshServer` (L1045–1175)、`PamLimitsCfg` (L1418–1441)、`HostConfigDaemon.__init__` (L2191–2277)、`ssh_handler` (L2297–2299)、`config_db.subscribe('SSH_SERVER', ...)` (L2478) |

## YANG leafref

`sonic-ssh-server.yang` は `SSH_SERVER|POLICIES` のフィールドに対して他テーブルへの leafref を持たない。全依存は実装レベルの暗黙参照。

## 暗黙参照 (実装レベル)

### 1. CONFIG_DB `DEVICE_METADATA|localhost` (PAM limits 更新の前提条件)

- **参照先テーブル**: `CONFIG_DB DEVICE_METADATA` キー `localhost`
- **参照方向**: 読み取り（`PamLimitsCfg.update_config_file()` 内）
- **条件**: `update_config_file()` 冒頭の early-return ガード (L1430)
- **意味**: `SSH_SERVER|POLICIES` と `DEVICE_METADATA|localhost` のどちらかが存在しない場合、PAM limits の書き込みをスキップして即時 return する。通常デプロイでは `DEVICE_METADATA|localhost` は必ず存在するが、テスト環境やミニマル構成では注意が必要。
- **evidence**: `hostcfgd` L1430

### 2. `/etc/ssh/sshd_config` (書き込み先ファイル)

- **参照先**: ファイルシステム `/etc/ssh/sshd_config`
- **参照方向**: 読み取り + 書き込み（`SshServer.set_policies()` → `modify_conf_file()` 内）
- **条件**: 常時。sshd_config が存在しない / 読み取り不可の場合は更新失敗
- **意味**: `modify_conf_file()` は既存 sshd_config を読み込んで差分更新する。ファイルが存在しなければ `FileNotFoundError` が発生し hostcfgd のエラーログに記録される。
- **evidence**: `hostcfgd` L1073–1090 (`modify_conf_file`)

### 3. `/etc/security/limits.d/` ディレクトリ (PAM limits 書き込み先)

- **参照先**: ファイルシステム `/etc/security/limits.d/`
- **参照方向**: 書き込み（`PamLimitsCfg.update_config_file()` 内）
- **条件**: `max_sessions > 0` のとき
- **意味**: ディレクトリが存在しない場合、PAM limits 設定が反映されない。
- **evidence**: `hostcfgd` L1440

### 4. `ssh.service` (systemd unit)

- **参照先**: `ssh.service` (systemd unit)
- **参照方向**: `systemctl restart ssh` 呼び出し
- **条件**: `sshd -T` 検証成功後（`set_policies()` 末尾）
- **意味**: `systemctl restart ssh` が失敗した場合（非 systemd 環境など）、sshd_config の更新は完了しているが sshd プロセスへの反映は行われない。
- **evidence**: `hostcfgd` L1170–1172

### 5. `/usr/sbin/sshd` バイナリ (設定検証ゲート)

- **参照先**: `/usr/sbin/sshd` (外部バイナリ)
- **参照方向**: `sshd -T -f <tmp>` 実行（検証のみ）
- **条件**: `set_policies()` の全フィールド反映後
- **意味**: `sshd -T` の返り値が非 0 の場合、一時ファイルを削除して全フィールドをロールバックする。sshd バイナリのバージョンによって許容される設定値が異なるため、YANG に定義された列挙値でも古い OpenSSH バージョンでは検証失敗の可能性がある。
- **evidence**: `hostcfgd` L1150–1168

## YANG leafref なし (確認済)

`sonic-ssh-server.yang` の全フィールド (`authentication_retries`, `login_timeout`, `ports`, `inactivity_timeout`, `max_sessions`, `password_authentication`, `permit_root_login`, `ciphers`, `kex_algorithms`, `macs`) に leafref 定義なし。他テーブルへの YANG 制約参照は存在しない。

## 参照関係サマリ

```
CONFIG_DB SSH_SERVER|POLICIES
  ↓ (subscribe / get_table)
hostcfgd SshServer + PamLimitsCfg

暗黙参照:
  ├─ [暗黙] CONFIG_DB DEVICE_METADATA|localhost  — PAM limits early-return ガード (L1430)
  ├─ [暗黙] /etc/ssh/sshd_config                 — 読み書き対象ファイル (L1073–1090)
  ├─ [暗黙] /etc/security/limits.d/              — PAM limits 書き込み先ディレクトリ (L1440)
  ├─ [暗黙] systemd ssh.service                  — systemctl restart ssh (L1170–1172)
  └─ [暗黙] /usr/sbin/sshd バイナリ              — sshd -T 検証ゲート (L1150–1168)
```

## evidence

- `sonic-host-services/scripts/hostcfgd` L1045–1175 (`SshServer.set_policies`, `modify_conf_file`, `handle_ports_set`, sshd -T 検証)
- `sonic-host-services/scripts/hostcfgd` L1418–1441 (`PamLimitsCfg.update_config_file`, DEVICE_METADATA early-return, PAM limits 書き込み)
- `sonic-host-services/scripts/hostcfgd` L2191–2277 (`HostConfigDaemon.__init__`, `sshscfg.load`)
- `sonic-host-services/scripts/hostcfgd` L2297–2299 (`ssh_handler`)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ssh-server.yang` — leafref 定義なし確認
