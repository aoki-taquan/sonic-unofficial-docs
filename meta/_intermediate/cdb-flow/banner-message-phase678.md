# BANNER_MESSAGE — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_0)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### init_cfg.json.j2 — global エントリ自動生成

```jinja2
{# sonic-buildimage/files/build_templates/init_cfg.json.j2:180 #}
"BANNER_MESSAGE": {
    "global": {
        "state": "disabled",
        "login": "Debian GNU/Linux 11",
        "motd": "You are on\n  ____   ___  ...\n\nHelp: ...\n\n",
        "logout": ""
    }
},
```

ビルド時に `BANNER_MESSAGE|global` が固定値で自動生成される。`state=disabled` / `login` / `motd` / `logout` は全て固定値（テンプレート変数なし）。

### minigraph.py / db_migrator.py

BANNER_MESSAGE への代入なし。

**結論**: ビルド時に init_cfg.json.j2 が `BANNER_MESSAGE|global` を固定値で派生代入。`state` のデフォルトは `disabled`。

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

### hostcfgd — BannerCfg クラス

```python
# sonic-host-services/scripts/hostcfgd:2215
self.bannermsgcfg = BannerCfg()
# hostcfgd:2520
self.config_db.subscribe(swsscommon.CFG_BANNER_MESSAGE_TABLE_NAME,
                         make_callback(self.banner_handler))
```

`BannerCfg` は **常時** インスタンス化・登録される。条件付き登録なし。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### BannerCfg.banner_message() — key 別 dispatch

```python
# sonic-host-services/scripts/hostcfgd:2084
def banner_message(self, key, data):
    # key: 'state', 'login', 'motd', 'logout'
    ...
    if key == 'state':
        # state フィールドの変更: banner-config サービス再起動
        run_cmd(["systemctl", "restart", "banner-config"], True, True)
```

| key | 処理 |
|-----|------|
| `state` | `banner-config` systemd サービスを再起動 |
| `login` | ログインバナーファイル更新 |
| `motd` | `/etc/motd` 更新 |
| `logout` | ログアウトメッセージ更新 |

### state フィールド分岐

| state 値 | 処理 |
|---------|------|
| `enabled` | バナー設定ファイルを生成し `banner-config` 再起動 |
| `disabled` | バナー設定を無効化し `banner-config` 再起動 |

サービス再起動失敗時は `syslog.LOG_ERR` を記録するのみ（crash なし）。

<!-- /handler-branching -->
