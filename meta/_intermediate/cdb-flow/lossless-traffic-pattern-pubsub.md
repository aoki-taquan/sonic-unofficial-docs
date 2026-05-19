# LOSSLESS_TRAFFIC_PATTERN テーブル — 通信メカニズム (Phase G) 解析メモ

対象: `LOSSLESS_TRAFFIC_PATTERN` テーブルと、`buffermgrdyn` + Lua ヘッドルーム計算プラグインの通信経路。

ソース確認:
- `sonic-swss/cfgmgr/buffermgrd.cpp:174-186` — `buffer_table_connectors` (dynamic mode)
- `sonic-swss/cfgmgr/buffermgrdyn.h` / `buffermgrdyn.cpp` — `BufferMgrDynamic` クラス定義
- `sonic-swss/cfgmgr/buffer_headroom_mellanox.lua:91-96` — CONFIG_DB 直接参照
- `sonic-swss/cfgmgr/buffer_headroom_barefoot.lua:80-84` — CONFIG_DB 直接参照

## 1. `buffermgrdyn` は `LOSSLESS_TRAFFIC_PATTERN` を Subscribe しない

`buffermgrd.cpp:174-186` の `buffer_table_connectors` に `LOSSLESS_TRAFFIC_PATTERN` は含まれていない:

```cpp
vector<TableConnector> buffer_table_connectors = {
    TableConnector(&cfgDb, CFG_PORT_TABLE_NAME),
    TableConnector(&cfgDb, CFG_PORT_CABLE_LEN_TABLE_NAME),
    TableConnector(&cfgDb, CFG_BUFFER_POOL_TABLE_NAME),
    TableConnector(&cfgDb, CFG_BUFFER_PROFILE_TABLE_NAME),
    TableConnector(&cfgDb, CFG_BUFFER_PG_TABLE_NAME),
    TableConnector(&cfgDb, CFG_BUFFER_QUEUE_TABLE_NAME),
    TableConnector(&cfgDb, CFG_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME),
    TableConnector(&cfgDb, CFG_BUFFER_PORT_EGRESS_PROFILE_LIST_NAME),
    TableConnector(&cfgDb, CFG_DEFAULT_LOSSLESS_BUFFER_PARAMETER),   ← 注: ここまで
    TableConnector(&stateDb, STATE_BUFFER_MAXIMUM_VALUE_TABLE),
    TableConnector(&stateDb, STATE_PORT_TABLE_NAME)
    // LOSSLESS_TRAFFIC_PATTERN はない
};
```

`Orch(tables)` コンストラクタが `SubscriberStateTable` を登録するのはこのリスト内のテーブルのみ。
`LOSSLESS_TRAFFIC_PATTERN` に対して keyspace notification / PSUBSCRIBE は張られない。

## 2. Lua スクリプトが実行時に CONFIG_DB を直接読み取る

`LOSSLESS_TRAFFIC_PATTERN` の値は、`calculateHeadroomSize()` が呼ばれたタイミングで
ベンダー別 Lua プラグインが CONFIG_DB から `redis.call('KEYS', ...)` + `redis.call('HGETALL', ...)` で直接取得する:

```lua
-- buffer_headroom_mellanox.lua:91-96
local lossless_traffic_keys = redis.call('KEYS', 'LOSSLESS_TRAFFIC_PATTERN*')
if #lossless_traffic_keys == 0 then
    return {}
end
local lossless_traffic = redis.call('HGETALL', lossless_traffic_keys[1])
```

この読み取りは Redis スクリプト (`EVAL`) の一部として、`buffermgrdyn` が他テーブル変更をトリガーとして
`calculateHeadroomSize()` を実行する際に行われる。`LOSSLESS_TRAFFIC_PATTERN` の変更を直接 watch しているわけではない。

## 3. 変更の反映タイミング

`LOSSLESS_TRAFFIC_PATTERN` が変更されても、`buffermgrdyn` は直接 `doTask()` にエントリをキューしない。
実際に変更が反映されるのは、次の条件でヘッドルーム再計算がトリガーされた場合のみ:

| トリガーイベント | 発生テーブル | 結果 |
|----------------|------------|------|
| ポート速度/ケーブル長変更 | `CFG_PORT_TABLE_NAME` / `CFG_PORT_CABLE_LEN_TABLE_NAME` | 対象ポートのヘッドルーム再計算 |
| BUFFER_PG 変更 | `CFG_BUFFER_PG_TABLE_NAME` | 対象 PG のヘッドルーム再計算 |
| BUFFER_POOL 変更 | `CFG_BUFFER_POOL_TABLE_NAME` | 影響バッファプロファイル再計算 |
| DEFAULT_LOSSLESS_BUFFER_PARAMETER 変更 | `CFG_DEFAULT_LOSSLESS_BUFFER_PARAMETER` | 全ロスレスプロファイル再計算 |

つまり `LOSSLESS_TRAFFIC_PATTERN` 単体を書き換えても、上記テーブルへの変更がなければ
**新しい値はヘッドルーム計算に反映されない**。再計算を強制するには他テーブルの変更か
`buffermgrd` プロセス再起動が必要。

## 4. Producer / Consumer ペア

| 区間 | 方式 | 詳細 |
|------|------|------|
| CLI `config buffer ...` → CONFIG_DB | `ConfigDBConnector.set_entry()` | 直接 HSET（Pub/Sub なし） |
| CONFIG_DB → Lua (`buffer_headroom_*.lua`) | `redis.call('HGETALL', key)` | Lua スクリプト内で直接読み取り（keyspace 通知なし） |
| Lua → buffermgrdyn | `swss::runRedisScript()` 戻り値 | スクリプト実行結果の直接受け渡し |
| buffermgrdyn → APP_DB | `ProducerStateTable.set()` | APP_BUFFER_PROFILE_TABLE への書き込み（`PUBLISH` あり） |
| APP_DB → orchagent | `ConsumerStateTable` | keyspace 通知 + SET_COMMAND |

## 5. サマリ

| 観点 | 内容 |
|------|------|
| `buffermgrdyn` の Subscribe 方式 | `LOSSLESS_TRAFFIC_PATTERN` は `buffer_table_connectors` に含まれず、`SubscriberStateTable` は未登録 |
| keyspace 通知 | 未使用（書き手・読み手ともに PSUBSCRIBE/keyspace notification を使わない） |
| 実際の読み取り方式 | Lua スクリプト (`EVAL`) が実行時に `redis.call('KEYS', ...)` + `HGETALL` で直接読み取る |
| 変更の即時反映 | なし。他テーブルの変更がトリガーとなった場合のみ次回 Lua 実行時に読み取られる |
| ConsumerStateTable / ProducerStateTable | 未使用（このテーブル自体に対しては） |
| 書き手 | CLI (`config buffer lossless-traffic-pattern`) / db_migrator.py の直接 HSET |

## 6. Evidence

- `sonic-swss/cfgmgr/buffermgrd.cpp:174-186` — `buffer_table_connectors` に `LOSSLESS_TRAFFIC_PATTERN` が含まれないことを確認
- `sonic-swss/cfgmgr/buffer_headroom_mellanox.lua:91-96` — Lua 内 `redis.call('KEYS', 'LOSSLESS_TRAFFIC_PATTERN*')` + `HGETALL` 直接読み取り
- `sonic-swss/cfgmgr/buffer_headroom_barefoot.lua:80-84` — 同上（Barefoot 版）
- `sonic-swss/cfgmgr/buffermgrdyn.cpp:32` — `Orch(tables)` コンストラクタ（`tables` = `buffer_table_connectors`）
