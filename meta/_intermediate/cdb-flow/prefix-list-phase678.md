# PREFIX_LIST — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_4)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### 全ソース — 該当なし

minigraph.py / config_samples.py / db_migrator.py / init_cfg.json.j2 に PREFIX_LIST への代入なし。CLI または config_db.json で明示設定。

**結論**: Phase 6 派生なし。

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

### bgpcfgd/main.py — PrefixListMgr 常時登録

```python
# bgpcfgd/main.py:132
managers.append(PrefixListMgr(common_objs, "CONFIG_DB", "PREFIX_LIST"))
```

**常時** (無条件) 登録。AsPathMgr 等の条件付き登録とは異なる。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### managers_prefix_list.py — set_handler / del_handler 分岐

```python
# L28-29  set_handler 内バリデーション失敗 early return
if not self.__set_handler_validate(key, data):
    return True  # True = 処理済み (エラー扱いしない)

# L51-65  __set_handler_validate early return 条件
if ip_version not in ['ip', 'ipv6']:  return False
if action not in ['permit', 'deny']:  return False
if seq <= 0:                          return False
```

IP バージョン dispatch (`get_prefix_list_type()` L139-143):
- `ip` → `ip prefix-list` FRR コマンド
- `ipv6` → `ipv6 prefix-list` FRR コマンド

del_handler: `key` が定義済み PREFIX_LIST でない → early return。

<!-- /handler-branching -->
