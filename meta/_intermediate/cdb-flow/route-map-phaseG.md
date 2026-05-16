# ROUTE_MAP — Phase G 通信メカニズム中間ファイル

生成日: 2026-05-16

ソース:
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
- `sonic-buildimage/src/sonic-frr-mgmt-framework/templates/bgpd/bgpd.conf.db.route_map.j2`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_rm.py`

<!-- pubsub -->
## Phase G: CONFIG_DB Subscribe 機構

### frrcfgd — ExtConfigDBConnector + Redis keyspace psubscribe

`frrcfgd.py` は `ConfigDBConnector` を継承した `ExtConfigDBConnector` を使用する。
`listen_thread()` が Redis keyspace イベント `__keyspace@<dbid>__:*` を `psubscribe` で監視し、
`sub_msg_handler()` がテーブル変更を検知してハンドラを呼び出す。

```python
# frrcfgd.py L1539-1543
sub_key_space = "__keyspace@{}__:*".format(self.get_dbid(self.db_name))
self.pubsub.psubscribe(sub_key_space)
```

`subscribe_all()` で `table_handler_list` の全テーブルを登録:

```python
# L2302
('ROUTE_MAP', self.bgp_table_handler_common),

# L2359-2361
def subscribe_all(self):
    for table, hdlr in self.table_handler_list:
        self.config_db.subscribe(table, hdlr)
```

ROUTE_MAP の適用デーモン: `['zebra', 'bgpd', 'ospfd']` (frrcfgd.py L86)

### Jinja2 テンプレート経路

`bgpd.conf.db.route_map.j2` が CONFIG_DB の ROUTE_MAP 全エントリを展開:

```jinja2
{% for rm_key, rm_val in ROUTE_MAP.items() %}
{% if 'route_operation' in rm_val %}
route-map {{rm_key[0]}} {{rm_val['route_operation']}} {{rm_key[1]}}
{% if 'match_as_path' in rm_val %}
 match as-path {{rm_val['match_as_path']}}
{% endif %}
{% if 'match_prefix_set' in rm_val %}
 match {ip|ipv6} address prefix-list {{rm_val['match_prefix_set']}}
{% endif %}
...set_* フィールドも同様にテンプレート展開
{% endfor %}
```

テンプレート展開後、vtysh `configure terminal` → `route-map <name> <action> <seq>` + 各 match/set 句を発行。

### SubscriberStateTable 相当 — bgpcfgd RouteMapMgr (SDN 専用)

`managers_rm.py` の `RouteMapMgr` は bgpcfgd フレームワーク内で `APPL_DB` の `BGP_PROFILE_TABLE` を購読し、SDN 専用の 2 キーのみ処理:

```python
ROUTE_MAPS = ["FROM_SDN_SLB_ROUTES", "FROM_SDN_APPLIANCE_ROUTES"]
```

汎用 ROUTE_MAP の CONFIG_DB 購読は frrcfgd が担当。bgpcfgd テンプレートエンジンは CONFIG_DB を一括読み込みして FRR 設定ファイルを生成する別経路も持つ。

### 購読フロー

```
CONFIG_DB ROUTE_MAP (redis keyspace event)
  ├─ frrcfgd ExtConfigDBConnector.psubscribe
  │    └─ bgp_table_handler_common (ROUTE_MAP)
  │         └─ bgpd.conf.db.route_map.j2 展開
  │              └─ vtysh -c "configure terminal"
  │                   -c "route-map <name> <permit|deny> <seq>"
  │                   -c "match ..." / "set ..."
  │              → bgpd / zebra / ospfd に反映
  └─ bgpcfgd RouteMapMgr (APPL_DB BGP_PROFILE 経由, SDN 専用)
       └─ cfg_mgr.push_list → vtysh route-map FROM_SDN_*_RM permit 100
```

<!-- /pubsub -->
