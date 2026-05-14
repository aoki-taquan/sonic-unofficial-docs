# AS_PATH_SET — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_0)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### 全ソース — 該当なし

minigraph.py / config_samples / db_migrator.py / init_cfg.json.j2 に AS_PATH_SET への代入なし。CLI (`config bgp as-path-set`) で明示設定。

**結論**: Phase 6 派生なし。

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

### bgpcfgd (sonic-bgpcfgd) — AsPathMgr

```python
# sonic-bgpcfgd/bgpcfgd/main.py:120-126
is_upstream_lc = (device_metadata["localhost"]["type"] == "SpineRouter" and
                  device_metadata["localhost"]["subtype"] == "UpstreamLC")
is_upper_spine_router = (device_metadata["localhost"]["type"] == "UpperSpineRouter")
if is_upstream_lc or is_upper_spine_router:
    managers.append(AsPathMgr(common_objs, "CONFIG_DB", "DEVICE_METADATA"))
    log_notice("AsPath Manager is enabled for %s" % ...)
```

`AsPathMgr` は **条件付き登録**。`DEVICE_METADATA.localhost.type == "UpperSpineRouter"` または `type == "SpineRouter" and subtype == "UpstreamLC"` の場合のみ起動時に登録される。

### frrcfgd (sonic-frr-mgmt-framework) — bgp_table_handler_common

```python
# sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py:2315
('AS_PATH_SET', self.bgp_table_handler_common),
```

frrcfgd の `BgpdClientMgr` は AS_PATH_SET を **常時** 購読。frrcfgd が有効な環境（sonic-frr-mgmt-framework がインストールされた場合）に限る。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### AsPathMgr.set_handler() — key early return

```python
# sonic-bgpcfgd/bgpcfgd/managers_as_path.py:34
def set_handler(self, key, data):
    if key != "localhost":
        return True  # early return: localhost 以外は無視
```

`key != "localhost"` の場合は即時 return（no-op）。AS_PATH_SET ではなく DEVICE_METADATA テーブルを購読し、`t2_group_asns` フィールドのみ処理対象。

### frrcfgd — AS_PATH_SET handler 分岐

```python
# frrcfgd/frrcfgd.py:2998-3011
elif table == 'AS_PATH_SET':
    as_set_data = data.get('as_path_set_member', None)
    if as_set_data is not None and (as_set_data.op == OP_DELETE or len(as_set_data.data) == 0):
        del_table = True
    if del_table:
        self.as_path_set_list.pop(as_set_name, None)
    elif as_set_data is not None:
        self.as_path_set_list[as_set_name] = as_set_data.data[:]
```

`as_path_set_member` フィールドが空またはDELETE → `del_table = True` で FRR から削除。非空の場合は `bgp as-path access-list` コマンドを生成して push。

`action` フィールド（`permit` / `deny`）は FRR コマンド生成時に `aspath_set_key_map` (L1977) で変換される:

| action 値 | FRR コマンド |
|-----------|------------|
| `permit` | `bgp as-path access-list <name> permit <regex>` |
| `deny` | `bgp as-path access-list <name> deny <regex>` |

<!-- /handler-branching -->
