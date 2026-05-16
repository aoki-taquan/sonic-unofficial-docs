# CONFIG_DB POLICER — 通信メカニズム (Phase G) 解析メモ

対象: CONFIG_DB の `POLICER` テーブルおよび `PORT_STORM_CONTROL` テーブル（スキーマ定数: `CFG_POLICER_TABLE_NAME` / `CFG_PORT_STORM_CONTROL_TABLE_NAME`、`sonic-swss-common/common/schema.h`）。

ソース確認:
- `sonic-swss/orchagent/policerorch.cpp` sha `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/orchagent/orch.cpp`
- `sonic-swss-common/common/subscriberstatetable.{h,cpp}`
- `sonic-swss-common/common/table.h`

## 1. 購読 API — `SubscriberStateTable` (keyspace 通知ベース)

`orchdaemon.cpp:396-402` で 2 テーブル分の `TableConnector` を生成して `PolicerOrch` に渡す:

```cpp
// orchdaemon.cpp:396-402
vector<TableConnector> policer_tables = {
    TableConnector(m_configDb, CFG_POLICER_TABLE_NAME),
    TableConnector(m_configDb, CFG_PORT_STORM_CONTROL_TABLE_NAME)
};
gPolicerOrch = new PolicerOrch(policer_tables, gPortsOrch);
```

`PolicerOrch::PolicerOrch(tableNames, portOrch)` は基底 `Orch(tableNames)` を呼び出す (`policerorch.cpp:116`)。`Orch` コンストラクタが各 TableConnector に `addConsumer()` を実行し、CONFIG_DB は **`SubscriberStateTable`** ブランチを選択する (`orch.cpp:1186-1196`)。

`SubscriberStateTable` は Redis keyspace 通知 (`__keyspace@<dbId>__:POLICER|*` への `PSUBSCRIBE`) を購読し、通知受信後に `HGETALL` で実データを再取得してから `pops()` で `(key, op, fvs)` タプル列を返す。バッチサイズは `DEFAULT_POP_BATCH_SIZE = 128`（`table.h:164`）。

## 2. 書き込み側 (publisher)

CONFIG_DB `POLICER` への書き込みは CLI (`config policer` / `acl_loader`) または `sonic-cfggen` が `HSET` を発行することで行われる。明示的な `PUBLISH` チャンネルへの投稿はなく、Redis の `notify-keyspace-events` 設定（CONFIG_DB は `Kxxx` 相当）が `__keyspace@<dbId>__:POLICER|<name>` イベントを自動発火する。

## 3. 購読側ディスパッチ

`OrchDaemon` メインループ (`orchdaemon.cpp:959`) が `m_select->select(&s, 1000ms)` で待機し、`SubscriberStateTable` の fd ready で wake する。`Consumer::execute()` がポップして `PolicerOrch::doTask(Consumer&)` を呼ぶ。

`doTask()` 冒頭 (`policerorch.cpp:379-382`) で `allPortsReady()` チェック。false の間は即 return（キュー保持）。

テーブル名による最初の分岐 (`policerorch.cpp:394-407`):

```cpp
if (table_name == CFG_PORT_STORM_CONTROL_TABLE_NAME)
    storm_status = handlePortStormControlTable(tuple);
```

`POLICER` テーブルは else 側（暗黙）で SET / DEL ハンドリングへ進む。

## 4. SAI policer_api 呼び出し経路

| 操作 | SAI 呼び出し | コード箇所 |
|------|------------|----------|
| POLICER SET (新規 create) | `sai_policer_api->create_policer()` | `policerorch.cpp:498-508` |
| POLICER SET (update) | `sai_policer_api->set_policer_attribute()` (CIR/CBS/PIR/PBS のみ) | `policerorch.cpp:535-546` |
| POLICER DEL | `sai_policer_api->remove_policer()` | `policerorch.cpp:573-581` |
| PORT_STORM_CONTROL SET | `create_policer()` + `sai_port_api->set_port_attribute()` | `policerorch.cpp:200-313` |
| PORT_STORM_CONTROL DEL | `remove_policer()` + `sai_port_api->set_port_attribute(0)` | `policerorch.cpp:316-360` |

APP_DB / STATE_DB への書き込みは一切行わない。

## 5. Observer パターン (参照カウント)

GoF Observer ではなく参照カウント方式。PolicerOrch が OID map と refcount map の両方を保有し、他 Orch が直接メソッドを呼ぶ:

```cpp
// m_syncdPolicers: map<string, sai_object_id_t>
// m_policerRefCounts: map<string, int>

bool PolicerOrch::increaseRefCount(const string &name); // MirrorOrch が呼ぶ
bool PolicerOrch::decreaseRefCount(const string &name); // MirrorOrch が呼ぶ
bool PolicerOrch::policerExists(const string &name);    // MirrorOrch, AclOrch が呼ぶ
bool PolicerOrch::getPolicerOid(const string &name, sai_object_id_t &oid); // 同上
```

`m_policerRefCounts[key] > 0` のまま DEL が来ると `SWSS_LOG_INFO` のみで `it++` 保留（永続保留; エラーにならない）。参照テーブル（MIRROR_SESSION 等）を先に DEL することで refcount が 0 に戻り、次の select wake で POLICER DEL が処理される。

## 6. Retry 機構

| 返値 | 処理 |
|-----|------|
| `task_success` / `task_failed` | `erase(it)` でキュー除去 |
| `task_need_retry` | `it++` でキュー保持、次 wake で再試行 |

SAI create / set / remove 失敗時は `handleSaiCreateStatus` / `handleSaiSetStatus` / `handleSaiRemoveStatus` が判定。`SAI_STATUS_SUCCESS` 以外で `task_need_retry` が返ると次ループで再実行される。

## まとめ

- 通知方式: Redis **keyspace 通知** + `HGETALL` 再取得 (`SubscriberStateTable`)
- APP_DB への中継なし (CONFIG_DB → SAI 直結)
- Observer: 参照カウント + プロセス内直接呼び出し（DB 非経由）
- Retry: `task_need_retry` によるキュー保持型
