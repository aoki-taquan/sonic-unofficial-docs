# nat-app Phase G — 通信メカニズム (pubsub) 調査メモ

## 対象ページ
`docs/reference/config-db/nat-app.md`

## 購読方式

- `NatOrch` は `orchdaemon.cpp:454-465` で 6 テーブルを `ConsumerStateTable` (channel ベース) で登録。
- DB ID が APPL_DB (= 0) のため `orch.cpp:1186-1196` の分岐で `ConsumerStateTable` が選ばれる。

## テーブル別優先度 (natorch_base_pri = 50)

| テーブル | 優先度 |
|---|---|
| APP_NAT_DNAT_POOL_TABLE_NAME | 55 |
| APP_NAT_TABLE_NAME | 54 |
| APP_NAPT_TABLE_NAME | 53 |
| APP_NAT_TWICE_TABLE_NAME | 52 |
| APP_NAPT_TWICE_TABLE_NAME | 51 |
| APP_NAT_GLOBAL_TABLE_NAME | 50 |

## SETTIMEOUTNAT 通知

- `natorch.cpp:137`: `NotificationProducer(appDb, "SETTIMEOUTNAT")` を生成。
- aging 系関数 (`natorch.cpp:1888, 2002, 2118, 2287, 3336-3501`) から `PUBLISH`。
- `natmgrd.cpp:149`: `NotificationConsumer(&appDb, "SETTIMEOUTNAT")` で受信 → `natmgr->timeoutNotifications(op, data)` → conntrack エントリ削除 → APPL_DB DEL。

## バッチサイズ

- `main.cpp:459`: `gBatchSize = DEFAULT_BATCH_SIZE = 128`。
- `-b <n>` オプション (`main.cpp:478`) で変更可能。

## 書き込み側

- `natmgrd` (natmgr.cpp): `ProducerStateTable::set()` / `del()`。
- `natsyncd` (natsync.cpp): `ProducerStateTable::set()` / `del()`。

## doTask ディスパッチ

`natorch.cpp:3041-3084` で `table_name` に基づき 6 関数に分岐。
