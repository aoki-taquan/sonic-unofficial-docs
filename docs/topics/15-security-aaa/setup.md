---
title: 設定
description: 設定 — ここでは AAA バックエンドと管理面ポリシーの最小構成を、どの reference を引いて投入すればよいかという観点でまとめます。詳細な
  CLI / DB スキーマは個別 reference ページに既に存在するため、本ページはあくまで導線として機能します。
area: topics
verification: meta
last_verified: 2026-05-10
sources:
- docs/reference/cli/config-aaa.md
- docs/reference/config-db/tacplus-server.md
- docs/reference/config-db/ldap-server.md
- docs/reference/yang/sonic-system-aaa.md
- docs/management/tacacs-authentication.md
- docs/management/radius-management-user-authentication.md
- docs/management/hld-ldap.md
- docs/management/ssh-server-global-config-hld.md
- docs/management/serial-console-global-config-hld.md
- docs/system/banner-messages-hld.md
related:
  cli:
  - config aaa
  - config banner
  - show aaa
  config_db:
  - AAA
  - TACPLUS_SERVER
  - LDAP_SERVER
  - BANNER_MESSAGE
  - RADIUS
  - TACPLUS
  - RADIUS_SERVER
  yang:
  - sonic-system-aaa
  - sonic-system-tacacs
  - sonic-system-ldap
  - sonic-ssh-server
---

# 設定

ここでは [AAA](../../reference/glossary.md#term-aaa) バックエンドと管理面ポリシーの最小構成を、どの reference を引いて投入すればよいかという観点でまとめます。詳細な CLI / DB スキーマは個別 reference ページに既に存在するため、本ページはあくまで導線として機能します。

## 認証バックエンドの選び方

[SONiC](../../reference/glossary.md#term-sonic) は local user に加えて TACACS+、[RADIUS](../../reference/glossary.md#term-radius)、LDAP の三つの外部バックエンドを持ちます。組み合わせは `config aaa` 系コマンドで設定し、最終的に `CONFIG_DB` の `AAA` テーブルと、各バックエンドのサーバー一覧テーブルに格納されます。

| バックエンド | 用途 | 設定の入口 | サーバーリスト |
| --- | --- | --- | --- |
| local | 緊急ログインの最後の砦 | `config aaa authentication login local` | 不要（`/etc/passwd` 等） |
| TACACS+ | 商用機器標準、per-command 認可と accounting | `config tacacs ...` | [`TACPLUS_SERVER`](../../reference/config-db/tacplus-server.md) |
| RADIUS | キャリアグレードの集中認証 | `config aaa ...` + RADIUS テーブル | 既存 reference を参照 |
| LDAP | 既存ディレクトリへの統合 | `config aaa ...` + LDAP テーブル | [`LDAP_SERVER`](../../reference/config-db/ldap-server.md) |

CLI の全体像は [config aaa](../../reference/cli/config-aaa.md) を、[YANG](../../reference/glossary.md#term-yang) モデル経由の表現は [sonic-system-aaa](../../reference/yang/sonic-system-aaa.md) を参照してください。バックエンド単位の典型設定と注意点は以下にあります。

- [TACACS+ authentication HLD](../../management/tacacs-authentication.md)
- [SONiC TACACS+ improvement](../../management/sonic-tacacs-improvement.md)
- [TACACS+ passkey encryption](../../management/tacacs-passkey-encryption.md)
- [RADIUS management user authentication](../../management/radius-management-user-authentication.md)
- [LDAP HLD](../../management/hld-ldap.md)

## login_method の順序

`config aaa authentication login` で複数バックエンドを列挙できますが、運用上の鉄則は最後を必ず `local` で締めることです。外部サーバー全滅時のロックアウトを避けるためで、[AAA improvements](../../management/aaa-improvements.md) と [TACACS test plan](../../management/tacacs-test-plan.md) の失敗フォールバックシナリオで議論されています。

## SSH と serial console のポリシー

SSH の listen address、port、ciphers、login grace time、max auth tries などは `SSH_SERVER` テーブルにまとめ、`hostcfgd` 経由で `sshd_config` に展開されます。詳細フィールドと意図は [SSH server global config HLD](../../management/ssh-server-global-config-hld.md) を参照してください。

serial console 側は inactivity timeout、login banner との組み合わせ、root login の可否などを `SERIAL_CONSOLE` テーブルで制御します。設計意図は [serial console global config HLD](../../management/serial-console-global-config-hld.md) にあります。

banner メッセージ（login 前と login 後）は `BANNER_MESSAGE` テーブルで管理され、`/etc/issue` と `/etc/motd` に反映されます。詳細は [banner messages HLD](../../system/banner-messages-hld.md) を参照してください。

## 設定の入口の対応

| やりたいこと | CLI | [CONFIG_DB](../../reference/glossary.md#term-config_db) | YANG / [HLD](../../reference/glossary.md#term-hld) |
|---|---|---|---|
| login_method の順序付け | `config aaa authentication login ...` | `AAA\|authentication` | [sonic-system-aaa](../../reference/yang/sonic-system-aaa.md) |
| TACACS+ サーバ追加 | `config tacacs add/delete` | [`TACPLUS_SERVER`](../../reference/config-db/tacplus-server.md) | [TACACS+ HLD](../../management/tacacs-authentication.md) |
| RADIUS サーバ追加 | `config aaa ...` | `RADIUS_SERVER` | [RADIUS HLD](../../management/radius-management-user-authentication.md) |
| LDAP サーバ追加 | `config ldap add/global` | [`LDAP_SERVER`](../../reference/config-db/ldap-server.md) | [LDAP HLD](../../management/hld-ldap.md) |
| SSH 強化 | `config ssh-server ...` | `SSH_SERVER` | [SSH HLD](../../management/ssh-server-global-config-hld.md) |
| serial console policy | `config serial-console ...` | `SERIAL_CONSOLE` | [serial console HLD](../../management/serial-console-global-config-hld.md) |
| banner | `config banner ...` | `BANNER_MESSAGE` | [banner HLD](../../system/banner-messages-hld.md) |

CLI ラッパが用意されていないフィールドは `sonic-cfggen -a '{...}' -w` で CONFIG_DB に直接書きます。`hostcfgd` が `pam_*.conf` / `nsswitch.conf` / `sshd_config` / `/etc/issue` / `/etc/motd` に展開します。

## 設定シナリオ 1: TACACS+ を主、local を fallback とする

最も多い構成です。`tac_plus` を 2 台立て、`config aaa` で順序付け、ロックアウト回避のため末尾に必ず `local` を残します。

```bash
# サーバー登録（passkey は CLI 上は平文 → CONFIG_DB では暗号化保存）
sudo config tacacs add 10.0.10.11 -k MyS3cret -t 5
sudo config tacacs add 10.0.10.12 -k MyS3cret -t 5

# 認証フロー
sudo config aaa authentication login tacacs+ local
sudo config aaa authentication failthrough enable

# 認可・accounting（任意）
sudo config aaa authorization "tacacs+ local"
sudo config aaa accounting    "tacacs+ local"

# 確認
show tacacs
show aaa
```

このとき CONFIG_DB は次のような形になります。

```json
{
    "AAA": {
        "authentication": {"login": "tacacs+,local", "failthrough": "True"},
        "authorization":  {"login": "tacacs+,local"},
        "accounting":     {"login": "tacacs+,local"}
    },
    "TACPLUS": {
        "global": {"auth_type": "pap", "timeout": "5", "passkey": "U2FsdGVk..."}
    },
    "TACPLUS_SERVER": {
        "10.0.10.11": {"priority": "1", "tcp_port": "49", "timeout": "5"},
        "10.0.10.12": {"priority": "1", "tcp_port": "49", "timeout": "5"}
    }
}
```

`show aaa` の典型出力:

```text
AAA authentication login          : tacacs+ local
AAA authentication failthrough    : True
AAA authorization login           : tacacs+ local
AAA accounting login              : tacacs+ local
```

## 設定シナリオ 2: LDAP（AD）統合 + SSH 制限

社内 AD に user を寄せ、ssh は cipher / kex を絞り、root login を禁止する例です。

```bash
# LDAP server とベース DN
sudo config ldap add 10.20.0.50 --port 389 --priority 1
sudo config ldap global set --base "dc=corp,dc=example,dc=com" \
    --bind-dn "cn=sonic,ou=ServiceAccounts,dc=corp,dc=example,dc=com" \
    --bind-password 'AppPass123!'

sudo config aaa authentication login ldap local

# SSH 強化
sudo sonic-cfggen -a '{
  "SSH_SERVER":{"POLICIES":{
     "permit_root_login":"no",
     "max_auth_tries":"3",
     "login_grace_time":"60",
     "ciphers":"aes256-gcm@openssh.com,aes256-ctr",
     "kex_algorithms":"curve25519-sha256,diffie-hellman-group16-sha512"
  }}
}' -w
sudo systemctl restart hostcfgd
```

確認は次の通り。

```bash
show ldap-server
show ssh-server
sudo sshd -T | grep -Ei 'permitrootlogin|ciphers|kex|maxauthtries'
```

## 設定シナリオ 3: banner と serial console の最小ハードニング

法的要件 + 置き忘れセッション切断:

```bash
sudo config banner login    "Authorized access only. Activity is logged."
sudo config banner motd     "SONiC NOS - production fabric"
sudo config serial-console inactivity-timeout 600
sudo config serial-console sysrq-capabilities disabled
```

CONFIG_DB:

```json
{
    "BANNER_MESSAGE": {"global": {"state":"enabled","login":"Authorized access only. Activity is logged.","motd":"SONiC NOS - production fabric"}},
    "SERIAL_CONSOLE": {"POLICIES":{"inactivity_timeout":"600","sysrq_capabilities":"disabled"}}
}
```

`show banner` / `show serial-console` で投入結果を確認します。

## 設定シナリオ 4: RADIUS で per-command 認可

RADIUS で `service-type` / `Cisco-AVPair` ベースの per-command 認可を入れる例。`freeradius` 側で `cisco-avpair="shell:priv-lvl=15"` のような属性を返す前提で、SONiC 側は次のように設定します。

```bash
sudo config aaa authentication login radius local
sudo config aaa authorization "radius local"
sudo config aaa accounting    "radius local"

sudo redis-cli -n 4 HSET 'RADIUS|global' auth_type pap timeout 5 retransmit 3
sudo redis-cli -n 4 HSET 'RADIUS_SERVER|10.0.10.21' priority 1 auth_port 1812 passkey 'R@diusPass'
```

CONFIG_DB:

```json
{
    "AAA": {"authentication":{"login":"radius,local"},"authorization":{"login":"radius,local"},"accounting":{"login":"radius,local"}},
    "RADIUS": {"global": {"auth_type":"pap","timeout":"5","retransmit":"3"}},
    "RADIUS_SERVER": {
        "10.0.10.21": {"priority":"1","auth_port":"1812","passkey":"<encrypted>"}
    }
}
```

`show aaa` と `show radius` で反映を確認、テスト user で `tail -f /var/log/auth.log` を見つつログインして `Accept` が返ることを確認します。

## 設定エラーと対処

| 症状 | 原因 | 対処 |
|---|---|---|
| 外部 AAA 設定後にコンソール / SSH からも入れない | `login_method` の末尾に `local` が無い | recovery USB / シリアル → ONIE rescue → `/etc/sonic/config_db.json` の `AAA` を直接修正 |
| TACACS+ で認証が遅い（10s 超） | 1 台目がダウン、`timeout` が長い、`failthrough` 無効 | `config aaa authentication failthrough enable`、`timeout` を 2-3s に、サーバー priority を見直す |
| `show tacacs` で passkey が `*****` のまま投入が反映されない | `config tacacs add` のオプション順序を誤った | `-k` の値が空白を含む場合は引用、`config tacacs delete` してから再追加 |
| LDAP bind が `Invalid credentials` | bind-dn か password の typo、または AD 側 sAMAccountName / userPrincipalName mismatch | `ldapsearch -x -D ... -W -b ...` で素のクエリを検証 |
| SSH の cipher を絞った後 windows クライアントから繋がらない | クライアント側に modern cipher が無い | クライアント側を更新、または `ciphers` リストに `aes128-ctr` を一時的に追加 |

## 最小構成のチェックリスト

1. 外部 AAA を入れる前に、`admin` 相当の local user のパスワードを十分長いものへ更新する。詳細は [運用](operations.md) で扱う [password hardening](../../architecture/pw-hardening-design.md) を参照。
2. TACACS+ / RADIUS / LDAP のサーバーを最低 2 台登録し、`login_method` の末尾に `local` を残す。
3. SSH の `permit_root_login` を `no` 相当に倒し、`ciphers` / `kex` を必要なものだけに絞る。
4. banner で「許可された運用者のみ」「アクセスは記録される」旨を明示し、法的要件を満たす。
5. serial console の `inactivity_timeout` を有効にし、置き忘れセッションを切る。

これ以降の運用面（password reset、default credential、トラブルシュート）は [運用](operations.md) に続きます。

## 関連リファレンス

- CLI: `config aaa`、`config tacacs`、`config ldap`、`config banner`、`config serial-console`、`show aaa`、`show tacacs`、`show ldap-server`、`show ssh-server`、`show banner`
- CONFIG_DB: `AAA`、`TACPLUS`、`TACPLUS_SERVER`、`RADIUS`、`RADIUS_SERVER`、`LDAP`、`LDAP_SERVER`、`SSH_SERVER`、`SERIAL_CONSOLE`、`BANNER_MESSAGE`
- YANG: [`sonic-system-aaa`](../../reference/yang/sonic-system-aaa.md)、`sonic-system-tacacs`、`sonic-system-ldap`、`sonic-ssh-server`、`sonic-system-banner`
- 関連 HLD: [TACACS+ HLD](../../management/tacacs-authentication.md)、[RADIUS HLD](../../management/radius-management-user-authentication.md)、[LDAP HLD](../../management/hld-ldap.md)、[SSH server global config HLD](../../management/ssh-server-global-config-hld.md)、[serial console HLD](../../management/serial-console-global-config-hld.md)、[banner messages HLD](../../system/banner-messages-hld.md)

<!-- glossary-links-injected: db62d2100cef -->
