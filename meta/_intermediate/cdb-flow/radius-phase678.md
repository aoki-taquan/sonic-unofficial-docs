# RADIUS — Phase 6/7/8 派生・分岐 証跡

## Phase 6: 自動派生 (assignment scan)

`hostcfgd` の `HostConfigDaemon` が `RADIUS` テーブルを購読し、PAM/NSS 設定ファイルを生成する。

| 派生先 | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| PAM 設定 `auth_type` | `RADIUS.auth_type` が未設定 | デフォルト `pap` | `hostcfgd.py` |
| PAM 設定 `port` | `RADIUS.auth_port` が未設定 | デフォルト `1812` | `hostcfgd.py` |
| PAM 設定 `timeout` | `RADIUS.timeout` が未設定 | デフォルト `5` | `hostcfgd.py` |
| PAM 設定 `retransmit` | `RADIUS.retransmit` が未設定 | デフォルト `3` | `hostcfgd.py` |
| NSS 設定 | `RADIUS_SERVER` エントリ存在 | `/etc/nsswitch.conf` の passwd/shadow を更新 | `hostcfgd.py` |

## Phase 7: 条件付き登録 (add_manager 条件)

| 条件 | 影響 | ソース |
|---|---|---|
| `hostcfgd` は常時起動 | `RADIUS` テーブルは無条件購読 | `hostcfgd.py` |
| `aaa.authentication.login` に `radius` が含まれる | PAM 設定を radius 用に切り替え | `hostcfgd.py` |
| `aaa.authentication.login` に `radius` が含まれない | RADIUS サーバ設定はあっても PAM に反映されない | `hostcfgd.py` |

## Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `hostcfgd` RADIUS handler | `passkey` フィールドあり | PAM 設定に `secret=<passkey>` を設定 | `hostcfgd.py` |
| `hostcfgd` RADIUS handler | `auth_type==chap` | PAM に `chap` オプションを追加 | `hostcfgd.py` |
| `hostcfgd` RADIUS handler | `auth_type==mschapv2` | PAM に `mschapv2` オプションを追加 | `hostcfgd.py` |
| `hostcfgd` RADIUS handler | `src_ip` あり | `source_ip=<src_ip>` を PAM 設定に追加 | `hostcfgd.py` |
| `hostcfgd` RADIUS handler | `vrf_name` あり | `vrf=<vrf_name>` を PAM 設定に追加 | `hostcfgd.py` |

> **スキャン証跡**: `RADIUS` テーブルは PAM/NSS 設定ファイル生成のための入力。`hostcfgd` が `RADIUS` + `RADIUS_SERVER` + `AAA` テーブルを合わせて処理する。CONFIG_DB 内フィールド間の自動付与はデフォルト値の補完のみ。
