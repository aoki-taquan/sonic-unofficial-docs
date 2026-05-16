# tunnel-decap-table Phase G: 通信メカニズム (pubsub)

## 対象ページ
`docs/reference/config-db/tunnel-decap-table.md`

## ソース
- `sonic-net/sonic-swss`: `orchagent/tunneldecaporch.cpp`
- `sonic-net/sonic-swss`: `orchagent/orchdaemon.cpp`

## 抽出結果

### Consumer 登録パターン

`orchdaemon.cpp` で `TunnelDecapOrch` を初期化:
```cpp
vector<string> tunnel_tables = {
    APP_TUNNEL_DECAP_TABLE_NAME,       // APPL_DB: "TUNNEL_DECAP_TABLE"
    APP_TUNNEL_DECAP_TERM_TABLE_NAME   // APPL_DB: "TUNNEL_DECAP_TERM_TABLE"
};
gTunneldecapOrch = new TunnelDecapOrch(m_applDb, m_stateDb, m_configDb, tunnel_tables);
```

`Orch(appDb, tableNames)` 基底クラスが各テーブルを Consumer として自動登録。

### CONFIG_DB 直接購読 (SubscriberStateTable)

コンストラクタ内で `CFG_SUBNET_DECAP_TABLE_NAME` を CONFIG_DB から明示的に購読:
```cpp
auto cfgSubnetDecapSubTable = new SubscriberStateTable(
    configDb, CFG_SUBNET_DECAP_TABLE_NAME,
    TableConsumable::DEFAULT_POP_BATCH_SIZE, 0);
Orch::addExecutor(new Consumer(cfgSubnetDecapSubTable, this, CFG_SUBNET_DECAP_TABLE_NAME));
```

### Observer パターン / doTask ディスパッチ

`doTask(Consumer &consumer)` でテーブル名によって分岐:

| テーブル | ハンドラ |
|---|---|
| `APP_TUNNEL_DECAP_TABLE_NAME` | `doDecapTunnelTask()` |
| `APP_TUNNEL_DECAP_TERM_TABLE_NAME` | `doDecapTunnelTermTask()` |
| `CFG_SUBNET_DECAP_TABLE_NAME` | `doSubnetDecapTask()` |

### SAI tunnel_api 呼び出し

APPL_DB 中間書き込みなし。orchagent → SAI 直接経路。

| SAI 関数 | 用途 |
|---|---|
| `create_tunnel()` | IP-in-IP トンネルオブジェクト生成 |
| `remove_tunnel()` | トンネル削除 |
| `create_tunnel_term_table_entry()` | P2P/P2MP decap term 登録 |
| `remove_tunnel_term_table_entry()` | decap term 削除 |
| `set_tunnel_attribute()` | QoS マップ等の属性更新 |

### STATE_DB 書き込み

SAI 操作後に `stateTunnelDecapTable` / `stateTunnelDecapTermTable` へ状態ミラー書き込み。他 Orch への通知なし。

## 適用ブロック
`<!-- pubsub -->` ... `<!-- /pubsub -->` として `tunnel-decap-table.md` 末尾（`<!-- glossary-links-injected -->` の直前）に追加済み。
