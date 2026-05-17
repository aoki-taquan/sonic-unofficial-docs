# ldap-server Phase E: 定数一覧 (Constants)

調査日: 2026-05-17  
調査対象:
- `sonic-host-services/scripts/ldap.py`
- `sonic-host-services/scripts/hostcfgd` (L.40-43, L.106-107)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-system-ldap.yang`
- `sonic-host-services/data/templates/nslcd.conf.j2`
- `sonic-host-services/data/templates/ldap.conf.j2`

---

## LdapCfg クラス定数 (ldap.py)

| 定数名 | 値 | 型 | 用途 |
|--------|----|----|------|
| `LdapCfg.BASE` | `'ou=users,dc=example,dc=com'` | str | `base_dn` 未設定時の fallback |
| `LdapCfg.BIND` | `''` (空文字) | str | `bind_dn` 未設定時の fallback |
| `LdapCfg.BINDPW` | `""` (空文字) | str | `bind_password` 未設定時の fallback |
| `LdapCfg.VERSION` | `'3'` | str | `version` 未設定時の fallback |
| `LdapCfg.TIMEOUT_SEARCH` | `5` | int | `timeout` 未設定時の fallback (秒) |
| `LdapCfg.TIMEOUT_BIND` | `5` | int | `bind_timeout` 未設定時の fallback (秒) |
| `LdapCfg.PORT` | `389` | int | `port` 未設定時の fallback |
| `LdapCfg.SCOPE` | `"sub"` | str | 常時固定 (CONFIG_DB から設定不可) |
| `LdapCfg.HOST` | `""` | str | サーバ未登録時のデフォルト URI 文字列 |
| `LdapCfg.IPV6` | `6` | int | IPv6 判定値 (`ipaddress.ip_address(ip).version == 6`) |

モジュールレベル定数 (ldap.py L.3-4):
- `TLS1_2 = "SECURE128:SECURE192:SECURE256:-VERS-TLS1.0:-VERS-DTLS1.0:-VERS-TLS1.1:-SHA1"` — GnuTLS プライオリティ文字列 (TLS 1.2 用)
- `TLS1_3 = "SECURE128:SECURE192:SECURE256:-VERS-TLS-ALL:-VERS-DTLS-ALL:+VERS-TLS1.3"` — GnuTLS プライオリティ文字列 (TLS 1.3 用)
  ※ 現行の nslcd.conf.j2 テンプレートは `tls_cacertfile /etc/ssl/certs/ca-certificates.crt` を静的に出力するのみで、TLS1_2/TLS1_3 定数は現時点でテンプレートに未使用 (将来拡張用の可能性あり)。

---

## hostcfgd モジュールレベル定数 (LDAP 関連)

| 定数名 | 値 | 用途 |
|--------|----|----|
| `LDAP_CONF_TEMPLATE` | `"/usr/share/sonic/templates/ldap.conf.j2"` | `ldap.conf` 生成テンプレートパス |
| `LDAP_CONF` | `"/etc/ldap/ldap.conf"` | 出力先 `ldap.conf` パス |
| `NSLCD_CONF_TEMPLATE` | `"/usr/share/sonic/templates/nslcd.conf.j2"` | `nslcd.conf` 生成テンプレートパス |
| `NSLCD_CONF` | `"/etc/nslcd.conf"` | 出力先 `nslcd.conf` パス |
| `NSS_CONF` | `"/etc/nsswitch.conf"` | nsswitch.conf パス (ldap エントリ追加に使用) |

---

## YANG 制約定数

| 制約 | 値 | 対応 YANG 宣言 |
|------|----|----------------|
| `LDAP_SERVER_LIST` 最大エントリ数 | 8 | `max-elements 8` |
| `priority` 範囲 | 1..8 | `range "1..8"` |
| `bind_timeout` 範囲 | 1..120 秒 | `range "1..120"` |
| `version` 範囲 | 1..3 | `range "1..3"` |
| `port` 型 | `inet:port-number` (0..65535) | IETF YANG 型 |
| `timeout` 範囲 | 1..60 秒 | `range "1..60"` |
| `bind_dn` / `base_dn` / `bind_password` 長さ | 1..65 文字 | `length "1..65"` |
| `bind_password` 使用禁止文字 | SPACE / `#` / `,` | `pattern "[^ #,]*"` |

---

## nslcd.conf 静的定数 (テンプレート固定値)

`nslcd.conf.j2` が常時出力する固定値:
- `uid nslcd` / `gid nslcd` — nslcd デーモンの実行ユーザ/グループ
- `tls_cacertfile /etc/ssl/certs/ca-certificates.crt` — TLS 証明書バンドルパス
- `nss_initgroups_ignoreusers ALLLOCAL` — ローカルユーザの initgroups スキップ
- `nss_min_uid 1000` — LDAP ユーザの最小 UID 閾値 (LDAP 側でシステムアカウントが見えないようにする)
