---
title: TACACS+ 認証（pam_tacplus / nss_tacplus と AAA / TACPLUS テーブル）
area: management
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/SONiC
    path: doc/aaa/TACACS+ Authentication.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - AAA
    - TACPLUS
    - TACPLUS_SERVER
  cli:
    - config aaa authentication
    - config tacacs
    - show aaa
    - show tacacs
  yang: []
---

!!! success "裏取りステータス: Code-verified"
    `sonic-host-services/scripts/hostcfgd` L354 `class AaaCfg`、L2185 で `self.aaacfg = AaaCfg(self.config_db)`、L2224-2225 で `init_data['TACPLUS']` / `init_data['TACPLUS_SERVER']` 初期化、L748-752 で `/etc/pam.d/sshd` と `/etc/pam.d/login` を `common-auth` ↔ `common-auth-sonic` で切替、L28-35 で `PAM_AUTH_CONF_TEMPLATE = "common-auth-sonic.j2"` / `NSS_TACPLUS_CONF_TEMPLATE = "tacplus_nss.conf.j2"` を確認。`pam_tacplus` の `source_ip` パッチは `sonic-buildimage/src/tacacs/pam/0006-Add-support-for-source-ip-address.patch` で当たっている。CLI は `sonic-utilities/config/aaa.py` L200-318 に `config tacacs` / `add` / `delete` 全部取り込み済み（verified at: 2026-05-09）。

# TACACS+ 認証（pam_tacplus / nss_tacplus と AAA / TACPLUS テーブル）

## 概要

SONiC は SSH / コンソールログインで TACACS+ サーバを使った認証をサポートする。Linux の Pluggable Authentication Modules (PAM) と Name Service Switch (NSS) の枠組みに **`pam_tacplus`** と **`nss_tacplus`** を組み込み、CONFIG_DB の `AAA` / `TACPLUS` / `TACPLUS_SERVER` テーブルから `hostcfgd` が PAM/NSS 設定ファイルを生成する[^1]。

主要要件（HLD §Requirements）[^1]:

- SSH と console の両方で TACACS+ ログイン認証
- TACACS+ パケットの送信元 IP 指定
- 複数 TACACS+ サーバ + 優先度
- ローカル認証と TACACS+ 認証の順序設定
- fail_through（あるサーバで失敗したら次へ）
- **root のみローカル認証** に固定

## 動作仕様

### 全体構成

```mermaid
flowchart LR
  CLI[config aaa / config tacacs] --> CDB[(ConfigDB:<br>AAA / TACPLUS /<br>TACPLUS_SERVER)]
  CDB --> HC[hostcfgd<br>AAA Config Module]
  HC --> PAM[/etc/pam.d/common-auth-sonic/]
  HC --> NSS[/etc/tacplus_nss.conf]
  HC --> NSWITCH[/etc/nsswitch.conf]
  SSH[SSH] --> PAMLIB[PAM libs]
  CON[Console] --> PAMLIB
  PAMLIB --> PAM
  PAMLIB --> TAC[(TACACS+ Server)]
```

`hostcfgd` の AAA module が CONFIG_DB を購読し、PAM/NSS 設定ファイルをホスト上に生成する。SSH/console の認証フローは標準 PAM 経由で `pam_tacplus.so` を呼ぶ[^1]。

### pam_tacplus の拡張

`pam_tacplus` は server / secret / timeout 等の標準オプションは持つが **送信元 IP 指定が無い** ため、SONiC は `source_ip` を加えるパッチを当てている[^1]。

### nss_tacplus と権限テーブル

TACACS+ 認証ユーザは通常 `/etc/passwd` に存在しないため、TACACS+ 認証だけでは getpwnam が失敗してログインが切れる。SONiC は **`nss_tacplus`** を NSS プラグインとして導入し、`getpwnam_r()` で TACACS+ サーバから user privilege を取得し、ローカルにユーザレコードを擬似的に提供する[^1]。

`/etc/tacplus_nss.conf` で TACACS+ 接続情報（と権限テーブル）を保持する。`hostcfgd` の AAA module がこのファイルを更新する[^1]。

#### 既定の権限テーブル

| user privilege | user info | gid | secondary groups | shell |
|----------------|-----------|-----|------------------|-------|
| 15 | `remote_user_su` | 1000 | `sudo,docker` | `/bin/bash` |
| 1 〜 14 | `remote_user`    | 999  | `docker`      | `/bin/bash` |

`/etc/tacplus_nss.conf` で再定義した例[^1]（`netops` と `operator` を分割）:

```
user_priv=7;pw_info=netops;gid=999;group=docker;shell=/bin/bash
user_priv=1;pw_info=operator;gid=999;group=docker;shell=/bin/rbash
```

| user privilege | user info | shell |
|----------------|-----------|-------|
| 15      | `remote_user_su` | `/bin/bash` |
| 14 〜 7 | `netops`         | `/bin/bash` |
| 1 〜 6  | `operator`       | `/bin/rbash` |

ホームディレクトリは `/home/<username>` に作成される。

#### 有効化

`nss_tacplus` は既定では無効。TACACS+ 認証を有効化したときに `/etc/nsswitch.conf` の `passwd` 行へ `tacplus` を追記する[^1]:

```
passwd: compat tacplus
```

### PAM configuration

既存 `common-auth` をそのまま編集すると他のアプリ（cron など）に影響するため、SONiC は **`/etc/pam.d/common-auth-sonic`** を独立に作成し、SSH / login がこれを参照するように差し替える[^1]。

#### パターン 1: 2 サーバ、`source_ip` 指定、`fail_through` 無効

```
auth [success=done new_authtok_reqd=done default=ignore auth_err=die] pam_unix.so nullok try_first_pass
auth [success=done new_authtok_reqd=done default=ignore auth_err=die] pam_tacplus.so server=10.65.254.222:49 secret=test123 login=pap timeout=3 source_ip=100.0.0.9 try_first_pass
auth [success=1 default=ignore] pam_tacplus.so server=10.65.254.248:49 secret=test123 login=pap timeout=3 source_ip=100.0.0.9 try_first_pass
auth requisite pam_deny.so
auth required  pam_permit.so
```

`auth_err=die` により最初のサーバで認証エラーが返ったら **次サーバを試さない**（fail_through 無効）[^1]。

#### パターン 2: `fail_through` 有効

```
auth [success=done new_authtok_reqd=done default=ignore] pam_unix.so nullok try_first_pass
auth [success=1   new_authtok_reqd=done default=ignore] pam_tacplus.so server=10.65.254.223:49 secret=test123 login=pap timeout=5 try_first_pass
auth requisite pam_deny.so
auth required  pam_permit.so
```

`auth_err=die` を外すことで失敗時に次の TACACS+ 行へフォールスルーする。

#### パターン 3: TACACS+ 優先 + root はローカル

```
auth [success=1 new_authtok_reqd=done default=ignore] pam_succeed_if.so user = root debug
auth [success=done new_authtok_reqd=done default=ignore] pam_tacplus.so server=10.65.254.222:49 secret=test123 login=pap timeout=3 try_first_pass
auth [success=1 default=ignore] pam_unix.so nullok try_first_pass
auth requisite pam_deny.so
auth required  pam_permit.so
```

冒頭の `pam_succeed_if user=root` で root だけ TACACS+ をスキップさせる構造[^1]。

<!-- evidence:
source: sonic-net/SONiC/doc/aaa/TACACS+ Authentication.md#L104-L146 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  If TACACS+ Authentication is enabled, a new PAM configuration file "common-auth-sonic" is created
  and replaced in login and ssh, and the other application which authentication include "common-auth" will not be affected.
reasoning: 専用 PAM ファイル分離と root ローカル限定の根拠。
-->

### CONFIG_DB スキーマ

#### `AAA`

```
key = "authentication"
protocol    = LIST(local, tacacs+)   ; pam modules
fallback    = "True"|"False"
failthrough = "True"|"False"
```

#### `TACPLUS` (global)

```
key = "global"
passkey   = 1*32VCHAR
auth_type = pap|chap|mschap
src_ip    = IPAddress
timeout   = 1-99
```

#### `TACPLUS_SERVER`

```
key = <server IP>
tcp_port  = 1-65535
passkey   = 1*32VCHAR
auth_type = pap|chap|mschap
priority  = 1-64
timeout   = 1-99
```

`TACPLUS_SERVER` のフィールドは `TACPLUS` のグローバル値を **個別に上書き** する形で評価される[^1]。

## 設定

### 関連する CLI

```
config aaa authentication login {local | tacacs+}
config aaa authentication failthrough enable|disable
show aaa

config tacacs src_ip <ADDRESS>
config tacacs timeout <0-60>
config tacacs authtype {pap|chap|mschap}
config tacacs passkey <TEXT>
config tacacs add <ADDRESS> --port <1-65535> --timeout <0-60> --key <TEXT> --type {pap|chap|mschap} --pri <1-64>
config tacacs delete <ADDRESS>
show tacacs
```

CLI は `sonic-utilities` の click モジュールで実装される[^1]。

### 設定例

```bash
config tacacs src_ip 100.0.0.9
config tacacs add 10.65.254.222 --port 49 --key test123 --type pap --pri 1
config tacacs add 10.65.254.248 --port 49 --key test123 --type pap --pri 2
config aaa authentication login tacacs+
config aaa authentication failthrough enable
```

## 制限事項

- **root はローカルのみ**: 要件として明示されており、TACACS+ では root を認証できない[^1]。
- **`pam_tacplus` 上流に `source_ip` が無い**: SONiC は独自パッチで対応。upstream 取り込み状況は別途確認が必要[^1]。
- **TACACS+ 認可・アカウンティング**: 本 HLD は **認証** に閉じる。authorization / accounting は別の設計（pam_tacplus 自体は対応するが本 HLD では言及最小）[^1]。
- **ホームディレクトリ作成**: 認証成功時に `/home/<username>` を作成する仕様。ディスク逼迫時の挙動は未規定。

## 干渉する機能

- **`hostcfgd`**: 本機能の本体。`AAA` / `TACPLUS` / `TACPLUS_SERVER` を購読して PAM/NSS ファイルを再生成する。`hostcfgd` 停止中は CONFIG_DB 変更が反映されない。
- **`/etc/pam.d/common-auth`**: SONiC は **触らない**。共通 auth を変えると他サブシステム（cron 等）に波及するため、専用 `common-auth-sonic` を分離して使う[^1]。
- **NSS の `passwd` ライン**: 本機能を有効化すると `tacplus` が追記される。他 NSS プラグイン（ldap 等）と共存させる場合は順序に注意。

## トラブルシューティング

- ログインは認証通るがホームディレクトリが無い: `nss_tacplus` の `getpwnam_r` 経路、`/etc/tacplus_nss.conf` の権限テーブルを確認。
- `source_ip` が反映されない: `pam_tacplus` のパッチ取り込み状況、PAM 設定行の `source_ip=` を確認。
- フェイルオーバーしない: PAM の `auth_err=die` の有無を確認。`failthrough enable` 時は `die` を外す構造。
- root が TACACS+ に流れる: `pam_succeed_if user=root` の前置きが入っているか確認。

## 引用元

[^1]: `sonic-net/SONiC` `doc/aaa/TACACS+ Authentication.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`
