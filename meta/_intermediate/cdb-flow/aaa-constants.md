# AAA — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-host-services/scripts/hostcfgd` (PAM/NSS パス、TACACS+/RADIUS デフォルト、Linux login.def デフォルト、FIPS リスト)
- `sonic-host-services/scripts/ldap.py` (LDAP デフォルトポート・タイムアウト・TLS 暗号スイート)

---

## 1. PAM / NSS 設定ファイルパス (hostcfgd L28-54)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `PAM_AUTH_CONF` | `/etc/pam.d/common-auth-sonic` | SONiC 用 PAM auth 共通インクルードファイル (テンプレートから再生成) | hostcfgd L28 |
| `PAM_AUTH_CONF_TEMPLATE` | `/usr/share/sonic/templates/common-auth-sonic.j2` | `PAM_AUTH_CONF` 生成元の Jinja2 テンプレート | hostcfgd L29 |
| `PAM_PASSWORD_CONF` | `/etc/pam.d/common-password` | パスワードポリシー PAM 設定ファイル | hostcfgd L30 |
| `PAM_PASSWORD_CONF_TEMPLATE` | `/usr/share/sonic/templates/common-password.j2` | パスワードポリシー PAM テンプレート | hostcfgd L31 |
| `NSS_TACPLUS_CONF` | `/etc/tacplus_nss.conf` | libnss-tacplus 設定ファイル | hostcfgd L34 |
| `NSS_TACPLUS_CONF_TEMPLATE` | `/usr/share/sonic/templates/tacplus_nss.conf.j2` | TACACS+ NSS テンプレート | hostcfgd L35 |
| `NSS_RADIUS_CONF` | `/etc/radius_nss.conf` | libnss-radius 設定ファイル | hostcfgd L36 |
| `NSS_RADIUS_CONF_TEMPLATE` | `/usr/share/sonic/templates/radius_nss.conf.j2` | RADIUS NSS テンプレート | hostcfgd L37 |
| `PAM_RADIUS_AUTH_CONF_TEMPLATE` | `/usr/share/sonic/templates/pam_radius_auth.conf.j2` | pam_radius_auth サーバごとの設定テンプレート | hostcfgd L38 |
| `NSS_CONF` | `/etc/nsswitch.conf` | NSS スイッチ設定ファイル (`passwd:` 行を書換) | hostcfgd L39 |
| `LDAP_CONF_TEMPLATE` | `/usr/share/sonic/templates/ldap.conf.j2` | LDAP クライアント設定テンプレート | hostcfgd L40 |
| `LDAP_CONF` | `/etc/ldap/ldap.conf` | LDAP クライアント設定ファイル | hostcfgd L41 |
| `NSLCD_CONF_TEMPLATE` | `/usr/share/sonic/templates/nslcd.conf.j2` | nslcd (nsswitch LDAP デーモン) 設定テンプレート | hostcfgd L42 |
| `NSLCD_CONF` | `/etc/nslcd.conf` | nslcd 設定ファイル | hostcfgd L43 |
| `PAM_SESSION_CONF` | `/etc/pam.d/common-session` | PAM session 共通設定 (mkhomedir ルール挿入対象) | hostcfgd L44 |
| `PAM_SESSION_NONINT_CONF` | `/etc/pam.d/common-session-noninteractive` | PAM session noninteractive 共通設定 | hostcfgd L45 |
| `ETC_PAMD_SSHD` | `/etc/pam.d/sshd` | sshd 用 PAM 設定 (`common-auth` インクルードを書換) | hostcfgd L50 |
| `ETC_PAMD_LOGIN` | `/etc/pam.d/login` | login 用 PAM 設定 (`common-auth` インクルードを書換) | hostcfgd L51 |
| `ETC_LOGIN_DEF` | `/etc/login.defs` | Linux パスワードエージング設定 | hostcfgd L52 |
| `RADIUS_PAM_AUTH_CONF_DIR` | `/etc/pam_radius_auth.d/` | pam_radius_auth がサーバごとの conf を読み込むディレクトリ。サーバ追加ごとに `{ip}_{auth_port}.conf` を 0600 で生成 | hostcfgd L97, L829 |

---

## 2. PAM モジュール / セッションルール (hostcfgd L47-49)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `MKHOME_DIR_RULE` | `session required pam_mkhomedir.so skel=/etc/skel/ umask=0022 silent` | リモート認証ユーザのホームディレクトリ自動作成 PAM ルール (`common-session` に挿入) | hostcfgd L47 |
| `MKHOME_DIR_LIB` | `pam_mkhomedir.so` | mkhomedir モジュール名 (ルール存在チェック用) | hostcfgd L48 |
| `MKHOME_DIR_LIB_REG` | `.*pam_mkhomedir` | mkhomedir ルール検出正規表現 | hostcfgd L49 |
| `PAM_SESSION_LAST_LINE` | `# end of pam-auth-update config` | `common-session` 末尾検出用マーカ (mkhomedir ルール挿入位置を決定) | hostcfgd L46 |

---

## 3. TACACS+ サーバデフォルト (hostcfgd L86-89)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `TACPLUS_SERVER_PASSKEY_DEFAULT` | `""` (空文字列) | `TACPLUS_SERVER.passkey` 未指定時のデフォルト (= passkey なし) | hostcfgd L87, L369 |
| `TACPLUS_SERVER_TIMEOUT_DEFAULT` | `"5"` 秒 | `TACPLUS_SERVER.timeout` 未指定時のデフォルト | hostcfgd L88, L368 |
| `TACPLUS_SERVER_AUTH_TYPE_DEFAULT` | `"pap"` | `TACPLUS_SERVER.auth_type` 未指定時のデフォルト認証方式 | hostcfgd L89 |

> TACACS+ TCP ポートは libnss-tacplus / pam_tacplus 側で 49 (well-known) がデフォルト。`hostcfgd` 内で TACACS+ ポート定数は定義されておらず、CONFIG_DB の `tcp_port` (YANG default 49) が直接 NSS/PAM テンプレートに渡される。

---

## 4. RADIUS サーバデフォルト (hostcfgd L91-97)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `RADIUS_SERVER_AUTH_PORT_DEFAULT` | `"1812"` | `RADIUS_SERVER.auth_port` 未指定時のデフォルト UDP ポート (RFC 2865) | hostcfgd L92, L376 |
| `RADIUS_SERVER_PASSKEY_DEFAULT` | `""` (空文字列) | RADIUS 共有秘密未指定時のデフォルト | hostcfgd L93 |
| `RADIUS_SERVER_RETRANSMIT_DEFAULT` | `"3"` | `RADIUS_SERVER.retransmit` 未指定時の再送回数 | hostcfgd L94 |
| `RADIUS_SERVER_TIMEOUT_DEFAULT` | `"5"` 秒 | `RADIUS_SERVER.timeout` 未指定時のタイムアウト | hostcfgd L95, L379 |
| `RADIUS_SERVER_AUTH_TYPE_DEFAULT` | `"pap"` | `RADIUS_SERVER.auth_type` 未指定時のデフォルト認証方式 | hostcfgd L96 |
| `RADIUS_SERVER_SKIP_MSG_AUTH` | `False` | Message-Authenticator 属性スキップフラグのデフォルト | hostcfgd L98 |

---

## 5. LDAP デフォルト (ldap.py L8-18)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `LdapCfg.PORT` | `389` (TCP) | `LDAP_SERVER.port` 未指定時のデフォルト LDAP ポート (RFC 4511; LDAPS は 636 だが定数化されていない) | ldap.py L15 |
| `LdapCfg.TIMEOUT_SEARCH` | `5` 秒 | `LDAP.search_timeout` 未指定時のデフォルト検索タイムアウト | ldap.py L13 |
| `LdapCfg.TIMEOUT_BIND` | `5` 秒 | `LDAP.bind_timeout` 未指定時のデフォルト bind タイムアウト | ldap.py L14 |
| `LdapCfg.VERSION` | `'3'` | LDAP プロトコルバージョンデフォルト | ldap.py L12 |
| `LdapCfg.BASE` | `'ou=users,dc=example,dc=com'` | `LDAP.base_dn` 未指定時のサンプル base_dn (本番では必ず上書き必要) | ldap.py L9 |
| `LdapCfg.BIND` | `''` (空) | bind DN デフォルト (= anonymous bind) | ldap.py L10 |
| `LdapCfg.BINDPW` | `""` (空) | bind パスワードデフォルト | ldap.py L11 |
| `LdapCfg.SCOPE` | `"sub"` | デフォルト LDAP 検索スコープ (subtree) | ldap.py L16 |
| `LdapCfg.HOST` | `""` (空) | デフォルト LDAP ホスト | ldap.py L17 |
| `LdapCfg.IPV6` | `6` | IPv6 識別用定数 (アドレスファミリー判定) | ldap.py L18 |
| `TLS1_2` cipher suite | `SECURE128:SECURE192:SECURE256:-VERS-TLS1.0:-VERS-DTLS1.0:-VERS-TLS1.1:-SHA1` | LDAPS TLS1.2 GnuTLS 暗号スイート (固定) | ldap.py L4 |
| `TLS1_3` cipher suite | `SECURE128:SECURE192:SECURE256:-VERS-TLS-ALL:-VERS-DTLS-ALL:+VERS-TLS1.3` | LDAPS TLS1.3 GnuTLS 暗号スイート (固定) | ldap.py L5 |

---

## 6. Linux login.def デフォルト (hostcfgd L57-58)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `LINUX_DEFAULT_PASS_MAX_DAYS` | `99999` | パスワードハードニング無効時のパスワード最大有効日数 (Debian デフォルト) | hostcfgd L57 |
| `LINUX_DEFAULT_PASS_WARN_AGE` | `7` | パスワード期限切れ前警告日数 (Debian デフォルト) | hostcfgd L58 |

---

## 7. FIPS / 関連サービス再起動 (hostcfgd L101-103)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `FIPS_CONFIG_FILE` | `/etc/sonic/fips.json` | FIPS モード設定ファイル | hostcfgd L101 |
| `OPENSSL_FIPS_CONFIG_FILE` | `/etc/fips/fips_enable` | OpenSSL FIPS 有効化フラグファイル | hostcfgd L102 |
| `DEFAULT_FIPS_RESTART_SERVICES` | `['ssh', 'telemetry.service', 'restapi']` | FIPS 切替時に再起動する固定サービスリスト | hostcfgd L103 |

---

## 8. nslcd サービス制御 (hostcfgd L241-251)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `nslcd` ユニット名 | `nslcd` (systemd) | LDAP 設定変更時の再起動対象。LDAP 無効時は stop + mask | hostcfgd L244, L250-251 |

---

## 特記事項

1. **TACACS+ ポート定数なし**: pam_tacplus / libnss-tacplus は IANA well-known TCP/49 をデフォルトで使う。`hostcfgd` 内に `49` のリテラルは出現せず、CONFIG_DB `TACPLUS_SERVER.tcp_port` (YANG default = 49) が直接テンプレートに渡される。
2. **LDAPS ポート 636 はハードコードされていない**: `LdapCfg.PORT = 389` のみ。LDAPS 使用時はユーザが `LDAP_SERVER.port` で明示指定する必要あり。`ldap_mode` (`ldap`/`ldaps`) によって URI スキームのみ切替 (ldap.py L58)。
3. **`LdapCfg.BASE` のサンプル値**: `'ou=users,dc=example,dc=com'` は明らかなプレースホルダ。本番では `LDAP.base_dn` を必ず CLI 設定すること。未設定の場合 nslcd は example.com を検索しに行き全リモートユーザ認証が失敗する。
4. **pam_radius_auth サーバごと conf ファイル形式**: `{ip}_{auth_port}.conf` (例: `192.0.2.10_1812.conf`) を `/etc/pam_radius_auth.d/` に 0600 権限で生成 (hostcfgd L829-837)。CONFIG_DB から `RADIUS_SERVER` エントリを削除しても、このファイルは自動削除されない (`aaa_update()` 全再生成依存)。
5. **mkhomedir セッションルールの umask**: `0022` (世界読取可能) がハードコード。`/etc/skel/` からホームを複製する。リモート認証ユーザの最初のログイン時に呼ばれる。
6. **TLS1_2 / TLS1_3 暗号スイート**: GnuTLS priority string 形式。OpenLDAP クライアント (`/etc/ldap/ldap.conf`) と nslcd の両方に渡される。SHA1 を明示的に除外 (`-SHA1`)。
7. **`PAM_AUTH_CONF` が独自パス**: `/etc/pam.d/common-auth-sonic` という SONiC 専用パス。`/etc/pam.d/common-auth` (Debian 標準) は直接書換せず、`sshd` / `login` の include 行のみ `common-auth` → `common-auth-sonic` に書換 (hostcfgd L744-745 周辺)。これにより Debian の `pam-auth-update` 機構を回避。

---

## 出典

- `sonic-net/sonic-host-services/scripts/hostcfgd` L28-54, L57-58, L86-103, L241-251, L367-380, L744-745, L825-837
- `sonic-net/sonic-host-services/scripts/ldap.py` L4-18, L44-80
