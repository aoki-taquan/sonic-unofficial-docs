# PREFIX_SET / PREFIX テーブル — 購読メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `PREFIX_SET` / `PREFIX` テーブル。

## 1. 購読デーモン: frrcfgd (sonic-frr-mgmt-framework)

`frrcfgd.py` の `ExtConfigDBConnector` が Redis keyspace イベントを psubscribe して CONFIG_DB 変更を検知する。
`FRRCfgd.__init__` 内で構築する `table_handler_list` に `PREFIX_SET` と `PREFIX` の両エントリが含まれ、
共通ハンドラ `bgp_table_handler_common` が割り当てられる。

```python
# frrcfgd.py L2298-2299
('PREFIX_SET', self.bgp_table_handler_common),
('PREFIX', self.bgp_table_handler_common),
```

`subscribe_all()` が全エントリを `config_db.subscribe(table, hdlr)` に渡し、
`ExtConfigDBConnector.listen_thread` が `__keyspace@<dbid>__:*` に `psubscribe` して
変更通知を受信する（frrcfgd.py L1536-1552）。

```python
# frrcfgd.py L2359-2361
def subscribe_all(self):
    for table, hdlr in self.table_handler_list:
        self.config_db.subscribe(table, hdlr)
```

## 2. 処理フロー

変更検知後、`bgp_table_handler_common` が `bgp_message` キューにメッセージを投入し、
`__update_bgp` が処理する。

- `PREFIX_SET` イベント: `prefix_set_list` キャッシュを更新（新規 SET 時は `MatchPrefixList(mode)` を追加、DEL 時は削除）。FRR コマンドは直接発行せず Jinja2 テンプレート経路で処理（frrcfgd.py L2894-2910）。
- `PREFIX` イベント: `prefix_set_list` から対応する af を参照し、IPv4 なら全デーモン対象・IPv6 なら `['bgpd', 'zebra']` 限定で `ip/ipv6 prefix-list` vtysh コマンドを生成（frrcfgd.py L2911-2936）。

Jinja2 テンプレート `bgpd.conf.db.pref_list.j2` が `PREFIX_SET` / `PREFIX` 両テーブルを走査し、
`ip prefix-list` / `ipv6 prefix-list` コマンドを生成する。適用対象デーモンは PREFIX の AF に依存する。

```
CONFIG_DB PREFIX_SET / PREFIX
  └─ frrcfgd (ExtConfigDBConnector psubscribe)
       └─ bgp_table_handler_common
            ├─ PREFIX_SET: prefix_set_list キャッシュ更新のみ（FRR コマンド非発行）
            └─ PREFIX: vtysh ip/ipv6 prefix-list <name> seq <seq> <action> <prefix>
                       適用デーモン: IPv4 → None (全デーモン) / IPv6 → ['bgpd', 'zebra']
```

## 3. bgpcfgd (sonic-bgpcfgd) の関与

`sonic-bgpcfgd` の各 Manager は `PREFIX_SET` / `PREFIX` テーブルを購読しない。
bgpcfgd テンプレートエンジンは CONFIG_DB を読み込んで FRR 設定を生成するが、
PREFIX_SET / PREFIX への直接サブスクリプションは存在しない（sonic-bgpcfgd 全ソース確認済み）。

## 4. 証跡

- `frrcfgd.py` L2293-2338: `table_handler_list` 定義（PREFIX_SET L2298、PREFIX L2299）
- `frrcfgd.py` L2359-2361: `subscribe_all()`
- `frrcfgd.py` L1536-1552: `listen_thread` / `psubscribe` 実装
- `frrcfgd.py` L2894-2910: PREFIX_SET ハンドラ（キャッシュ更新）
- `frrcfgd.py` L2911-2936: PREFIX ハンドラ（vtysh コマンド生成）
- `bgpd.conf.db.pref_list.j2` L1-42: Jinja2 テンプレート全文
