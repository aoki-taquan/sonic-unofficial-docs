# SSH_SERVER 暗黙参照マップ (Phase C)

生成日: 2026-05-16  
調査対象: `sonic-host-services/scripts/hostcfgd`

## 参照関係の整理

### SSH_SERVER → DEVICE_METADATA（暗黙参照）

`PamLimitsCfg.update_config_file()` は `DEVICE_METADATA` テーブルを `get_table('DEVICE_METADATA')` で読み込み、`localhost` キーの存在確認を行う（L1422, L1430）。

- `"localhost" not in device_metadata and "POLICIES" not in ssh_server_policies` の場合は early return
- `localhost["hwsku"]` / `localhost["type"]` を PAM limits テンプレートに渡す
- つまり `SSH_SERVER|POLICIES.max_sessions` の反映には `DEVICE_METADATA|localhost` の存在が前提

### SSH_SERVER → AAA（間接参照：/etc/pam.d/sshd 共有）

`AaaCfg.modify_conf_file()` は `/etc/pam.d/sshd` を直接書き換える（L748-751）。

- AAA の認証方式（TACACS+/RADIUS/LDAP）が変わると `/etc/pam.d/sshd` の `@include` 行が `common-auth-sonic` に切り替わる
- SSH_SERVER の `password_authentication` と PAM の認証スタックは**独立した設定ファイル**だが、sshd が両方を参照するため実質的に連動する
- `PasswordAuthentication yes` + PAM `common-auth-sonic`（TACACS+）の組み合わせで TACACS+ 認証が有効になる

### SSH_SERVER → MGMT_INTERFACE（間接参照：TACACS/RADIUS src_intf 経由）

`AaaCfg.get_interface_ip()` が TACACS+/RADIUS の `src_intf` に `eth0` を指定すると `MGMT_INTERFACE` テーブルの IP を参照する（L600）。SSH_SERVER テーブルは MGMT_INTERFACE を直接参照しないが、SSH 認証バックエンドとして TACACS+/RADIUS を使用する場合、AAA の `src_intf` → `MGMT_INTERFACE` の IP 解決が SSH 認証経路に影響する。

## サマリ

| 参照方向 | このテーブル | 相手テーブル | 条件 |
|---------|------------|-------------|------|
| SSH_SERVER → | `max_sessions` (PamLimitsCfg) | `DEVICE_METADATA` | `update_config_file()` が localhost キー確認。不在時 early return |
| SSH_SERVER ← | `PasswordAuthentication` (sshd_config) | `AAA` | AAA が /etc/pam.d/sshd を書き換え、パスワード認証と PAM 認証スタックが連動 |
| SSH_SERVER ← (間接) | SSH 認証経路 | `MGMT_INTERFACE` | TACACS+/RADIUS の src_intf=eth0 時に MGMT_INTERFACE の IP を解決 |

## evidence

- `sonic-host-services/scripts/hostcfgd` L1422-1430: PamLimitsCfg.update_config_file() の DEVICE_METADATA 参照
- `sonic-host-services/scripts/hostcfgd` L744-751: AaaCfg.modify_conf_file() の /etc/pam.d/sshd 書き換え
- `sonic-host-services/scripts/hostcfgd` L596-606: AaaCfg.get_interface_ip() の MGMT_INTERFACE 参照
- `sonic-host-services/scripts/hostcfgd` L2297-2299: ssh_handler() — SSH_SERVER 変更時に sshscfg + pamLimitsCfg を逐次実行
