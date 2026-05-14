# AAA — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_0)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### minigraph.py

AAA テーブルへの代入なし。minigraph は TACACS+ / RADIUS サーバ情報を生成するが、`AAA` テーブル自体は出力しない。

### config_samples / init_cfg.json.j2

AAA テーブルの初期値記述なし。ビルド時デフォルト不在。

### db_migrator.py — `migrate_aaa()` (L869)

```python
# sonic-utilities/scripts/db_migrator.py:869
def migrate_aaa(self):
    if not self.config_src_data or 'AAA' not in self.config_src_data:
        return
    aaa_new = self.config_src_data['AAA']
    # authentication エントリが存在しない場合のみ移行
    authentication = self.configDB.get_entry('AAA', 'authentication')
    if not authentication:
        self.configDB.set_entry("AAA", "authentication", aaa_new.get("authentication"))
    # accounting 同様
    accounting = self.configDB.get_entry('AAA', 'accounting')
    if not accounting:
        self.configDB.set_entry("AAA", "accounting", aaa_new.get("accounting"))
    # authorization: TACACS+ passkey が存在する場合のみ移行
    tacplus_config = self.configDB.get_entry('TACPLUS', 'global')
    if 'passkey' in tacplus_config and '' != tacplus_config.get('passkey'):
        authorization = self.configDB.get_entry('AAA', 'authorization')
        if not authorization:
            self.configDB.set_entry("AAA", "authorization", aaa_new.get("authorization"))
    else:
        # passkey がない場合は authorization エントリを削除（remote ユーザコマンドブロック防止）
        keys = self.configDB.keys(self.configDB.CONFIG_DB, "AAA|authorization")
        if keys:
            self.configDB.delete(self.configDB.CONFIG_DB, "AAA|authorization")
```

**結論**: `db_migrator` が migration 時に `AAA|authentication` / `AAA|accounting` / `AAA|authorization` を条件付きで派生代入。authorization は TACPLUS passkey の有無に依存する条件付き代入。

### managers_*.py

AAA テーブルへの直接書き込みなし（読み取り側のみ）。

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

### hostcfgd — AaaCfg クラス

```python
# sonic-host-services/scripts/hostcfgd:2185
self.aaacfg = AaaCfg(self.config_db)
# ...
# hostcfgd:2470
self.config_db.subscribe('AAA', make_callback(self.aaa_handler))
```

`AaaCfg` は **常時** インスタンス化・登録される。条件付き登録なし。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### AaaCfg.aaa_update() — key 別 dispatch

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

| key | 処理 |
|-----|------|
| `authentication` | `self.authentication` 更新、`failthrough`/`debug` を bool 変換 |
| `authorization` | `self.authorization` 更新のみ |
| `accounting` | `self.accounting` 更新のみ |
| その他 | 実質 no-op（内部状態を更新しない） |

### LDAP 依存 early return

`authentication.login` に `ldap` が含まれる場合、`is_ldap_config_complete()` が False を返すと `nslcd` 起動をスキップする。

```python
# hostcfgd:435
def is_ldap_config_complete(self):
    if self.ldap_global == {}:
        return False
    return self.ldap_global.get('bind_dn', "") and \
           self.ldap_global.get('bind_password', "") and \
           self.ldap_global.get('base_dn', "")
```

`bind_dn` / `bind_password` / `base_dn` のいずれかが未設定 → nslcd 起動スキップ（early return）。

<!-- /handler-branching -->
