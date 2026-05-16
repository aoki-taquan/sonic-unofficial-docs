# SNMP_AGENT_ADDRESS_CONFIG / SNMP_USER フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14
対象テーブル: CONFIG_DB `SNMP_AGENT_ADDRESS_CONFIG`, `SNMP_USER`

## 調査対象ファイル

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-snmp.yang` — YANG 定義・default 文
- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2` — テンプレート側フォールバック
- `sonic-utilities/config/main.py` — CLI 書き込み処理
- `sonic-buildimage/src/sonic-config-engine/minigraph.py` — minigraph 自動注入

---

## SNMP_AGENT_ADDRESS_CONFIG フィールド別デフォルト

### `agent_ip` (key 要素)

**コード由来デフォルト**: なし (必須引数)

CLI `config snmp agentaddress add <agentip>` で必須指定。
YANG: `type inet:ip-address` — default 文なし。

### `port` (key 要素)

**コード由来デフォルト**: YANG `pattern ''` 許容（空文字 = 未指定）。

YANG 定義:
```yang
leaf port {
  type union {
    type string { pattern ''; }     // 空文字 = デフォルトポート (161)
    type inet:port-number;
  }
}
```

- 空文字を指定した場合、snmpd.conf.j2 は `{% if port %}:{{ port }}{% endif %}` で port 部を省略し snmpd がデフォルト 161 で listen する。
- minigraph.py は `port = '161'` をハードコードして登録する（行 2314）。

```python
# minigraph.py:2314
port = '161'
snmp_key = agent_addr + '|' + port + '|'
results['SNMP_AGENT_ADDRESS_CONFIG'][snmp_key] = {}
```

**実質デフォルト**: `'161'`（minigraph 経由）。空文字指定時 snmpd は 161 を使用。

### `vrf_name` (key 要素)

**コード由来デフォルト**: YANG `pattern ''` 許容（空文字 = default VRF）。

YANG 定義:
```yang
leaf vrf_name {
  type union {
    type string { pattern ''; }         // 空文字 = default VRF
    type string { pattern 'mgmt'; }
    type string { pattern "Vrf[a-zA-Z0-9_-]+"; }
  }
}
```

- minigraph.py は `snmp_key = agent_addr + '|' + port + '|'` — vrf 部は空文字でキーを作成。
- snmpd.conf.j2: `{% if vrf %}@{{ vrf }}{% endif %}` → 空文字なら VRF サフィックスなし。

**実質デフォルト**: `''`（空文字 = default VRF）。minigraph も空文字で登録。

### テーブルなし時のフォールバック

snmpd.conf.j2:
```jinja
{% if SNMP_AGENT_ADDRESS_CONFIG %}
...
{% else %}
agentAddress udp:161
agentAddress udp6:161
{% endif %}
```

テーブルにエントリが 1 件もない場合、snmpd は全インタフェース・ポート 161 で listen。

---

## SNMP_USER フィールド別デフォルト

### `SNMP_USER_TYPE` (必須)

**コード由来デフォルト**: なし (mandatory true)

YANG: `mandatory true; type enumeration { enum noAuthNoPriv; enum AuthNoPriv; enum Priv; }`

CLI でも必須引数 `<noAuthNoPriv|AuthNoPriv|Priv>` として指定必須。
DB への書き込み時に正規化: `is_valid_user_type()` が入力を小文字に変換し `noAuthNoPriv` / `AuthNoPriv` / `Priv` の正規ケースにマッピング（config/main.py:4284）。

```python
# config/main.py:4284
convert_user_type = {'noauthnopriv': 'noAuthNoPriv', 'authnopriv': 'AuthNoPriv', 'priv': 'Priv'}
```

### `SNMP_USER_PERMISSION` (必須)

**コード由来デフォルト**: なし (mandatory true)

YANG: `mandatory true; type enumeration { enum RO; enum RW; }`

CLI: `<RO|RW>` 必須引数。`user_permission_type.upper()` で大文字正規化。

### `SNMP_USER_AUTH_TYPE`

**コード由来デフォルト**: `""` (空文字)

YANG:
```yang
leaf SNMP_USER_AUTH_TYPE {
  type string;
  default "";
  ...
}
```

- `SNMP_USER_TYPE = 'noAuthNoPriv'` の場合: 空文字必須。CLI が auth_type を拒否。
- `SNMP_USER_TYPE = 'AuthNoPriv'` / `'Priv'` の場合: `MD5`, `SHA`, `HMAC-SHA-2` のいずれかが必須。
- CLI が `None` の場合 `user_auth_type = ''` にフォールバック（config/main.py:4771-4772）。

```python
# config/main.py:4771-4772
if not user_auth_type:
    user_auth_type = ''
```

snmpd.conf.j2 では auth_type が空文字の場合 `CreateUser <user>  <password>` 形式で渡される（YANG default `""` がそのまま展開）。

### `SNMP_USER_AUTH_PASSWORD`

**コード由来デフォルト**: `""` (空文字)

YANG:
```yang
leaf SNMP_USER_AUTH_PASSWORD {
  type string { length "0..64"; pattern '[^ @:]*'; }
  must "(AuthNoPriv and len >= 8) or (Priv and len >= 8) or (noAuthNoPriv and current() = '')";
}
```

- YANG に explicit default 文なし。noAuthNoPriv の場合は空文字が MUST 制約で強制。
- CLI: `if not user_auth_password: user_auth_password = ''`（config/main.py:4773-4774）。
- パスワード長: 8〜64 文字（AuthNoPriv / Priv）。

### `SNMP_USER_ENCRYPTION_TYPE`

**コード由来デフォルト**: `""` (空文字)

YANG:
```yang
leaf SNMP_USER_ENCRYPTION_TYPE {
  type string;
  default "";
  ...
}
```

- `Priv` の場合のみ `DES` または `AES` が必須。その他は空文字。
- CLI: `if not user_encrypt_type: user_encrypt_type = ''`（config/main.py:4775-4776）。

### `SNMP_USER_ENCRYPTION_PASSWORD`

**コード由来デフォルト**: `""` (空文字、mandatory true)

YANG:
```yang
leaf SNMP_USER_ENCRYPTION_PASSWORD {
  mandatory true;
  type string { length "0..64"; pattern '[^ @:]*'; }
  must "(noAuthNoPriv and current() = '') or (AuthNoPriv and current() = '') or (Priv and len >= 8)";
}
```

- `mandatory true` だが `length "0.."` で空文字を許容。
- noAuthNoPriv / AuthNoPriv の場合は空文字が MUST で強制。Priv の場合は 8 文字以上。
- CLI: `if not user_encrypt_password: user_encrypt_password = ''`（config/main.py:4777-4778）。

---

## snmpd.conf.j2 テンプレート挙動（SNMP_USER 空フィールド）

```jinja
CreateUser {{ user }} {{ SNMP_USER[user]['SNMP_USER_AUTH_TYPE'] }} {{ SNMP_USER[user]['SNMP_USER_AUTH_PASSWORD'] }} {{ SNMP_USER[user]['SNMP_USER_ENCRYPTION_TYPE'] }} {{ SNMP_USER[user]['SNMP_USER_ENCRYPTION_PASSWORD'] }}
```

フィールドが空文字 `""` の場合、テンプレートは空文字をそのまま展開する。
例: `noAuthNoPriv` ユーザの場合 → `CreateUser alice  ` （空フィールドがスペースで区切られる）。

---

## 要約表

### SNMP_AGENT_ADDRESS_CONFIG

| フィールド | YANG default | コード由来デフォルト | 備考 |
|-----------|-------------|-------------------|------|
| `agent_ip` | なし | 必須 | CLI 必須引数 |
| `port` | `pattern ''` 許容 | `'161'`（minigraph ハードコード） | 空文字 → snmpd デフォルト 161 |
| `vrf_name` | `pattern ''` 許容 | `''`（空文字 = default VRF） | minigraph も空文字登録 |

### SNMP_USER

| フィールド | YANG default | コード由来デフォルト | 条件 |
|-----------|-------------|-------------------|------|
| `SNMP_USER_TYPE` | なし (mandatory) | 必須 | noAuthNoPriv / AuthNoPriv / Priv |
| `SNMP_USER_PERMISSION` | なし (mandatory) | 必須 | RO / RW |
| `SNMP_USER_AUTH_TYPE` | `""` | `""` (CLI フォールバック) | noAuthNoPriv: 必ず空 |
| `SNMP_USER_AUTH_PASSWORD` | なし | `""` (CLI フォールバック) | noAuthNoPriv: 必ず空; 認証あり: 8〜64 chars |
| `SNMP_USER_ENCRYPTION_TYPE` | `""` | `""` (CLI フォールバック) | Priv 以外: 必ず空; Priv: DES / AES |
| `SNMP_USER_ENCRYPTION_PASSWORD` | なし (mandatory) | `""` (CLI フォールバック) | Priv のみ: 8〜64 chars |

---

## 証拠リンク

- `sonic-snmp.yang` — YANG default/mandatory 定義
  <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-snmp.yang>
- `config/main.py:4283-4306` — `is_valid_user_type()`, `is_valid_auth_type()`, `is_valid_encrypt_type()`
- `config/main.py:4708-4784` — `add_user()` CLI コマンド
- `config/main.py:4137-4186` — `add_snmp_agent_address()` CLI コマンド
- `minigraph.py:2310-2324` — SNMP_AGENT_ADDRESS_CONFIG 自動生成
- `snmpd.conf.j2:27-34` — agentAddress テンプレートフォールバック
- `snmpd.conf.j2:66-77` — SNMP_USER テンプレート展開
