# ROUTE_MAP — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_4)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### 全ソース — 該当なし

minigraph.py / config_samples.py / db_migrator.py / init_cfg.json.j2 に ROUTE_MAP への代入なし。CLI (`config route-map`) または config_db.json で明示設定。

**結論**: Phase 6 派生なし。

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

### bgpcfgd/main.py — RouteMapMgr 登録

```python
# bgpcfgd/main.py:102
RouteMapMgr(common_objs, "APPL_DB", swsscommon.APP_BGP_PROFILE_TABLE_NAME),
```

RouteMapMgr は APPL_DB の BGP_PROFILE テーブルを購読 (CONFIG_DB の ROUTE_MAP とは別経路)。**常時** 登録、条件なし。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### managers_rm.py — set_handler / del_handler 分岐

```python
# L47-65  __set_handler_validate — early return 条件
if key not in ROUTE_MAPS:           return False  # 定義済み ROUTE_MAP 外
if type not in ['permit', 'deny']:  return False  # type 不正
if seq <= 0:                        return False  # seq 不正

# L70-73  __del_handler_validate
if key not in ROUTE_MAPS:           return False  # key 不存在
```

`ROUTE_MAPS` はデプロイ固有の route-map 名一覧 (bgpcfgd constants)。その外のキーは early return。

deployment_id に応じた ASN マッピング dispatch (L80):
```python
return self.constants['deployment_id_asn_map'][FROM_SDN_SLB_DEPLOYMENT_ID]
```

<!-- /handler-branching -->
