# BGP_ALLOWED_PREFIXES — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_0)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### 全ソース — 該当なし

minigraph.py / config_samples / db_migrator.py / init_cfg.json.j2 に BGP_ALLOWED_PREFIXES への代入なし。CLI または REST で明示設定。

**結論**: Phase 6 派生なし。

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

### bgpcfgd — BGPAllowListMgr

```python
# sonic-bgpcfgd/bgpcfgd/main.py:94
BGPAllowListMgr(common_objs, "CONFIG_DB", "BGP_ALLOWED_PREFIXES"),
```

`BGPAllowListMgr` は **常時** 登録される。ただし内部の `enabled` フラグで機能有効/無効が制御される。

```python
# managers_allow_list.py:__init__
self.enabled = self.__get_enabled()
```

`constants` 設定から `enabled` を読み取る。`enabled=False` の場合は SET/DEL コマンドを受けても処理せずに return。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### BGPAllowListMgr.set_handler() — enabled チェック early return

```python
# managers_allow_list.py:set_handler()
if not self.enabled:
    log_warn("BGPAllowListMgr::Received 'SET' command, but this feature is disabled in constants")
    return True  # early return
```

`constants` で無効化されている場合は処理をスキップ。

### default_action フィールド分岐

`default_action` フィールド（`permit` / `deny`）により FRR route-map のデフォルト動作が切り替わる:

```python
# managers_allow_list.py:__get_default_action_community()
def __get_default_action_community(self, data):
    default_action = data.get("default_action", "deny")
    ...
```

| default_action 値 | FRR 処理 |
|-----------------|---------|
| `permit` | デフォルト permit。allow-list に含まれないプレフィックスも通過 |
| `deny` | `no-export` community を付与してデフォルト deny 相当を実現。直接 FRR deny ルールではなく、community 設定による間接実装 |

**間接実装の詳細**: `deny` は FRR の `deny` ステートメントを直接使うのではなく、`no-export` community を付与することで AS 外への流出を防ぐ間接方式。`NEIGHBOR_TYPE` 単位のサブポリシーと GLOBAL ポリシーで同一 community を共用し AND 条件によるフィルタリングを実現。

### key 形式検証 early return

```python
# managers_allow_list.py:__set_handler_validate()
if not self.key_re.match(key):
    log_err("Received BGP ALLOWED 'SET' message with invalid key: '%s'" % key)
    return False  # early return: 無効キー形式
```

`DEPLOYMENT_ID|<id>|<community>` / `DEPLOYMENT_ID|<id>|NEIGHBOR_TYPE|<type>` 形式に合致しない場合はスキップ。

<!-- /handler-branching -->
