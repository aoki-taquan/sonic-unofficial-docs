---
title: 設定
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
---

# 設定

ここでは AAA バックエンドと管理面ポリシーの最小構成を、どの reference を引いて投入すればよいかという観点でまとめます。詳細な CLI / DB スキーマは個別 reference ページに既に存在するため、本ページはあくまで導線として機能します。

## 認証バックエンドの選び方

SONiC は local user に加えて TACACS+、RADIUS、LDAP の三つの外部バックエンドを持ちます。組み合わせは `config aaa` 系コマンドで設定し、最終的に `CONFIG_DB` の `AAA` テーブルと、各バックエンドのサーバー一覧テーブルに格納されます。

| バックエンド | 用途 | 設定の入口 | サーバーリスト |
| --- | --- | --- | --- |
| local | 緊急ログインの最後の砦 | `config aaa authentication login local` | 不要（`/etc/passwd` 等） |
| TACACS+ | 商用機器標準、per-command 認可と accounting | `config tacacs ...` | [`TACPLUS_SERVER`](../../reference/config-db/tacplus-server.md) |
| RADIUS | キャリアグレードの集中認証 | `config aaa ...` + RADIUS テーブル | 既存 reference を参照 |
| LDAP | 既存ディレクトリへの統合 | `config aaa ...` + LDAP テーブル | [`LDAP_SERVER`](../../reference/config-db/ldap-server.md) |

CLI の全体像は [config aaa](../../reference/cli/config-aaa.md) を、YANG モデル経由の表現は [sonic-system-aaa](../../reference/yang/sonic-system-aaa.md) を参照してください。バックエンド単位の典型設定と注意点は以下にあります。

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

## 最小構成のチェックリスト

1. 外部 AAA を入れる前に、`admin` 相当の local user のパスワードを十分長いものへ更新する。詳細は [運用](operations.md) で扱う [password hardening](../../architecture/pw-hardening-design.md) を参照。
2. TACACS+ / RADIUS / LDAP のサーバーを最低 2 台登録し、`login_method` の末尾に `local` を残す。
3. SSH の `permit_root_login` を `no` 相当に倒し、`ciphers` / `kex` を必要なものだけに絞る。
4. banner で「許可された運用者のみ」「アクセスは記録される」旨を明示し、法的要件を満たす。
5. serial console の `inactivity_timeout` を有効にし、置き忘れセッションを切る。

これ以降の運用面（password reset、default credential、トラブルシュート）は [運用](operations.md) に続きます。
