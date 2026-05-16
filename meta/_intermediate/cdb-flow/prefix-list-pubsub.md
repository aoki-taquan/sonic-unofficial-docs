# PREFIX_LIST — Phase G: CONFIG_DB 購読メカニズム

## 調査対象ソース

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_prefix_list.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/runner.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/radian/add_radian.conf.j2`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/suppress_prefix/add_suppress_prefix.conf.j2`

## 購読メカニズム: swsscommon.SubscriberStateTable

`bgpcfgd` の `Runner.add_manager()` が `swsscommon.SubscriberStateTable(conn, table_name)` を生成し、
`swsscommon.Select` に登録する。`PrefixListMgr` は `"CONFIG_DB"` / `"PREFIX_LIST"` テーブルを購読対象として登録される (`main.py` L132)。

```python
# runner.py L49-52
subscriber = swsscommon.SubscriberStateTable(conn, table_name)
self.subscribers.add(subscriber)
self.selector.addSelectable(subscriber)
self.callbacks[db][table_name].append(manager.handler)
```

## イベントループ

`Runner.run()` が `selector.select(1000ms)` でブロック待機し、変更があると `subscriber.pop()` で
`(key, op, fvs)` タプルを取得。`op == "SET"` → `manager.set_handler(key, fvs)`、`op == "DEL"` → `manager.del_handler(key)` が呼ばれる。

## Jinja2 テンプレート経路

`PrefixListMgr.__init__` で `PREFIX_TYPE_CONFIG` の各エントリに対し Jinja2 テンプレートを事前ロード:

| prefix_type | add テンプレート | del テンプレート |
|---|---|---|
| `ANCHOR_PREFIX` | `bgpd/radian/add_radian.conf.j2` | `bgpd/radian/del_radian.conf.j2` |
| `SUPPRESS_PREFIX` | `bgpd/suppress_prefix/add_suppress_prefix.conf.j2` | `bgpd/suppress_prefix/del_suppress_prefix.conf.j2` |

`add_radian.conf.j2` の抜粋:

```jinja2
{{ data.ipv }} prefix-list ANCHOR_CONTRIBUTING_ROUTES permit {{ data.prefix }} ge {{ data.prefixlen + 1 }}
router bgp {{ data.bgp_asn }}
{% if data.ipv == 'ip' %}
 address-family ipv4 unicast
{% else %}
 address-family ipv6 unicast
{% endif %}
 aggregate-address {{ data.prefix }} route-map TAG_ANCHOR_COMMUNITY
 exit
exit
```

`add_suppress_prefix.conf.j2`:

```jinja2
{{ data.ipv }} prefix-list {{ data.prefix_list_name }} permit {{ data.prefix }}
```

テンプレート展開後、`cfg_mgr.push(cmd)` で FRR vtysh に送信する。

## 購読フロー要約

```
CONFIG_DB PREFIX_LIST (SubscriberStateTable)
  └─ bgpcfgd PrefixListMgr
       ├─ set_handler: key split → netaddr.IPNetwork parse
       │    └─ generate_prefix_list_config(add=True)
       │         ├─ ANCHOR_PREFIX → add_radian.conf.j2 → vtysh (ip/ipv6 prefix-list + aggregate-address)
       │         └─ SUPPRESS_PREFIX → add_suppress_prefix.conf.j2 → vtysh (ip/ipv6 prefix-list permit)
       └─ del_handler: 同様に del テンプレートを使用
```
