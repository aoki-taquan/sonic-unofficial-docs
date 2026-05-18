# feature-state pubsub 調査メモ (Phase G)

## 対象ページ

`docs/reference/config-db/feature-state.md` — STATE_DB FEATURE テーブル

## 購読方式サマリ

- **書込み元**: `featured` / `container_startup.py` / `ctrmgrd.py` は直接 `swsscommon.Table.set()` / `_del()` で STATE_DB を更新
- **購読 API**: `featured` は CONFIG_DB `FEATURE` を `swsscommon.SubscriberStateTable` + `swsscommon.Select()` で購読
  - Redis Streams チャネルベース（`ConfigDBConnector.subscribe()` / keyspace 通知とは異なる）
- **APPL_DB 購読**: `featured` は APPL_DB `PORT_TABLE` も `SubscriberStateTable` で購読し、`PortInitDone` で delayed 機能を解除
- **consumer**: `show feature status` は STATE_DB を `HGETALL` でポーリング（Subscribe なし）

## コードロケーション

| コード | 行 | 内容 |
|--------|-----|------|
| `featured:601-603` | `cfg_db_conn` / `state_db_conn` / `appl_db_conn` の `DBConnector` 初期化 |
| `featured:612` | `swsscommon.Select()` 初期化 |
| `featured:626-634` | `subscribe()` — `SubscriberStateTable` 作成 + `selector.addSelectable()` |
| `featured:644-646` | CONFIG_DB `FEATURE` 購読登録 |
| `featured:647-648` | APPL_DB `PORT_TABLE` 購読登録 |
| `featured:656` | `selector.select(DEFAULT_SELECT_TIMEOUT)` イベントループ |
| `featured:674` | `subscriber.pop()` → `(key, op, fvs)` 取得 |
| `featured:585-590` | `set_feature_state()` → `Table.set()` で STATE_DB 書込み |
| `featured:607-609` | `RestartWaiter.waitAdvancedBootDone()` — warm/fast boot 待機 |
| `featured:169-184` | `handle_adv_boot()` / `port_listener()` — delayed 機能解除 |
| `show/feature.py:58-80` | STATE_DB `HGETALL` によるポーリング読み出し |

## 調査日

2026-05-18
