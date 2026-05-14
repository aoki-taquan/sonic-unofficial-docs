# TACPLUS_SERVER — Phase 6/7/8 派生・分岐 証跡

## Phase 6: 自動派生 (assignment scan)

`hostcfgd` が `TACPLUS_SERVER` テーブルを読み、TACACS+ 認証の PAM 設定ファイルを生成する。

| 派生先 | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| PAM 設定 `port` | `TACPLUS_SERVER.tcp_port` 未設定 | デフォルト `49` | `hostcfgd.py` |
| PAM 設定 `timeout` | `TACPLUS_SERVER.timeout` 未設定 | デフォルト `5` | `hostcfgd.py` |
| PAM 設定順序 | `TACPLUS_SERVER.priority` フィールド | 昇順にサーバーを PAM 設定に並べる | `hostcfgd.py` |
| NSS 設定 | `TACPLUS_SERVER` エントリ存在 | `/etc/nsswitch.conf` の passwd/shadow を更新 | `hostcfgd.py` |

## Phase 7: 条件付き登録 (add_manager 条件)

| 条件 | 影響 | ソース |
|---|---|---|
| `hostcfgd` は常時起動 | `TACPLUS_SERVER` テーブルは無条件購読 | `hostcfgd.py` |
| `aaa.authentication.login` に `tacacs+` が含まれる | PAM 設定を TACACS+ 用に切り替え | `hostcfgd.py` |
| `aaa.authentication.login` に `tacacs+` が含まれない | TACACS+ サーバー設定があっても PAM に反映されない | `hostcfgd.py` |

## Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `hostcfgd` TACACS+ handler | `auth_type==ascii` | PAM に ascii 認証設定 | `hostcfgd.py` |
| `hostcfgd` TACACS+ handler | `auth_type==pap` | PAM に pap 認証設定 | `hostcfgd.py` |
| `hostcfgd` TACACS+ handler | `auth_type==chap` | PAM に chap 認証設定 | `hostcfgd.py` |
| `hostcfgd` TACACS+ handler | `passkey` フィールドあり | PAM 設定に `secret=<passkey>` を設定 | `hostcfgd.py` |
| `hostcfgd` TACACS+ handler | `vrf_name` フィールドあり | VRF バインドで TACACS+ サーバーに接続 | `hostcfgd.py` |
| `hostcfgd` TACACS+ handler | `src_ip` フィールドあり | ソース IP を指定して接続 | `hostcfgd.py` |
| `hostcfgd` | サーバー削除 | PAM / NSS 設定を更新 | `hostcfgd.py` |

> **スキャン証跡**: `TACPLUS_SERVER` は TACACS+ 認証の設定テーブル。`auth_type` の分岐と `priority` による順序付けが主要な Phase 8 ポイント。RADIUS と同様のパターン。
