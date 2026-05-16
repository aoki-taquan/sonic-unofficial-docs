# AS_PATH_SET テーブル — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `AS_PATH_SET` テーブル、および補助購読経路として `DEVICE_METADATA[localhost].t2_group_asns` を読む `AsPathMgr` (bgpcfgd)。

## 1. 購読者は 2 経路 (両者とも Redis keyspace 通知ベース)

| 購読者 | 対象テーブル | 購読 API | 通信方式 | 主たるトリガキー |
|--------|------------|---------|---------|----------------|
| `frrcfgd` (sonic-frr-mgmt-framework) | `AS_PATH_SET` | `ExtConfigDBConnector.subscribe(table, hdlr)` + `listen()` | Redis **keyspace 通知** (`PSUBSCRIBE __keyspace@<dbId>__:*`) | `AS_PATH_SET|<name>` |
| `bgpcfgd` `AsPathMgr` | `DEVICE_METADATA` | `swsscommon.SubscriberStateTable` + `swsscommon.Select` | Redis **channel ベース PUBLISH/SUBSCRIBE** (`SubscriberStateTable` 内部) | `DEVICE_METADATA|localhost` の `t2_group_asns` フィールド |

両経路とも `AS_PATH_SET` テーブルの「直接」購読は frrcfgd だけで、`AsPathMgr` は AS_PATH_SET を読まずに `DEVICE_METADATA` 変更を契機に固定名 `T2_GROUP_ASNS` の access-list を生成する補助経路。CONFIG_DB は永続前提のため TTL は設定されない。

## 2. frrcfgd 側 — `ExtConfigDBConnector` (keyspace 通知)

frrcfgd は `ConfigDBConnector` を継承した `ExtConfigDBConnector` 経由で購読する (`frrcfgd.py:1506-1555`)。

```python
# frrcfgd.py:2359-2361
def subscribe_all(self):
    for table, hdlr in self.table_handler_list:
        self.config_db.subscribe(table, hdlr)
```

`table_handler_list` に `('AS_PATH_SET', self.bgp_table_handler_common)` が登録されている (`frrcfgd.py:2315`)。 

内部実装 (`frrcfgd.py:1536-1552`) は標準 `ConfigDBConnector.listen()` と同じく Redis の keyspace 通知 (`__keyspace@<dbId>__:*` の `PSUBSCRIBE`) を別スレッド (`listen_thread`) で受信し、テーブル名にマッチしたコールバック (`_ConfigDBConnector__fire`) へ `(table, row, data)` をディスパッチする。`SubscriberStateTable` (channel ベース) は **使用しない**。

- 通知ペイロード: Redis keyspace 通知の本体は操作名 (`hset`/`del` 等) のみ。値は `client.hgetall(key)` で再取得する (`frrcfgd.py:1527-1528`)。
- daemon バインド: `AS_PATH_SET` は `'bgpd'` のみへ送信 (`frrcfgd.py:96`)。
- 起動時スナップショット: `frrcfgd.py:2249-2253` で `config_db.get_table('AS_PATH_SET')` を読み、`as_path_set_member` キーを持つ entry のみ初期登録。`subscribe_all` 開始前に config replay (`frrcfgd.py:2344-2357`) を実行。

## 3. bgpcfgd `AsPathMgr` 側 — `SubscriberStateTable` (channel ベース)

`bgpcfgd` のメインループ `Runner` は `swsscommon.SubscriberStateTable` + `swsscommon.Select` で実装される (`runner.py:23-51`)。これは Redis の channel ベース PUBLISH/SUBSCRIBE (`ConsumerStateTable`-相当) を使う方式で、frrcfgd の keyspace 通知方式とは異なる。

```python
# bgpcfgd/runner.py:47-52
if table_name not in self.callbacks[db]:
    conn = self.db_connectors[db]
    subscriber = swsscommon.SubscriberStateTable(conn, table_name)
    self.subscribers.add(subscriber)
    self.selector.addSelectable(subscriber)
self.callbacks[db][table_name].append(manager.handler)
```

- `AsPathMgr` の登録: `main.py:122-130` で `DEVICE_METADATA[localhost]` の `type`/`subtype` が `SpineRouter`+`UpstreamLC` または `UpperSpineRouter` の場合のみ起動。
- 購読対象は `CONFIG_DB` の `DEVICE_METADATA` テーブル (`main.py:129`)。**AS_PATH_SET テーブル自体は購読しない**。
- イベントループ (`runner.py:54-73`): `selector.select(1000ms)` で待機、`subscriber.pop()` で `(key, op, fvs)` を取り出し `callback(key, op, dict(fvs))` 呼出。各 manager の `set_handler` / `del_handler` は `Manager.handler` 経由でディスパッチされる。

## 4. キー単位ディスパッチ

### frrcfgd

`bgp_table_handler_common` (`AS_PATH_SET` の登録ハンドラ) は `(table, key, data)` 3 引数を受ける。`data is None` で DEL、それ以外で SET と判別する (`ConfigDBConnector` 標準動作)。 `key` は `AS_PATH_SET|<name>` の右辺 `<name>`、`data` は `{action: ..., as_path_set_member: [...]}`。実際の FRR コマンド生成は `aspath_set_key_map = [('as_path_set_member', '{no:no-prefix}bgp as-path access-list {}', hdl_aspath_set)]` (`frrcfgd.py:1977`) と `hdl_aspath_set` (`frrcfgd.py:1009-1020`) が担当。

### AsPathMgr

`set_handler(self, key, data)` (`managers_as_path.py:30-58`) と `del_handler(self, key)` (`managers_as_path.py:60-66`) が `(key, op, fvs)` の dispatch を Manager 基底クラス経由で受ける。`key != "localhost"` の場合は即 return (`managers_as_path.py:31, 61`) のため `DEVICE_METADATA|localhost` のみが実効入力。`data` の `t2_group_asns` フィールドだけを参照 (`managers_as_path.py:34-37`)。

## 5. keyspace 通知 / channel 通知 → ハンドラ呼び出しの流れ

### frrcfgd 経路

```
config route-map as-path-set add UPSTREAM_FILTER _65000_
  ↓ HSET "AS_PATH_SET|UPSTREAM_FILTER" as_path_set_member@... "_65000_"
Redis keyspace PUBLISH "__keyspace@4__:AS_PATH_SET|UPSTREAM_FILTER" "hset"
  ↓ ExtConfigDBConnector.listen_thread() がパターンマッチ
sub_msg_handler() で HGETALL "AS_PATH_SET|UPSTREAM_FILTER"
  ↓ raw_to_typed() で leaf-list を Python list 化
bgp_table_handler_common("AS_PATH_SET", "UPSTREAM_FILTER", {as_path_set_member: [...]})
  ↓ aspath_set_key_map → hdl_aspath_set()
  ↓ vtysh -c "no bgp as-path access-list UPSTREAM_FILTER"   ← 先に全削除 (frrcfgd.py:1015)
  ↓ vtysh -c "bgp as-path access-list UPSTREAM_FILTER permit _65000_"   (frrcfgd.py:1017-1019)
```

### AsPathMgr 経路

```
config device-metadata localhost t2_group_asns 65001,65002
  ↓ HSET "DEVICE_METADATA|localhost" t2_group_asns "65001,65002"
Redis channel PUBLISH (SubscriberStateTable 内部)
  ↓ Runner.selector.select() で起床
subscriber.pop() → (key="localhost", op=SET, fvs={t2_group_asns:"65001,65002"})
  ↓ Manager.handler → AsPathMgr.set_handler("localhost", {t2_group_asns:"65001,65002"})
  ↓ cfg_mgr.update() で FRR running-config を読み戻し
  ↓ 差分計算 (regex r"bgp as-path access-list T2_GROUP_ASNS seq \d+ permit _(\d+)_" — managers_as_path.py:43)
  ↓ 不要な ASN を "no bgp as-path access-list T2_GROUP_ASNS seq <n> permit _<asn>_" で削除
  ↓ 新規 ASN を "bgp as-path access-list T2_GROUP_ASNS permit _<asn>_" で追加 (managers_as_path.py:56)
```

## 6. サービス再起動トリガー

| 契機 | 操作 | コード |
|------|------|--------|
| `AS_PATH_SET` 変更 (frrcfgd 経路) | FRR `bgpd` への vtysh コマンド送出のみ。`bgpd` プロセス restart **なし** | `frrcfgd.py:1015-1019` (`no bgp as-path access-list <name>` → `bgp as-path access-list <name> permit <regex>`) |
| `DEVICE_METADATA.t2_group_asns` 変更 (AsPathMgr 経路) | FRR `bgpd` への vtysh コマンド送出のみ。プロセス restart なし | `managers_as_path.py:52, 56, 65` |
| `DEVICE_METADATA.type`/`subtype` 変更 | `AsPathMgr` の登録自体は bgpcfgd 起動時に 1 回確定 (`main.py:128-130`)。 ランタイム変更で manager 追加・削除はされない | `main.py:115-130` (起動時 `get_table` で gate) |

vtysh コマンドの実行は `frrcfgd` の `g_run_command` および `bgpcfgd` の `cfg_mgr.push() / commit()` に閉じる。BGP セッション自体は再起動されず、既存セッションには次回 UPDATE 送信時 / `clear bgp ... soft in/out` 実施時に新しい access-list が適用される。

## 7. 並列性・ロック

- frrcfgd `ExtConfigDBConnector.listen_thread()` は **専用スレッド** で動作 (`frrcfgd.py:1551`)。`subscribe_all()` で登録されたハンドラはすべて同スレッド内で逐次実行される (ハンドラ間の競合は内部キュー `self.bgp_message` 経由で `__update_bgp` に直列化)。
- bgpcfgd `Runner` は **シングルスレッド** メインループ (`runner.py:54-73`)。各 manager の handler はメインスレッドで逐次実行され、ループ末尾で `cfg_manager.commit()` をまとめて発行する (`runner.py:71`)。
- 両経路ともロックは持たず、Redis 側のシリアル化 (各 client が単一接続) と Python シングルスレッド実行に依存。

## 8. 他プロセスからの購読有無

`AS_PATH_SET` テーブルを購読する SONiC プロセスは **`frrcfgd` のみ** (`grep -rn "AS_PATH_SET" .cache/sonic-sources` で frrcfgd と yang-models 以外ヒットなし)。`orchagent` / `syncd` / `swssconfig` 等の APPL_DB/ASIC_DB レイヤは AS_PATH_SET を読まない (Phase F で確認済み、`as-path-set-side.md` 参照)。`AsPathMgr` も AS_PATH_SET を直接購読しない (DEVICE_METADATA 経由で固定名生成)。

## 9. Evidence サマリ

- `frrcfgd.py:96` `'AS_PATH_SET': ['bgpd']`
- `frrcfgd.py:1009-1020` `hdl_aspath_set`
- `frrcfgd.py:1506-1555` `ExtConfigDBConnector` (keyspace listen 実装)
- `frrcfgd.py:1977` `aspath_set_key_map`
- `frrcfgd.py:2116` `'AS_PATH_SET': aspath_set_key_map`
- `frrcfgd.py:2249-2253` 起動時 `get_table('AS_PATH_SET')` スナップショット
- `frrcfgd.py:2315` table_handler_list 登録
- `frrcfgd.py:2359-2361` `subscribe_all`
- `bgpcfgd/runner.py:23-73` `SubscriberStateTable` ループ
- `bgpcfgd/main.py:122-130` `AsPathMgr` 登録 gate
- `bgpcfgd/managers_as_path.py:30-66` `set_handler`/`del_handler`
