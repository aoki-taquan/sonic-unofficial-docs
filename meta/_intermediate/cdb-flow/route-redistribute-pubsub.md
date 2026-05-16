# ROUTE_REDISTRIBUTE テーブル — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `ROUTE_REDISTRIBUTE` テーブル。購読者: `frrcfgd` (sonic-frr-mgmt-framework) および `bgpcfgd` (sonic-bgpcfgd)。

## 1. frrcfgd の購読 API — `ConfigDBConnector.subscribe()` (keyspace 通知ベース)

`frrcfgd` は `swsscommon.ConfigDBConnector` を継承した `ExtConfigDBConnector` を使用し、`subscribe_all()` でテーブルごとにハンドラを登録する。

```python
# frrcfgd.py L2359-2361
def subscribe_all(self):
    for table, hdlr in self.table_handler_list:
        self.config_db.subscribe(table, hdlr)
```

```python
# frrcfgd.py L2316 (table_handler_list の一部)
('ROUTE_REDISTRIBUTE', self.bgp_table_handler_common),
```

`ConfigDBConnector.subscribe()` は内部で Redis keyspace 通知（`__keyspace@<dbId>__:<TABLE>|*` への `PSUBSCRIBE`）を購読し、テーブル名にマッチするコールバックへ `(table, key, data)` をディスパッチする。`ConsumerStateTable` / `PUBLISH` 形式は使用しない。

起動シーケンス:

```python
# frrcfgd.py L3955
self.subscribe_all()
# その後 config_db.listen() で Redis keyspace 通知ループへ入る
```

## 2. frrcfgd の ROUTE_REDISTRIBUTE ハンドラ

`bgp_table_handler_common` が `ROUTE_REDISTRIBUTE` イベントを受信すると、`L3149` 以降の分岐で以下を実行する:

```python
# frrcfgd.py L3149-3168
elif table == 'ROUTE_REDISTRIBUTE':
    src_proto, dst_proto, af = key.split('|')
    if af == 'ipv6' and src_proto == 'ospf3':
        src_proto = 'ospf6'
    ip_type = 'unicast'
    if dst_proto != 'bgp':
        syslog.syslog(syslog.LOG_ERR, 'only bgp could be used as dst protocol...')
        continue
    op = CachedDataWithOp.OP_DELETE if del_table else CachedDataWithOp.OP_UPDATE
    data['protocol'] = CachedDataWithOp(src_proto, op)
    cmd_prefix = ['configure terminal',
                  'router bgp {} vrf {}'.format(local_asn, vrf),
                  'address-family {} {}'.format(af, ip_type)]
    ret_val = key_map.run_command(self, table, data, cmd_prefix)
```

FRR へのコマンド送出は `__run_command()` → `run_vtysh_command()` → `subprocess` で `vtysh -c ...` を呼び出す形式:

```python
# frrcfgd.py L2363-2364 (__run_command)
@staticmethod
def __run_command(table, command, daemons=None):
    return g_run_command(table, command, True, daemons)

# frrcfgd.py L44-52 (g_run_command)
def g_run_command(table, command, ignore_fail=False, daemons=None):
    if not (len(command) > 0 and command[0] == 'vtysh'):
        ...
    if not bgpd_client.run_vtysh_command(table, command, daemons) and not ignore_fail:
        ...
```

生成される vtysh コマンド列の例（connected を IPv4 unicast に再配布）:

```
vtysh -c "configure terminal"
      -c "router bgp 65100 vrf default"
      -c "address-family ipv4 unicast"
      -c "redistribute connected"
```

`route_redist_key_map` (frrcfgd.py L1979-1980) のテンプレ:

```
'{no:no-prefix}redistribute {} {:redist-metric} {:redist-route-map}'
```

削除時は `del_table=True` → `OP_DELETE` → `no redistribute <src>` として送出される。

## 3. bgpcfgd の購読 API — `SubscriberStateTable`

`bgpcfgd` は `ROUTE_REDISTRIBUTE` テーブルを直接購読しない。`STATIC_ROUTE` テーブルを `swsscommon.SubscriberStateTable` で購読し、静的経路の追加・削除をトリガーに `redistribute static route-map STATIC_ROUTE_FILTER` を BGP に設定する。

```python
# runner.py L49-51
subscriber = swsscommon.SubscriberStateTable(conn, table_name)
self.subscribers.add(subscriber)
self.selector.addSelectable(subscriber)
```

```python
# runner.py L63-69 (イベントループ)
for subscriber in self.subscribers:
    while True:
        key, op, fvs = subscriber.pop()
        if not key:
            break
        for callback in self.callbacks[db][subscriber.getTableName()]:
            callback(key, op, dict(fvs))
```

`SubscriberStateTable` は Redis の `__keyspace@<db>__:<TABLE>|*` 通知ではなく、`SUBSCRIBE <TABLE>_CHANNEL` 形式の channel 購読を使用する（swsscommon の Consumer/Producer パターン）。CONFIG_DB の `STATIC_ROUTE` エントリが `sonic-cfggen` / CLI によって `HSET` されると、`SubscriberStateTable` 経由でイベントが `StaticRouteMgr.handler()` へ届く。

```python
# main.py L98-99
StaticRouteMgr(common_objs, "CONFIG_DB", "STATIC_ROUTE"),
StaticRouteMgr(common_objs, "APPL_DB", "STATIC_ROUTE"),
```

## 4. bgpcfgd の FRR コマンド送出

`StaticRouteMgr` は `cfg_mgr.push_list()` でコマンドリストをキューに積み、`commit()` 時に `vtysh -f <tmp_file>` でまとめて FRR bgpd に適用する。

```python
# managers_static_rt.py L221-235 (enable_redistribution_command)
def enable_redistribution_command(self, vrf):
    cmd_list = []
    cmd_list.append("route-map STATIC_ROUTE_FILTER permit 10")
    cmd_list.append(" match tag %s" % self.ROUTE_ADVERTISE_ENABLE_TAG)
    cmd_list.append("router bgp %s" % bgp_asn)
    for af in ["ipv4", "ipv6"]:
        cmd_list.append(" address-family %s" % af)
        cmd_list.append("  redistribute static route-map STATIC_ROUTE_FILTER")
        cmd_list.append(" exit-address-family")
    return cmd_list
```

```python
# frr.py L46-48 (ConfigMgr.commit)
command = ["vtysh", "-f", tmp_filename]
ret_code, out, err = run_command(command)
```

`ConfigDBConnector.subscribe()` (frrcfgd) と `SubscriberStateTable` (bgpcfgd) の違い:

| 項目 | frrcfgd | bgpcfgd |
|------|---------|---------|
| 購読 API | `ConfigDBConnector.subscribe()` (keyspace 通知) | `swsscommon.SubscriberStateTable` (channel 通知) |
| 購読テーブル | `ROUTE_REDISTRIBUTE` | `STATIC_ROUTE` (CONFIG_DB + APPL_DB) |
| FRR 送出方法 | `vtysh -c <cmd>` (逐次) | `vtysh -f <tmpfile>` (バッチ) |
| 起動時スナップショット | `subscribe_all()` → `listen()` 開始時に既存データを一括処理 | `runner.run()` ループ開始後にのみ差分受信 |

## 5. keyspace 通知パターン (frrcfgd)

| Redis keyspace イベント | frrcfgd 受信 | 結果 |
|------------------------|--------------|------|
| `__keyspace@4__:ROUTE_REDISTRIBUTE\|default\|connected\|bgp\|ipv4` `hset` | `bgp_table_handler_common("ROUTE_REDISTRIBUTE", "connected\|bgp\|ipv4", SET, {...})` | `vtysh ... redistribute connected` 発行 |
| `__keyspace@4__:ROUTE_REDISTRIBUTE\|default\|ospf3\|bgp\|ipv6` `hset` | 同上 `src_proto` を `ospf6` に変換 | `vtysh ... redistribute ospf6` 発行 |
| `__keyspace@4__:ROUTE_REDISTRIBUTE\|default\|connected\|bgp\|ipv4` `del` | `OP_DELETE` | `vtysh ... no redistribute connected` 発行 |

dbId は CONFIG_DB の標準 4 (sonic-swss-common `database_config.json` 既定)。

## 6. ConsumerStateTable / NotificationProducer 非使用の確認 (ROUTE_REDISTRIBUTE)

- `ROUTE_REDISTRIBUTE` テーブルに `swsscommon.ConsumerStateTable` 購読者は存在しない。
- `NotificationProducer` で `ROUTE_REDISTRIBUTE` 関連の通知を出す箇所は SONiC ソース内になし。
- 結論: `ROUTE_REDISTRIBUTE` は **CONFIG_DB → frrcfgd(keyspace 通知) → vtysh → bgpd(FRR)** の一方向で完結し、APPL_DB/STATE_DB の中継パスを持たない。

## 7. 参考行番号

- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
  - L2316: `('ROUTE_REDISTRIBUTE', self.bgp_table_handler_common)` — テーブルハンドラ登録
  - L2359-2361: `subscribe_all()`
  - L3149-3168: ROUTE_REDISTRIBUTE イベント処理ロジック
  - L1979-1980: `route_redist_key_map` テンプレ
  - L3955: `self.subscribe_all()` — 起動時呼び出し
  - L44-52: `g_run_command()` — vtysh 実行
  - L279-281: `run_vtysh_command()`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/runner.py`
  - L49-51: `SubscriberStateTable` 登録
  - L63-69: イベントループ (`subscriber.pop()`)
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_static_rt.py`
  - L220-235: `enable_redistribution_command()`
  - L237-253: `disable_redistribution_command()`
  - L257: `cfg_mgr.push_list()`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/frr.py`
  - L46-48: `vtysh -f <tmpfile>` バッチ送出
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py`
  - L98-99: `StaticRouteMgr` の登録 (CONFIG_DB + APPL_DB)
