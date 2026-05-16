# COMMUNITY_SET — Phase G 通信メカニズム中間ファイル

生成日: 2026-05-16

ソース:
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/runner.py`

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
# frrcfgd.py L2300-2301
('COMMUNITY_SET', self.comm_set_handler),
('EXTENDED_COMMUNITY_SET', self.comm_set_handler),

# L2359-2361
def subscribe_all(self):
    for table, hdlr in self.table_handler_list:
        self.config_db.subscribe(table, hdlr)
```

`comm_set_handler` は `bgp_table_handler_common` → `hdl_com_set()` を経由して FRR vtysh コマンドを生成する。

### vtysh 経路 — hdl_com_set

```python
# frrcfgd.py L981-1006
def hdl_com_set(daemon, cmd_str, op, st_idx, args, extended):
    if len(args) < 2 or 0 not in args[1] or 1 not in args[1] or 2 not in args[1]:
        return None  # 必須フィールド欠如 → スキップ
    set_type = args[1][0][0].lower()   # STANDARD / EXPANDED
    match_action = args[1][1][0].lower()  # all / any
    member_list = args[1][2][0]
    if match_action == 'all':
        # 全 member を 1 行にまとめて bgp community-list permit コマンドを生成
        cmd_list.append(cmd_str.format(...mbr_str...))
    elif match_action == 'any':
        # member ごとに個別の bgp community-list permit コマンドを生成
        for member in member_list:
            cmd_list.append(cmd_str.format(...mbr_str...))
```

生成コマンド形式:
- `configure terminal`
- `bgp community-list <standard|expanded> <name> permit <value>`

適用対象デーモン: `bgpd` (frrcfgd.py L84-85)

### bgpcfgd (sonic-bgpcfgd) — 非購読

bgpcfgd は COMMUNITY_SET テーブルを `SubscriberStateTable` で購読しない。
`runner.py` の `Runner.add_manager()` は各 Manager が指定するテーブルを `SubscriberStateTable` で登録するが、
bgpcfgd の Manager 群に COMMUNITY_SET 購読は含まれない。
COMMUNITY_SET は FRR BGP policy 専用であり、frrcfgd が単独で担当する。

### 購読フロー

```
CONFIG_DB COMMUNITY_SET / EXTENDED_COMMUNITY_SET (redis keyspace event)
  └─ frrcfgd ExtConfigDBConnector.psubscribe
       └─ comm_set_handler → bgp_table_handler_common
            └─ hdl_com_set (match_action: all/any 分岐)
                 └─ vtysh configure terminal
                      └─ bgp community-list <standard|expanded> <name> permit <value>
                           → bgpd に反映（次回 BGP route-map 評価から適用）

bgpcfgd: COMMUNITY_SET 非購読（SubscriberStateTable なし）
```

<!-- /pubsub -->
