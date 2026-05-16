# LDAP_SERVER / LDAP フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14  
対象テーブル: CONFIG_DB `LDAP_SERVER`, `LDAP`

## 調査対象ファイル

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-system-ldap.yang` (YANG スキーマ default 宣言)
- `sonic-host-services/scripts/ldap.py` (LdapCfg クラス — nslcd テンプレート描画時の fallback)
- `sonic-host-services/scripts/hostcfgd` (AaaCfg クラス — ldap_global_default, ldap_server_update)
- `sonic-host-services/data/templates/nslcd.conf.j2` (Jinja2 テンプレート)
- `sonic-utilities/config/plugins/sonic-system-ldap_yang.py` (CLI プラグイン)

---

## フィールド別 暗黙デフォルト

### `priority`（LDAP_SERVER エントリ）

**YANG default**: `1`

```yang
# sonic-system-ldap.yang:31-32
leaf priority {
    default 1;
    type uint8 { range "1..8"; }
}
```

CLI (`LDAP_SERVER add`) で `--priority` を省略した場合は data dict に `priority` キーが含まれない。  
その場合 YANG エンジンが `default 1` を適用する。  
`hostcfgd` の `ldap_server_update()` (hostcfgd:555-564) は DB から読み込んだ dict をそのまま `self.ldap_servers[key]` に格納する。  
`modify_conf_file()` (hostcfgd:706-713) で `ldapsrvs_conf` を `priority` でソート:
```python
ldapsrvs_conf = sorted(ldapsrvs_conf, key=lambda t: int(t['priority']), reverse=True)
```
→ `priority` キーが無い場合は `KeyError` になるため、実質 YANG default `1` が DB に書かれていることが前提。

---

### `bind_timeout`（LDAP|global）

**YANG default**: `5`（秒）

```yang
# sonic-system-ldap.yang:66-73
leaf bind_timeout {
    default 5;
    type uint16 { range "1..120"; }
}
```

**LdapCfg fallback** (ldap.py:15): `TIMEOUT_BIND = 5`

```python
# ldap.py:79-80
@staticmethod
def cfg_bind_timeout(_ldapsrvs_conf):
    return LdapCfg._do_cfg(_ldapsrvs_conf, LdapCfg.TIMEOUT_BIND, 'bind_timeout')
```

`_do_cfg` は `_ldapsrvs_conf[0].get('bind_timeout', TIMEOUT_BIND)` を返す。  
DB に値が存在しない場合、LdapCfg.TIMEOUT_BIND = `5` がフォールバックとして nslcd.conf の `bind_timelimit` に書かれる。  
YANG default と LdapCfg fallback が同値（`5`）で一致。

---

### `version`（LDAP|global）

**YANG default**: `3`

```yang
# sonic-system-ldap.yang:76-83
leaf version {
    default 3;
    type uint16 { range "1..3"; }
}
```

**LdapCfg fallback** (ldap.py:12): `VERSION = '3'`

```python
# ldap.py:63-64
@staticmethod
def cfg_version(_ldapsrvs_conf):
    return LdapCfg._do_cfg(_ldapsrvs_conf, LdapCfg.VERSION, 'version')
```

YANG default と LdapCfg fallback が同値（`3`）で一致。nslcd.conf の `ldap_version 3` として反映。

---

### `port`（LDAP|global）

**YANG default**: `389`

```yang
# sonic-system-ldap.yang:93-96
leaf port {
    type inet:port-number;
    default 389;
}
```

**LdapCfg fallback** (ldap.py:15): `PORT = 389`

```python
# ldap.py:44
port = LdapCfg._do_cfg(_ldapsrvs_conf, LdapCfg.PORT, 'port')
```

`cfg_servers()` でポートを URI に埋め込む (`ldap://ip:389/`)。YANG default と LdapCfg fallback が同値（`389`）で一致。

---

### `timeout`（LDAP|global）

**YANG default**: なし（YANG に `default` 宣言なし）

```yang
# sonic-system-ldap.yang:99-106
leaf timeout {
    type uint16 { range "1..60"; }
}
```

**LdapCfg fallback** (ldap.py:13): `TIMEOUT_SEARCH = 5`

```python
# ldap.py:75-76
@staticmethod
def cfg_timeout(_ldapsrvs_conf):
    return LdapCfg._do_cfg(_ldapsrvs_conf, LdapCfg.TIMEOUT_SEARCH, 'search_timeout')
```

注意: YANG フィールド名は `timeout`、LdapCfg では `search_timeout` を参照している。  
YANG schema の `timeout` は `search_timeout` として hostcfgd に渡されていない可能性があり、フィールド名の不一致が存在する。  
DB に `timeout` が設定されていても `cfg_timeout()` は `search_timeout` キーで引くため、nslcd.conf の `timelimit` に反映されない疑いがある（要実装確認）。  
DB に `search_timeout` も `timeout` も存在しない場合、LdapCfg.TIMEOUT_SEARCH = `5` がフォールバック。

---

### `bind_dn`（LDAP|global）

**YANG default**: なし

**LdapCfg fallback** (ldap.py:10): `BIND = ''`

```python
# ldap.py:31-32
@staticmethod
def cfg_bind(_ldapsrvs_conf):
    return LdapCfg._do_cfg(_ldapsrvs_conf, LdapCfg.BIND, 'bind_dn')
```

DB に `bind_dn` が存在しない場合、nslcd.conf に `binddn ` (空文字) として出力される。

---

### `bind_password`（LDAP|global）

**YANG default**: なし

**LdapCfg fallback** (ldap.py:11): `BINDPW = ""`

```python
# ldap.py:35-36
@staticmethod
def cfg_bindpw(_ldapsrvs_conf):
    return LdapCfg._do_cfg(_ldapsrvs_conf, LdapCfg.BINDPW, 'bind_password')
```

DB に `bind_password` が存在しない場合、nslcd.conf に `bindpw ` (空文字) として出力される。

---

### `base_dn`（LDAP|global）

**YANG default**: なし

**LdapCfg fallback** (ldap.py:9): `BASE = 'ou=users,dc=example,dc=com'`

```python
# ldap.py:27-28
@staticmethod
def cfg_base(_ldapsrvs_conf):
    return LdapCfg._do_cfg(_ldapsrvs_conf, LdapCfg.BASE, 'base_dn')
```

DB に `base_dn` が存在しない場合、nslcd.conf に `base ou=users,dc=example,dc=com` が書かれる。  
ただし `is_ldap_config_complete()` (hostcfgd:440) で `base_dn` が空文字か未設定の場合 nslcd が起動されないため、このフォールバックが実際に使われることはない。

---

### `scope`（LDAP|global — YANG にフィールドなし）

**YANG**: `scope` フィールドは YANG スキーマに存在しない  
**LdapCfg fallback** (ldap.py:16): `SCOPE = "sub"`

nslcd.conf テンプレートは `scope {{ ldap_cfg.cfg_scope(servers) }}` を使用しており、  
`cfg_scope()` は `_ldapsrvs_conf[0].get('scope', LdapCfg.SCOPE)` を返す。  
`scope` は CONFIG_DB から設定できないが、nslcd.conf 生成時は常に `sub` が使われる。

---

## ldap_global_default の役割

```python
# hostcfgd:386
self.ldap_global_default = {}
```

`ldap_global_default` は空 dict。  
TACACS/RADIUS と異なり LDAP は hostcfgd レベルの追加デフォルト注入を一切行わない。  
すべての値は YANG schema の `default` 宣言、または LdapCfg クラスの class attribute による nslcd テンプレート描画時の fallback のみで決まる。

---

## 要約表

| フィールド | テーブル | YANG default | LdapCfg fallback | 備考 |
|-----------|---------|-------------|-----------------|------|
| `priority` | LDAP_SERVER | **1** | — | YANG default がソート処理前提 |
| `bind_timeout` | LDAP\|global | **5** | `TIMEOUT_BIND = 5` | 一致 |
| `version` | LDAP\|global | **3** | `VERSION = '3'` | 一致 |
| `port` | LDAP\|global | **389** | `PORT = 389` | 一致 |
| `timeout` | LDAP\|global | なし | `TIMEOUT_SEARCH = 5` | フィールド名 `search_timeout` 不一致の疑い |
| `bind_dn` | LDAP\|global | なし | `BIND = ''` | 空文字フォールバック |
| `bind_password` | LDAP\|global | なし | `BINDPW = ""` | 空文字フォールバック |
| `base_dn` | LDAP\|global | なし | `BASE = 'ou=users,dc=example,dc=com'` | 実使用なし (`is_ldap_config_complete` ガード) |
| `scope` | — | (YANG にフィールドなし) | `SCOPE = "sub"` | CONFIG_DB から設定不可 |

---

## 証拠リンク

- `sonic-system-ldap.yang:31-32` — `priority` YANG default 1
- `sonic-system-ldap.yang:66-67` — `bind_timeout` YANG default 5
- `sonic-system-ldap.yang:76-77` — `version` YANG default 3
- `sonic-system-ldap.yang:93-95` — `port` YANG default 389
- `ldap.py:9-17` — LdapCfg クラス attribute 定義 (BASE, BIND, BINDPW, VERSION, TIMEOUT_SEARCH, TIMEOUT_BIND, PORT, SCOPE)
- `ldap.py:21-80` — cfg_* 静的メソッド群 (_do_cfg フォールバックロジック)
- `hostcfgd:386` — `ldap_global_default = {}` (追加デフォルト注入なし)
- `hostcfgd:437-441` — `is_ldap_config_complete()` (bind_dn/base_dn/bind_password 必須ガード)
- `hostcfgd:706-713` — `ldapsrvs_conf` priority ソート
- `nslcd.conf.j2:17,34,36` — `ldap_version`, `timelimit`, `bind_timelimit` テンプレート行
