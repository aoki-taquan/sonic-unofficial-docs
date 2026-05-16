# LDAP_SERVER — Phase C: 暗黙参照テーブル分析 (cross-refs)

対象ドキュメント: `docs/reference/config-db/ldap-server.md`
解析日: 2026-05-16
根拠ソース:
- `sonic-host-services/scripts/hostcfgd` (L241-251, L396-442, L547-580, L642-863, L1422-1525, L2184-2476)
- `sonic-host-services/data/templates/nslcd.conf.j2`
- `sonic-host-services/data/templates/ldap.conf.j2`

---

## 目的

`LDAP_SERVER` テーブルエントリが CONFIG_DB に存在するとき、`hostcfgd` の `AaaCfg` クラスおよびテンプレートが **暗黙的に** 参照・依存する他テーブルを網羅する。
YANG leafref に明示されない「実装上の暗黙前提」を列挙し、`<!-- cross-refs -->` ブロックに変換する。

---

## 1. AAA|authentication — LDAP 有効化の必須条件

### 参照箇所

`hostcfgd:437-442` `is_ldap_config_complete()`:

```python
def is_ldap_config_complete(self):
    if self.ldap_global == {}:
        return False
    return self.ldap_global.get('bind_dn', "") and self.ldap_global.get('base_dn', "") and \
        self.ldap_global.get('bind_password', "") and 'ldap' in self.authentication.get('login', "") and \
            self.ldap_servers
```

`hostcfgd:720-721`:

```python
if 'ldap' in authentication['login']:
    pam_conf = template.render(debug=self.debug, trace=self.trace, auth=authentication, servers=ldapsrvs_conf)
```

### 依存内容

| `AAA|authentication.login` の状態 | 影響 |
|---|---|
| `ldap` を含む | `is_ldap_config_complete()` が `True` を返せる条件が整う。PAM 設定に LDAP サーバ一覧が注入される |
| `ldap` を含まない | `handle_nslcd_service(False)` → nslcd を stop & mask。LDAP_SERVER エントリが存在しても nslcd は起動しない |

**YANG leafref**: なし。`hostcfgd` の実装上の暗黙前提。

---

## 2. LDAP|global — サーバ設定生成の前提

### 参照箇所

`hostcfgd:650-651`:

```python
ldap_global = self.ldap_global_default.copy()
ldap_global.update(self.ldap_global)
```

`hostcfgd:706-713`:

```python
if self.ldap_servers:
    for addr in self.ldap_servers:
        server = ldap_global.copy()
        server['ip'] = addr
        server.update(self.ldap_servers[addr])
        ldapsrvs_conf.append(server)
    ldapsrvs_conf = sorted(ldapsrvs_conf, key=lambda t: int(t['priority']), reverse=True)
```

`nslcd.conf.j2` テンプレート展開 (`hostcfgd:854-863`):

```python
generate_file_from_template(NSLCD_CONF_TEMPLATE, NSLCD_CONF, 0o640, {'servers': ldapsrvs_conf, 'ldap_cfg': ldap.LdapCfg})
generate_file_from_template(LDAP_CONF_TEMPLATE, LDAP_CONF, 0o644, {'servers': ldapsrvs_conf, 'ldap_cfg': ldap.LdapCfg})
```

### 依存内容

| `LDAP|global` の状態 | 影響 |
|---|---|
| `bind_dn` / `base_dn` / `bind_password` 全て設定済み | `is_ldap_config_complete()` が `True` を返す条件を満たす。nslcd.conf に正しい `binddn`, `base`, `bindpw` ディレクティブが生成される |
| 未設定 / 部分設定 | `ldap_global == {}` → `is_ldap_config_complete()` が即 `False`。nslcd は起動しない |
| `LDAP_SERVER` より先に設定しない | `modify_conf_file()` が `server = ldap_global.copy()` するため、`LDAP|global` 未設定時は `LdapCfg` fallback 値 (`BASE = 'ou=users,dc=example,dc=com'` 等) が使われる |

**YANG leafref**: `sonic-system-ldap.yang` で `LDAP_SERVER` と `LDAP` は同一 YANG モジュール内の別リスト/コンテナ。leafref はないが同一モジュールの強い意味的依存あり。

---

## 3. DEVICE_METADATA|localhost — hostcfgd 初期化時の hostname 取得

### 参照箇所

`hostcfgd:1422`:

```python
device_metadata = self.config_db.get_table('DEVICE_METADATA')
```

`hostcfgd:1490-1496`:

```python
self.hostname = ''
# ...
self.hostname = dev_meta.get('localhost', {}).get('hostname', '')
```

`hostcfgd:566-570` `AaaCfg.hostname_update()`:

```python
def hostname_update(self, hostname, modify_conf=True):
    if self.hostname == hostname:
        return
    self.hostname = hostname
```

### 依存内容

`AaaCfg` は `hostname_update()` を通じて `self.hostname` を保持する。RADIUS の `nas_id` 設定に使われる (`hostcfgd:675-678`)。LDAP 設定自体には `hostname` は直接使われないが、同一 `AaaCfg.modify_conf_file()` フロー内で処理される。`DEVICE_METADATA|localhost` が存在しない場合、`hostname` が空文字列になるが LDAP 動作への直接影響はない。

| `DEVICE_METADATA|localhost.hostname` の状態 | LDAP への影響 |
|---|---|
| 設定済み | RADIUS の `nas_id` に使用。LDAP には影響なし |
| 未設定 | hostname が空文字列になる。LDAP 認証自体には影響なし |

**YANG leafref**: なし。`hostcfgd` 初期化時の読み取りのみ。

---

## 4. nslcd サービス — Linux NSS/PAM デーモン (外部参照)

### 参照箇所

`hostcfgd:241-251`:

```python
def handle_nslcd_service(is_ldap_config_complete):
    if is_ldap_config_complete:
        restart_service("nslcd")
    else:
        cmd_nslcd_return = run_cmd_output_custom_log(['systemctl', 'is-enabled', 'nslcd'], ...)
        if 'enabled' in cmd_nslcd_return.decode():
            run_cmd_output_custom_log(['systemctl', 'stop', 'nslcd'])
            run_cmd_output_custom_log(['systemctl', 'mask', 'nslcd'])
```

`nslcd.conf.j2` + `ldap.conf.j2` テンプレートが `/etc/nslcd.conf` / `/etc/ldap/ldap.conf` を生成。

### 依存内容

CONFIG_DB テーブルではないが、`LDAP_SERVER` → `LDAP|global` → `AAA|authentication.login=ldap` の 3 つが揃って初めて nslcd が起動・稼働する。この「3テーブル完全性ゲート」が LDAP 認証の実質的な必須条件となる。

---

## 5. SAI 参照

なし。LDAP 認証は純粋にユーザー空間 (nslcd / PAM) で完結する。APPL_DB 中継も SAI への書き込みも一切ない。

---

## cross-refs ブロック (docs/reference/config-db/ldap-server.md 向け)

```markdown
<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

> **調査根拠**: `sonic-host-services/scripts/hostcfgd` 全行精読 (2026-05-16)  
> 詳細証跡: `meta/_intermediate/cdb-flow/ldap-server-cross-refs.md`

`LDAP_SERVER` テーブルは YANG leafref を持たないが、`hostcfgd` の `AaaCfg` クラスが以下のテーブルを暗黙参照する。**3 テーブルが揃って初めて nslcd が起動し LDAP 認証が有効になる**。

| 参照先テーブル | DB | 参照方向 | YANG leafref | 実装上の必須度 | 証拠 |
|---|---|---|---|---|---|
| `AAA\|authentication` (`login` フィールド) | CONFIG_DB | 読み取り (`is_ldap_config_complete()` 判定) | なし | **必須** (未設定または `login` に `ldap` なしで nslcd 停止) | `hostcfgd:437-442`, `hostcfgd:241-251` |
| `LDAP\|global` (`bind_dn`, `base_dn`, `bind_password`) | CONFIG_DB | 読み取り (nslcd.conf 生成・completeness チェック) | なし (同一 YANG モジュール内の別コンテナ) | **必須** (未設定で nslcd 停止・`LdapCfg` fallback 値使用) | `hostcfgd:437-442`, `hostcfgd:650-651`, `hostcfgd:706-713` |
| `DEVICE_METADATA\|localhost` (`hostname`) | CONFIG_DB | 読み取り (hostcfgd 初期化時) | なし | 任意 (LDAP 動作への直接影響なし; RADIUS `nas_id` で使用) | `hostcfgd:1422-1496`, `hostcfgd:675-678` |

### AAA|authentication — LDAP 有効化ゲート

`is_ldap_config_complete()` は `'ldap' in self.authentication.get('login', "")` を条件の一つとして評価する (`hostcfgd:441`)。`AAA|authentication.login` に `ldap` が含まれない場合、`LDAP_SERVER` と `LDAP|global` が完全に設定済みであっても `handle_nslcd_service(False)` が呼ばれ nslcd を stop & mask する。**`config aaa authentication login ldap` を実行して AAA テーブルを更新するまで LDAP 認証は機能しない**。

### LDAP|global — nslcd.conf 生成の前提

`modify_conf_file()` は `server = ldap_global.copy(); server.update(self.ldap_servers[addr])` で各サーバのパラメータを合成し `nslcd.conf.j2` / `ldap.conf.j2` テンプレートに渡す (`hostcfgd:706-713`, `hostcfgd:854-863`)。`LDAP|global` が未設定の場合は `ldap_global == {}` → `is_ldap_config_complete()` が即 `False` を返す。推奨設定順序: `LDAP|global` → `LDAP_SERVER` → `AAA|authentication.login=ldap`。

### DEVICE_METADATA|localhost — hostname 取得

hostcfgd 初期化時に `DEVICE_METADATA` から `localhost.hostname` を取得し `self.hostname` に保持する (`hostcfgd:1422-1496`)。この値は RADIUS の `nas_id` に使われるが LDAP の nslcd.conf 生成には直接関与しない。`DEVICE_METADATA|localhost` が未設定でも LDAP 認証は動作する。

### SAI 参照

なし。LDAP 認証は nslcd / PAM のユーザー空間で完結し、APPL_DB 中継も SAI への書き込みも一切ない。

<!-- /cross-refs -->
```
