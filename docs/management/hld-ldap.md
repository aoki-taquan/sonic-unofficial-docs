---
title: LDAP 認証（hostcfgd / nslcd / NSS / PAM 連携）
area: management
verification: hld-only
last_verified: 2026-05-09
sources:
  - repo: sonic-net/SONiC
    path: doc/aaa/ldap/hld_ldap.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - LDAP_TABLE
    - LDAP_SERVER
    - AAA
  cli:
    - config aaa
    - config ldap
    - show ldap
  yang:
    - sonic-system-ldap
---

!!! warning "裏取りステータス: HLD-only / Phase 1"
    HLD は v0.1 / 2023-09 改訂の Phase 1 設計。`LDAP_TABLE` / `LDAP_SERVER` / `AAA` テーブル、`hostcfgd` 内 AAA クラスでの PAM/NSS テンプレート再生成、`config aaa authentication` 系 CLI 拡張、`sonic-system-ldap` YANG が現行 master でこの仕様どおりかは未確認。

# LDAP 認証（hostcfgd / nslcd / NSS / PAM 連携）

## 概要

SONiC スイッチの SSH / シリアルログインを **外部 LDAP サーバで認証** できるようにする Phase 1 設計[^1]。Debian の `libnss-ldapd` / `libpam-ldapd` / `ldap-utils` パッケージを取り込み、`nslcd` デーモンで LDAP との通信を担当する。`hostcfgd` が CONFIG_DB の LDAP 関連テーブルを監視し、`/etc/ldap/ldap.conf` / `/etc/nslcd.conf` / `/etc/nsswitch.conf` / `/etc/pam.d/common-auth-sonic` を再生成する。

ローカル認証フォールバックと、LDAP サーバの優先度に基づく順序的フォールバックをサポート。**REST API（nginx）への適用は TODO**[^1]。

## 動作仕様

### 構成

```mermaid
flowchart LR
    CFG[CONFIG_DB\n LDAP_TABLE / LDAP_SERVER / AAA] --> HC[hostcfgd]
    HC --> CONF[/etc/ldap/ldap.conf\n /etc/nslcd.conf\n /etc/nsswitch.conf\n /etc/pam.d/common-auth-sonic/]
    CONF --> NSLCD[nslcd]
    NSLCD --> LDAPSRV[(LDAP server)]
    SSHD[sshd / login] --> PAM[libpam-ldapd]
    PAM --> NSLCD
    NSS[libnss-ldapd] --> NSLCD
```

### CONFIG_DB スキーマ（HLD より）

```text
LDAP_TABLE|global
    bind_dn       = ""             ; default empty (anonymous bind)
    bind_password = "****"         ; encrypted
    bind_timeout  = 5              ; seconds
    version       = 3              ; LDAPv3
    base_dn       = "ou=users,dc=example,dc=com"
    port          = 389
    timeout       = 5

LDAP_SERVER|<server_ip>
    priority = <int>               ; lower = preferred

AAA
    ; 既存テーブル。authentication フィールドで ldap を有効化
    authentication.login = "ldap,local"
```

### Init / 設定変更フロー

`hostcfgd` の AAA クラスは `LDAP_TABLE` / `LDAP_SERVER` / `AAA` 変更を購読し、jinja2 テンプレートから設定ファイルを再生成して `nslcd` を再起動する。LDAP 無効時は `nslcd` を停止し、PAM/NSS から LDAP モジュールを外す[^1]。

### パッケージ

ビルド時に追加：

- `libnss-ldapd`: NSS モジュール（getent passwd 等が LDAP を引く）
- `libpam-ldapd`: PAM モジュール（ssh login 認証）
- `ldap-utils`: `ldapsearch` / `ldapwhoami` 等のユーティリティ
- `nslcd`: NSS/PAM の lookup を LDAP にプロキシするデーモン（libnss-ldapd の依存）

### 認証フロー

1. ユーザが SSH ログイン → `sshd` が PAM 経由で認証要求
2. `pam_ldap` (libpam-ldapd) が `nslcd` 経由で LDAP サーバに `simple bind` を試行
3. 成功すれば認証 OK、失敗または接続失敗なら `AAA.authentication.login` の次のメソッド（`local` 等）にフォールバック
4. NSS 側 (`libnss-ldapd`) は `getpwnam` 等で LDAP の user/group エントリを返す

`LDAP_SERVER` の priority に基づいて nslcd は複数サーバを試す。

## 設定

### 関連する CONFIG_DB

| Table | 説明 |
|-------|------|
| `LDAP_TABLE` | グローバル LDAP 設定（base_dn / port / version / bind 認証 等） |
| `LDAP_SERVER` | サーバごとの優先度 |
| `AAA` | 既存。`authentication.login` でメソッド順を指定 |

### 関連する CLI

HLD には CLI コマンド名の正式な体系は明記されていないが、既存の `config aaa authentication ...` を拡張する形で `ldap` メソッドを追加すると示唆されている。LDAP 固有設定用の `config ldap` 系コマンドが追加される想定。

### 関連する YANG

`sonic-system-ldap.yang`（HLD ディレクトリに同梱）。

### 設定例

```bash
# LDAP サーバ追加
sudo config ldap server add 10.0.0.1 --priority 1

# グローバル設定
sonic-cfggen -a '{
  "LDAP_TABLE": {
    "global": {
      "base_dn": "ou=users,dc=example,dc=com",
      "version": "3",
      "port": "389",
      "timeout": "5"
    }
  }
}' --write-to-db

# 認証メソッド設定
sudo config aaa authentication login ldap local
```

## 制限事項

- Phase 1 設計のため、TLS/StartTLS や SASL は HLD では言及が少ない（後続 phase で扱う想定）。
- REST API (nginx) への LDAP 認証適用は TODO[^1]。
- `bind_password` は CONFIG_DB に格納される（暗号化方式は HLD で詳細規定なし）。
- `nslcd` 再起動中は短時間ログイン認証が落ちる可能性がある。

## 干渉する機能

- **TACACS+ / RADIUS（既存 AAA）**: 同じ AAA テーブルの authentication.login で並列指定可。順序フォールバックで連動する。
- **`hostcfgd` AAA クラス**: tacacs / radius / ldap いずれの設定変更も同クラスで処理される。
- **NSS**: `getent passwd` 等のシステムコールも LDAP を見るようになる（`/etc/nsswitch.conf` 経由）。
- **REST / gNMI**: REST API 認証は本機能のスコープ外（TODO）。

## トラブルシューティング

- ログイン失敗 → `journalctl -u nslcd` で LDAP サーバ通信ログを確認。
- `getent passwd <user>` で LDAP ユーザが見えない → `/etc/nsswitch.conf` の `passwd:` 行に `ldap` が含まれているか確認。
- 認証は通るが `sudo` で失敗 → group 解決失敗の可能性。`getent group <gid>` で確認。
- bind 失敗 → `LDAP_TABLE.bind_dn` / `bind_password` と `base_dn` の対応、サーバ FQDN 解決を確認。

## 引用元

[^1]: `sonic-net/SONiC` `doc/aaa/ldap/hld_ldap.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`
