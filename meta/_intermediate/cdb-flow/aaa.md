# AAA テーブル — consumer 例外条件分析

## Consumer: hostcfgd (sonic-host-services/scripts/hostcfgd)

### 処理関数
- `AaaCfg.aaa_update(key, data, modify_conf=True)` (L419)
- `AaaCfg.load(aaa_conf, ...)` (L400)

### 例外条件・特殊挙動

#### 1. key フィルタリング
`aaa_update` は key が `authentication` / `authorization` / `accounting` の 3 種のみ分岐処理する。
それ以外の key は明示的に reject されないが、`self.authentication/authorization/accounting` を上書きしないため実質 no-op になる。

```python
# sonic-host-services/scripts/hostcfgd:419
def aaa_update(self, key, data, modify_conf=True):
    if key == 'authentication':
        self.authentication = data
        if 'failthrough' in data:
            self.authentication['failthrough'] = is_true(data['failthrough'])
        if 'debug' in data:
            self.debug = is_true(data['debug'])
    if key == 'authorization':
        self.authorization = data
    if key == 'accounting':
        self.accounting = data
```

#### 2. boolean フィールドの型強制
`failthrough` / `debug` は `is_true()` ヘルパで文字列 → bool に変換。
`"true"` / `"True"` / `"yes"` / `"1"` が truthy、それ以外は False。文字列の型検証は行わない。

#### 3. LDAP 依存チェック (is_ldap_config_complete)
`authentication.login` に `ldap` が含まれる場合、`ldap_global.bind_dn`, `bind_password`, `base_dn` が揃わないと `nslcd` サービスを起動しない (no-op skip)。

```python
# sonic-host-services/scripts/hostcfgd:435
def is_ldap_config_complete(self):
    if self.ldap_global == {}:
        return False
    return self.ldap_global.get('bind_dn', "") and ...
```

#### 4. modify_conf_file — 設定ファイル再生成
`modify_conf=True` の場合、全設定を PAM ファイルに書き直す。失敗時は syslog に ERROR を書くのみ。crash しない。

#### 5. 依存関係: TACACS+
YANG `must` 制約で `authentication.login` に `tacacs+` を含む場合は `TACPLUS.global.passkey` 必須。ただしこれは YANG レベルの検証であり、hostcfgd は passkey の有無を実行時に再チェックしない。
