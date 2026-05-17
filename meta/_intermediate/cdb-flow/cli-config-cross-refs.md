# cli-config (SERIAL_CONSOLE / SSH_SERVER) — Phase C: 暗黙テーブル参照 (cross-refs)

## 調査対象

- `sonic-host-services/scripts/hostcfgd` (ref: c5bbbe8b07b96f078fa4b761316627404b01bd04)

## 分析

### CONFIG_DB.DEVICE_METADATA → PamLimitsCfg 依存

`PamLimitsCfg.update_config_file()` (hostcfgd:1422,1430) は `DEVICE_METADATA` テーブルの
存在を前提とする。`"localhost" not in device_metadata and "POLICIES" not in ssh_server_policies`
の場合に early return するため、`DEVICE_METADATA|localhost` が未設定の環境では
`SSH_SERVER.max_sessions` の PAM limits 設定が全く適用されない。

### /etc/ssh/sshd_config 書き換えフロー

`SshServer.set_policies()` (hostcfgd:1112-1160):
1. `/etc/ssh/sshd_config` を `.tmp` ファイルへコピー
2. `.tmp` に差分書き換え
3. `sshd -T -f <tmp>` で構文検証
4. 成功 → `os.rename(.tmp, sshd_config)` / 失敗 → `os.remove(.tmp)` で既存保護

### /etc/pam.d/pam-limits-conf

`PamLimitsCfg.render_conf_file()` (hostcfgd:1455-1478) が `pam_limits.j2` テンプレートを
展開して `/etc/pam.d/pam-limits-conf` を上書きする。
`max_sessions == 0` の場合は `render_conf_file()` を呼ばずファイル書き込みをスキップ（無制限）。

### serial-config.service

`SerialConsoleCfg.update_serial_console_cfg()` (hostcfgd:2031-2040) はキャッシュと
差分があった場合のみ `service serial-config restart` を実行する。
load フェーズでは再起動しない（キャッシュ初期化のみ）。

### AAA / /etc/pam.d/sshd との関係

`AaaCfg.modify_conf_file()` が `/etc/pam.d/sshd` / `/etc/pam.d/login` の `@include` 行を
書き換えるが、これは AAA 変更時の別経路であり SSH_SERVER/SERIAL_CONSOLE テーブルとは独立している。

## evidence

- `hostcfgd:1422,1430` — DEVICE_METADATA 参照
- `hostcfgd:1112-1160` — sshd_config 書き換えフロー
- `hostcfgd:1460-1466` — PAM limits conf 書き換え
- `hostcfgd:1150` — sshd -T 検証
- `hostcfgd:2032-2038` — serial-config.service 再起動
- `hostcfgd:748-752` — /etc/pam.d/sshd / login (AAA 経路)
