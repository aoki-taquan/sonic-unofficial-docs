# RADIUS — 副次書込・副次動作 (Phase F) 調査証跡

## 調査対象

`sonic-host-services/scripts/hostcfgd` — `AaaCfg.radius_global_update()` (L527-533) と `modify_conf_file()` (L641-860)

## 結論

`RADIUS` の処理経路では **Redis DB（STATE_DB / APPL_DB / COUNTERS_DB など）への書き込みは一切発生しない**。副次書込は OS ファイルシステムへの設定ファイル再生成と systemd サービス制御のみ。

## 副次書込詳細

### PAM 設定ファイル

| ファイルパス | 操作 | 条件 | evidence |
|-------------|------|------|---------|
| `/etc/pam.d/common-auth-sonic` | 上書き (atomic rename) | 常時 | `hostcfgd:728-731` |
| `/etc/pam.d/sshd` | `sed -i` 相当 (`@include common-auth` → `common-auth-sonic` or 逆) | PAM_AUTH_CONF 存否に応じて | `hostcfgd:733-738` |
| `/etc/pam.d/login` | 同上 | 同上 | `hostcfgd:733-738` |
| `/etc/pam_radius_auth.d/<ip>_<port>.conf` | 新規作成または上書き (0600) | RADIUS サーバ設定ありかつ `radsrvs_conf` 非空 | `hostcfgd:826-837` |

### NSS / RADIUS NSS 設定ファイル

| ファイルパス | 操作 | 条件 | evidence |
|-------------|------|------|---------|
| `/etc/nsswitch.conf` | `sed -i` 相当で `passwd` / `group` / `shadow` 行の `radius` エントリを追加/削除 | `AAA.authentication.login` に `radius` が含まれる場合に追加 | `hostcfgd:748-760` |
| `/etc/radius_nss.conf` | Jinja2 テンプレートから再生成 (`NSS_RADIUS_CONF_TEMPLATE`) | 常時 | `hostcfgd:820-823` |

### systemd サービス制御

| サービス | 操作 | 条件 | evidence |
|---------|------|------|---------|
| `aaastatsd` | `service aaastatsd start` | `AAA.authentication.login` に `radius` があり `RADIUS.statistics == True` | `hostcfgd:840-851` |
| `aaastatsd` | `service aaastatsd stop` | 上記以外 | `hostcfgd:840-851` |

## Redis DB 書込: なし

`modify_conf_file()` 全体を精読した結果、`swsscommon.Table.set()` / `ProducerStateTable` / `ConfigDBConnector.set_entry()` など Redis への書き込みは一切存在しない。`hostcfgd` の RADIUS 経路は純粋にファイルシステムとサービス管理への副次動作のみ。
