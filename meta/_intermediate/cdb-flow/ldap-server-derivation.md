# ldap-server — Phase 6/7 derivation intermediate

## 調査対象

- `sonic-host-services/scripts/hostcfgd` (AaaCfg クラス)
- `sonic-host-services/scripts/ldap.py` (LdapCfg クラス)

## Phase 6: 自動派生

hostcfgd は `LDAP_SERVER` テーブルを `ldap_server_update()` で受信後、`modify_conf_file()` 内で以下の自動補完を行う。

### ldap_global_default の初期化

`AaaCfg.__init__()` で `self.ldap_global_default = {}` と空 dict を初期化する。TACACS+ / RADIUS と異なり、LDAP は hostcfgd レイヤでのデフォルト注入を行わない (`hostcfgd:386`)。

### LdapCfg クラス属性による fallback

`modify_conf_file()` は Jinja2 テンプレートに `ldap_cfg=ldap.LdapCfg` を渡す。テンプレート内で `ldap_cfg.BASE`, `ldap_cfg.PORT`, `ldap_cfg.VERSION` 等を参照することで、CONFIG_DB に値が存在しない場合の fallback を提供する (`hostcfgd:855, 863`)。

| フィールド | LdapCfg 定数 | fallback 値 | コード場所 |
|-----------|------------|------------|----------|
| `base_dn` | `LdapCfg.BASE` | `'ou=users,dc=example,dc=com'` | `ldap.py:9` |
| `bind_dn` | `LdapCfg.BIND` | `''` (空文字) | `ldap.py:10` |
| `bind_password` | `LdapCfg.BINDPW` | `""` (空文字) | `ldap.py:11` |
| `version` | `LdapCfg.VERSION` | `'3'` | `ldap.py:12` |
| `timeout` (search) | `LdapCfg.TIMEOUT_SEARCH` | `5` | `ldap.py:13` |
| `bind_timeout` | `LdapCfg.TIMEOUT_BIND` | `5` | `ldap.py:14` |
| `port` | `LdapCfg.PORT` | `389` | `ldap.py:15` |
| `scope` | `LdapCfg.SCOPE` | `"sub"` | `ldap.py:16` |

### priority による降順ソート

`ldapsrvs_conf = sorted(ldapsrvs_conf, key=lambda t: int(t['priority']), reverse=True)` でサーバリストを priority 降順にソートして nslcd.conf / ldap.conf に反映する (`hostcfgd:713`)。これは YANG default `priority=1` に依存する派生処理。

### global → per-server マージ

`ldap_global = self.ldap_global_default.copy()` → `ldap_global.update(self.ldap_global)` の後、各サーバエントリで `server = ldap_global.copy(); server.update(self.ldap_servers[addr])` とマージする (`hostcfgd:650-651, 708-711`)。per-server 設定が global 設定を上書きする標準継承パターン。

## Phase 7: 条件付き登録 (add_manager 条件)

hostcfgd は起動時から `LDAP` / `LDAP_SERVER` テーブルを常時購読する (`hostcfgd:2475-2476`)。

ただし以下の条件がすべて満たされないと nslcd は起動しない (`is_ldap_config_complete()` at `hostcfgd:437-442`):

1. `LDAP|global.bind_dn` が空でない
2. `LDAP|global.base_dn` が空でない
3. `LDAP|global.bind_password` が空でない
4. `AAA|authentication.login` に `ldap` が含まれる
5. `LDAP_SERVER` にエントリが 1 件以上存在する

条件未達の場合 `handle_nslcd_service(False)` が呼ばれ nslcd を停止・mask する。条件が揃うと `handle_nslcd_service(True)` で nslcd を再起動する。
