---
title: SNMP_AGENT_ADDRESS_CONFIG / SNMP_USER テーブル (デフォルト詳細)
description: "SNMP_AGENT_ADDRESS_CONFIG と SNMP_USER テーブルのフィールド暗黙デフォルト — YANG default 文・CLI フォールバック・minigraph 注入・snmpd.conf.j2 テンプレート挙動をコード証拠付きで解説。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-snmp.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: dockers/docker-snmp/snmpd.conf.j2
    ref: master
  - repo: sonic-net/sonic-utilities
    path: config/main.py
    ref: master
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-config-engine/minigraph.py
    ref: master
related:
  config_db:
    - SNMP_AGENT_ADDRESS_CONFIG
    - SNMP_USER
    - SNMP
    - SNMP_COMMUNITY
  cli:
    - config snmp agentaddress
    - config snmp user
  yang:
    - sonic-snmp
---

# SNMP_AGENT_ADDRESS_CONFIG / SNMP_USER テーブル (デフォルト詳細)

## 概要

[SNMP](../../reference/glossary.md#term-snmp) 関連の 2 テーブルのフィールド暗黙デフォルトをコード証拠付きで解説する。

- **`SNMP_AGENT_ADDRESS_CONFIG`**: `snmpd` のリッスンアドレス / ポート / [VRF](../../reference/glossary.md#term-vrf) 設定。key 要素に `port` と `vrf_name` の暗黙デフォルトあり。
- **`SNMP_USER`**: SNMPv3 ユーザ設定。auth / encrypt フィールドが `SNMP_USER_TYPE` 値に連動する暗黙デフォルト（空文字フォールバック）を持つ。

<!-- defaults -->
## フィールド暗黙デフォルト

### SNMP_AGENT_ADDRESS_CONFIG

key は `<agent_ip>|<port>|<vrf_name>` の 3 要素複合。`port` / `vrf_name` は空文字を許容する。

#### `port`

**YANG default**: explicit default 文なし。`type union` で空文字パターン (`pattern ''`) を許容。[^2]

**コード由来デフォルト (minigraph)**: `'161'`

```python
# sonic-buildimage/src/sonic-config-engine/minigraph.py:2314
port = '161'
snmp_key = agent_addr + '|' + port + '|'
results['SNMP_AGENT_ADDRESS_CONFIG'][snmp_key] = {}
```

minigraph 経由（`sonic-cfggen` が minigraph.xml を読み込んで生成する初期設定）では `port` を `'161'` でハードコードして key を構築する。[^5] CLI (`config snmp agentaddress add`) では `-p` オプション省略時に port 部が空文字 `''` となり、`snmpd.conf.j2` の `{% if port %}:{{ port }}{% endif %}` で port サフィックスが省略 → snmpd はデフォルトポート 161 で listen する。[^1]

| port 値 | snmpd.conf への展開 |
|---------|-------------------|
| `'161'` | `agentAddress udp:[<ip>]:161` |
| `''` (空文字) | `agentAddress udp:[<ip>]` (snmpd はデフォルト 161 を使用) |

#### `vrf_name`

**YANG default**: explicit default 文なし。`type union` で空文字・`'mgmt'`・`Vrf<name>` パターンを許容。[^2]

**コード由来デフォルト (minigraph)**: `''` (空文字 = default VRF)

minigraph.py は `snmp_key = agent_addr + '|' + port + '|'` — vrf_name 部に空文字を使いキーを構築する。[^5] CLI の `-v` オプションを省略した場合も空文字がキーに入る。

`snmpd.conf.j2` では `{% if vrf %}@{{ vrf }}{% endif %}` で空文字なら VRF サフィックスなし（default VRF でリッスン）。[^1]

| vrf_name 値 | snmpd.conf への展開 |
|------------|-------------------|
| `''` (空文字) | VRF サフィックスなし → default VRF |
| `'mgmt'` | `agentAddress udp:[<ip>]@mgmt` |
| `'Vrf<name>'` | `agentAddress udp:[<ip>]@Vrf<name>` |

#### テーブルが空の場合のフォールバック

```jinja
{# snmpd.conf.j2:31-34 #}
{% else %}
agentAddress udp:161
agentAddress udp6:161
{% endif %}
```

テーブルにエントリが 1 件もない場合、snmpd は全インタフェース・IPv4/IPv6 ともにポート 161 で listen する。[^1]

---

### SNMP_USER

#### `SNMP_USER_TYPE` (mandatory)

**YANG**: `mandatory true; type enumeration { enum noAuthNoPriv; enum AuthNoPriv; enum Priv; }`[^2]

デフォルトなし。CLI は必須引数として大文字・小文字を正規化して登録する。

```python
# config/main.py:4284
convert_user_type = {'noauthnopriv': 'noAuthNoPriv', 'authnopriv': 'AuthNoPriv', 'priv': 'Priv'}
```

#### `SNMP_USER_PERMISSION` (mandatory)

**YANG**: `mandatory true; type enumeration { enum RO; enum RW; }`[^2]

デフォルトなし。CLI が `upper()` で大文字正規化して DB に書く。

#### `SNMP_USER_AUTH_TYPE`

**YANG default**: `""` (空文字)[^2]

```yang
leaf SNMP_USER_AUTH_TYPE {
  type string;
  default "";
  must "(noAuthNoPriv and current() = '') or
        ((AuthNoPriv or Priv) and (current() = 'SHA' or current() = 'MD5' or current() = 'HMAC-SHA-2'))";
}
```

CLI フォールバック:
```python
# config/main.py:4771-4772
if not user_auth_type:
    user_auth_type = ''
```

| SNMP_USER_TYPE | SNMP_USER_AUTH_TYPE |
|---------------|-------------------|
| `noAuthNoPriv` | `""` (必須) |
| `AuthNoPriv` | `MD5` / `SHA` / `HMAC-SHA-2` のいずれか (必須) |
| `Priv` | `MD5` / `SHA` / `HMAC-SHA-2` のいずれか (必須) |

#### `SNMP_USER_AUTH_PASSWORD`

**YANG default**: explicit default 文なし。`must` 制約で `noAuthNoPriv` の場合は空文字を強制。[^2]

```yang
leaf SNMP_USER_AUTH_PASSWORD {
  type string { length "0..64"; pattern '[^ @:]*'; }
  must "(AuthNoPriv and len >= 8) or (Priv and len >= 8) or (noAuthNoPriv and current() = '')";
}
```

CLI フォールバック: `if not user_auth_password: user_auth_password = ''`（config/main.py:4773-4774）。[^4]

| SNMP_USER_TYPE | 有効な SNMP_USER_AUTH_PASSWORD |
|---------------|-------------------------------|
| `noAuthNoPriv` | `""` (必須) |
| `AuthNoPriv` | 8〜64 文字、`@` `:` ` ` 禁止 |
| `Priv` | 8〜64 文字、`@` `:` ` ` 禁止 |

#### `SNMP_USER_ENCRYPTION_TYPE`

**YANG default**: `""` (空文字)[^2]

```yang
leaf SNMP_USER_ENCRYPTION_TYPE {
  type string;
  default "";
  must "(noAuthNoPriv and current() = '') or
        (AuthNoPriv and current() = '') or
        (Priv and (current() = 'DES' or current() = 'AES'))";
}
```

CLI フォールバック: `if not user_encrypt_type: user_encrypt_type = ''`（config/main.py:4775-4776）。[^4]

| SNMP_USER_TYPE | SNMP_USER_ENCRYPTION_TYPE |
|---------------|--------------------------|
| `noAuthNoPriv` | `""` (必須) |
| `AuthNoPriv` | `""` (必須) |
| `Priv` | `DES` または `AES` (必須) |

#### `SNMP_USER_ENCRYPTION_PASSWORD` (mandatory)

**YANG**: `mandatory true; type string { length "0..64"; }; must (noAuthNoPriv and empty) or (AuthNoPriv and empty) or (Priv and len >= 8)`[^2]

`mandatory true` だが `length "0.."` で空文字を許容。noAuthNoPriv / AuthNoPriv では空文字が MUST 制約で強制される。

CLI フォールバック: `if not user_encrypt_password: user_encrypt_password = ''`（config/main.py:4777-4778）。[^4]

| SNMP_USER_TYPE | SNMP_USER_ENCRYPTION_PASSWORD |
|---------------|------------------------------|
| `noAuthNoPriv` | `""` (必須) |
| `AuthNoPriv` | `""` (必須) |
| `Priv` | 8〜64 文字、`@` `:` ` ` 禁止 |

#### snmpd.conf.j2 での空フィールド展開

```jinja
{# snmpd.conf.j2:70 #}
CreateUser {{ user }} {{ SNMP_USER[user]['SNMP_USER_AUTH_TYPE'] }} {{ SNMP_USER[user]['SNMP_USER_AUTH_PASSWORD'] }} {{ SNMP_USER[user]['SNMP_USER_ENCRYPTION_TYPE'] }} {{ SNMP_USER[user]['SNMP_USER_ENCRYPTION_PASSWORD'] }}
```

フィールドが空文字の場合、テンプレートは空文字をそのまま展開する（スペース区切りで空フィールドが含まれる）。`noAuthNoPriv` ユーザでは `CreateUser alice   ` のような行が生成される。[^1]

---

## 要約表

### SNMP_AGENT_ADDRESS_CONFIG

| フィールド | YANG default | コード由来デフォルト | 備考 |
|-----------|-------------|-------------------|------|
| `agent_ip` | なし | 必須 | CLI 必須引数 |
| `port` | (explicit default 文なし) | `'161'` (minigraph) / `''` (CLI 省略時) | 空文字 → snmpd デフォルト 161 |
| `vrf_name` | (explicit default 文なし) | `''` (空文字 = default VRF) | minigraph・CLI 省略時ともに空文字 |

### SNMP_USER

| フィールド | YANG default | コード由来デフォルト | 条件 |
|-----------|-------------|-------------------|------|
| `SNMP_USER_TYPE` | なし (mandatory) | 必須 | noAuthNoPriv / AuthNoPriv / Priv |
| `SNMP_USER_PERMISSION` | なし (mandatory) | 必須 | RO / RW |
| `SNMP_USER_AUTH_TYPE` | `""` | `""` (CLI フォールバック) | noAuthNoPriv: 必ず空 |
| `SNMP_USER_AUTH_PASSWORD` | (なし) | `""` (CLI フォールバック) | noAuthNoPriv: 必ず空; 認証あり: 8〜64 chars |
| `SNMP_USER_ENCRYPTION_TYPE` | `""` | `""` (CLI フォールバック) | Priv 以外: 必ず空; Priv: DES / AES |
| `SNMP_USER_ENCRYPTION_PASSWORD` | なし (mandatory) | `""` (CLI フォールバック) | Priv のみ: 8〜64 chars |

---

## 関連リファレンス

- [CONFIG_DB: SNMP_AGENT_ADDRESS_CONFIG](snmp-agent-address-config.md)
- [CONFIG_DB: SNMP](snmp.md)
- [YANG: sonic-snmp](../yang/sonic-snmp.md)
- CLI: [`config snmp agentaddress`](../cli/config-snmp.md)

## 引用元

[^1]: `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2` — agentAddress テンプレートフォールバック (行 27-34) / SNMP_USER CreateUser テンプレート (行 66-77). <https://github.com/sonic-net/sonic-buildimage/blob/master/dockers/docker-snmp/snmpd.conf.j2>

[^2]: `src/sonic-yang-models/yang-models/sonic-snmp.yang` — SNMP_USER / SNMP_AGENT_ADDRESS_CONFIG YANG 定義. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-snmp.yang>

[^3]: `sonic-utilities/config/main.py:4137-4186` — `add_snmp_agent_address()`. <https://github.com/sonic-net/sonic-utilities/blob/master/config/main.py>

[^4]: `sonic-utilities/config/main.py:4708-4784` — `add_user()`. <https://github.com/sonic-net/sonic-utilities/blob/master/config/main.py>

[^5]: `sonic-buildimage/src/sonic-config-engine/minigraph.py:2310-2324` — SNMP_AGENT_ADDRESS_CONFIG 自動生成. <https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-config-engine/minigraph.py>
