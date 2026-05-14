# RESTAPI — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_4)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### minigraph.py — RESTAPI 自動生成

```
# minigraph.py:2689
results['RESTAPI'] = {
    'config': {'client_auth': 'user_jwt',
               'allow_insecure': 'false',
               'log_level': 'notice'},
    'certs': {}
}
```

### init_cfg.json.j2 — RESTAPI feature 条件

```
# restapi feature: type NOT IN [LeafRouter, BackEndLeafRouter] → enabled
```

### db_migrator.py — RESTAPI 欠如補完 (Phase 6 派生)

```
# db_migrator.py:608-619  migrate_restapi()
config = self.configDB.get_entry('RESTAPI', 'config')
if not config:
    self.configDB.set_entry("RESTAPI", "config", restapi_data.get("config"))
certs = self.configDB.get_entry('RESTAPI', 'certs')
if not certs:
    self.configDB.set_entry("RESTAPI", "certs", restapi_data.get("certs"))
```

既存エントリ欠如時にデフォルト値を **自動補完**。

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

RESTAPI は `feature` テーブルで有効/無効が制御。featuremgrd が `FEATURE|restapi` の `state` を見てコンテナを起動/停止。`type NOT IN [LeafRouter, BackEndLeafRouter]` のとき `always_enabled` (間接的な条件付き起動)。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### RESTAPI サービス — 起動時読み込み

| フィールド | 処理 |
|-----------|------|
| `client_auth` | JWT / cert 認証モード選択 |
| `allow_insecure` | HTTP 許可/拒否 |
| `log_level` | ログレベル設定 |

CONFIG_DB の RESTAPI は主に起動時設定。実行時の動的変更ハンドラは最小限。

<!-- /handler-branching -->
