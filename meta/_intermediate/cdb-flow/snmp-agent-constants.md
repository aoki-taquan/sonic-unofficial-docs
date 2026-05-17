# SNMP_AGENT_ADDRESS_CONFIG / SNMP_USER — Phase E ハードコード定数調査

対象テーブル: `SNMP_AGENT_ADDRESS_CONFIG`, `SNMP_USER`
調査日: 2026-05-17
調査ファイル:
- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2`
- `sonic-utilities/config/main.py` (is_valid_auth_type, is_valid_encrypt_type, snmp_username_check, snmp_user_secret_check)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-snmp.yang`

---

## SNMP_AGENT_ADDRESS_CONFIG の定数

### agentAddress フォールバック (snmpd.conf.j2)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| フォールバック agentAddress (IPv4) | `udp:161` | `SNMP_AGENT_ADDRESS_CONFIG` テーブルが空の場合に全インターフェース公開 | `snmpd.conf.j2` L32 |
| フォールバック agentAddress (IPv6) | `udp6:161` | 同上、IPv6 | `snmpd.conf.j2` L33 |
| デフォルト listen ポート (minigraph) | `161` | minigraph 自動生成時に key の port 部にハードコード | `minigraph.py:2314` |

CONFIG_DB の `SNMP_AGENT_ADDRESS_CONFIG` で管理されないハードコード値。エントリが 0 件の場合に使用されるため、明示的に制限したい場合はエントリを 1 件以上登録する必要がある。

---

## SNMP_USER の定数

### 認証タイプの許容値 (CLI 検証)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| 有効な `SNMP_USER_AUTH_TYPE` | `['MD5', 'SHA', 'HMAC-SHA-2']` | CLI `is_valid_auth_type()` でのホワイトリスト | `config/main.py:4294` |
| 有効な `SNMP_USER_ENCRYPTION_TYPE` | `['DES', 'AES']` | CLI `is_valid_encrypt_type()` でのホワイトリスト | `config/main.py:4302` |

YANG の `SNMP_USER_AUTH_TYPE` は `type string` で制約が緩いが、CLI が Python レベルで `MD5`/`SHA`/`HMAC-SHA-2` の 3 値のみに制限する。`sonic-db-cli` で直接書き込む場合は YANG `must` 制約のみが適用される。

### パスワード長・文字種制約 (CLI 検証)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| パスワード最小長 | `8` 文字 | `SNMP_USER_AUTH_PASSWORD` / `SNMP_USER_ENCRYPTION_PASSWORD` の最小長 | `config/main.py:4347` |
| パスワード最大長 | `64` 文字 | 同上の最大長 | `config/main.py:4354` |
| ユーザ名最大長 | `32` 文字 | `SNMP_USER` のユーザ名（キー）の最大長 | `config/main.py:4329` |
| 禁止文字 (パスワード/ユーザ名) | `['@', ':']` | CLI レベルの禁止文字リスト | `config/main.py:4346,4328` |

YANG の `SNMP_USER_AUTH_PASSWORD` / `SNMP_USER_ENCRYPTION_PASSWORD` は `type string { length "0..64"; pattern '[^ @:]*'; }` で制約を持つが、最小長 8 文字は YANG `must` で保証する（AuthNoPriv/Priv 時のみ）。CLI は事前に Python で同等のチェックを実行する。

### SNMP_USER タイプ正規化 (CLI)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| ユーザタイプ正規化マップ | `{'noauthnopriv': 'noAuthNoPriv', 'authnopriv': 'AuthNoPriv', 'priv': 'Priv'}` | CLI 入力の大文字小文字を正規化して CONFIG_DB に書き込む | `config/main.py:4284` |
| 権限タイプ正規化 | `upper()` による大文字変換 | `SNMP_USER_PERMISSION` を `RO`/`RW` に正規化 | `config/main.py:4727` |

---

## サマリ表

### SNMP_AGENT_ADDRESS_CONFIG

| 定数 | 値 | CONFIG_DB で変更可能 | ソース |
|------|----|---------------------|--------|
| フォールバック agentAddress (IPv4) | `udp:161` | 不可（テーブル空時のみ使用） | `snmpd.conf.j2` L32 |
| フォールバック agentAddress (IPv6) | `udp6:161` | 不可 | `snmpd.conf.j2` L33 |
| minigraph デフォルト port | `'161'` | 不可（minigraph 経路でハードコード） | `minigraph.py:2314` |

### SNMP_USER

| 定数 | 値 | CONFIG_DB で変更可能 | ソース |
|------|----|---------------------|--------|
| 有効 AUTH_TYPE | `MD5`, `SHA`, `HMAC-SHA-2` | 不可（CLI/YANG ハードコード） | `config/main.py:4294` |
| 有効 ENCRYPTION_TYPE | `DES`, `AES` | 不可（CLI/YANG ハードコード） | `config/main.py:4302` |
| パスワード最小長 | `8` 文字 | 不可（CLI/YANG `must`) | `config/main.py:4347` |
| パスワード最大長 | `64` 文字 | 不可（YANG `length`) | `config/main.py:4354`, `sonic-snmp.yang` |
| ユーザ名最大長 | `32` 文字 | 不可（CLI) | `config/main.py:4329` |
| 禁止文字 | `@`, `:` | 不可（CLI/YANG `pattern`) | `config/main.py:4328,4346` |
