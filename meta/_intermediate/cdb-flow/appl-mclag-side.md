# APPL_DB MCLAG/ICCP — Phase F: 副次 DB 書込スキャン中間ファイル

生成日: 2026-05-15 (Task F Phase F / cdb_q67_f)

## 調査対象

`docs/reference/config-db/appl-mclag.md` で扱う APPL_DB MCLAG/ICCP テーブル群
(`MCLAG_FDB_TABLE` / `ISOLATION_GROUP_TABLE` / `ACL_TABLE_TABLE` / `ACL_RULE_TABLE` /
`LAG_TABLE` / `PORT_TABLE` / `INTF_TABLE`) の書込主体 `mclagsyncd` および補助デーモン
`iccpd` が、本来の APPL_DB 書込に **副次して** STATE_DB / COUNTERS_DB / その他副次 DB
へ書き込みを行うかどうか。

## 走査範囲

- `.cache/sonic-sources/sonic-swss/mclagsyncd/` (主購読者 `MclagLink` クラス)
- `.cache/sonic-sources/sonic-buildimage/src/iccpd/src/` (補助プロセス `iccpd`)
- `.cache/sonic-sources/sonic-swss/orchagent/` 内の MCLAG 関連 orch
  (`fdborch`, `isolationgrouporch`) — APPL_DB 経由の連鎖書込確認用

## 走査コマンドと結果

### 1. `mclagsyncd` 内の副次 DB アクセス

```bash
grep -n -E "STATE_DB|COUNTERS_DB|state_db|counters_db" \
  .cache/sonic-sources/sonic-swss/mclagsyncd/mclaglink.cpp \
  .cache/sonic-sources/sonic-swss/mclagsyncd/mclaglink.h
```

主な検出箇所:

- `mclaglink.h:218` `unique_ptr<DBConnector> p_state_db;` — STATE_DB 接続あり
- `mclaglink.h:222` `unique_ptr<DBConnector> p_counters_db;` — COUNTERS_DB 接続あり
- `mclaglink.cpp:1794` `p_state_db    = DBConnector("STATE_DB", 0);`
- `mclaglink.cpp:1798` `p_counters_db = DBConnector("COUNTERS_DB", 0);`
- `mclaglink.cpp:1799` `p_notificationsDb = DBConnector("STATE_DB", 0);`
- `mclaglink.cpp:1805-1807` `Table(p_state_db.get(), STATE_MCLAG_TABLE_NAME / STATE_MCLAG_LOCAL_INTF_TABLE_NAME / STATE_MCLAG_REMOTE_INTF_TABLE_NAME)`

### 2. STATE_DB への実際の書込呼出

```bash
grep -n -E "p_mclag_tbl|p_mclag_local_intf_tbl|p_mclag_remote_intf_tbl" \
  .cache/sonic-sources/sonic-swss/mclagsyncd/mclaglink.cpp
```

検出結果 (set / del 呼出):

| 行 | テーブル | 操作 | 用途 |
|---|---|---|---|
| L1357, L1412, L1460, L1733 | `STATE_MCLAG_TABLE` | `set(mlag_id, ...)` | `oper_status` / `role` / `system_mac` / `domain` 書込 |
| L1503 | `STATE_MCLAG_TABLE` | `del(mlag_id)` | ICCP 情報削除 |
| L1520 | `STATE_MCLAG_LOCAL_INTF_TABLE` | `set(if, port_isolate_peer_link)` | ローカル IF のピアリンク分離状態 |
| L1533 | `STATE_MCLAG_LOCAL_INTF_TABLE` | `del(if)` | ローカル IF エントリ削除 |
| L1584 | `STATE_MCLAG_REMOTE_INTF_TABLE` | `set("<id>\|<if>", oper_status)` | リモート IF の oper 状態 |
| L1633 | `STATE_MCLAG_REMOTE_INTF_TABLE` | `del("<id>\|<if>")` | リモート IF エントリ削除 |

### 3. COUNTERS_DB 利用

```bash
grep -n "p_counters_db" .cache/sonic-sources/sonic-swss/mclagsyncd/mclaglink.cpp
```

検出:

- `mclaglink.cpp:66` `auto hash = p_counters_db->hgetall("COUNTERS_PORT_NAME_MAP");`

`hgetall` は **読取専用**。`COUNTERS_PORT_NAME_MAP` はオブジェクト OID 解決のために
読み出すのみで、`mclagsyncd` から COUNTERS_DB への書込は **0 件**。

### 4. NotificationProducer / FLUSHFDBREQUEST

```bash
grep -n -E "NotificationProducer|notifications" \
  .cache/sonic-sources/sonic-swss/mclagsyncd/mclaglink.cpp
```

- `mclaglink.cpp:423` `swss::NotificationProducer flushFdb(p_appl_db.get(), "FLUSHFDBREQUEST");`

宛先は `p_appl_db` (APPL_DB)。STATE_DB / COUNTERS_DB への notification 発行は無し
(`p_notificationsDb` は宣言されているが、`mclaglink.cpp` 全体に `*p_notificationsDb`
や `Producer*(p_notificationsDb` を用いた書込呼出は出現しない)。

### 5. `iccpd` 側の DB 書込

```bash
grep -n -E "STATE_DB|COUNTERS_DB|ASIC_DB|LOGLEVEL_DB|FLEX_COUNTER_DB" \
  .cache/sonic-sources/sonic-buildimage/src/iccpd/src/*.c \
  .cache/sonic-sources/sonic-buildimage/src/iccpd/include/*.h
```

検出ヒットはすべてコメント (`/* Remove ICCP info from STATE_DB */` 等) で、実体は
すべて `mclagsyncd` への IPC メッセージ送信に置き換わっている。`iccpd` 自身からの
Redis 直書きは存在しない。

### 6. orchagent 側 (APPL_DB 連鎖の確認)

```bash
grep -rln "MCLAG_FDB_TABLE\|ISOLATION_GROUP_TABLE" \
  .cache/sonic-sources/sonic-swss/orchagent/
```

- `fdborch.cpp` (L724 `APP_MCLAG_FDB_TABLE_NAME` を参照)
- `isolationgrouporch.cpp`
- `orchdaemon.cpp` (初期化登録のみ)

これらは APPL_DB 消費側であり、書込先は SAI 経由の ASIC_DB のみ。STATE_DB /
COUNTERS_DB への **副次** 書込は MCLAG 経路に紐づくものは見つからない
(`isolationgrouporch.cpp` 内 `state_db` / `counters_db` の参照 0 件)。

## 結論

APPL_DB MCLAG/ICCP 関連テーブル書込に伴う副次 DB 書込は以下の通り:

| 副次 DB | 書込有無 | 対象テーブル | 根拠 |
|---|---|---|---|
| STATE_DB | **あり** | `MCLAG_TABLE` / `MCLAG_LOCAL_INTF_TABLE` / `MCLAG_REMOTE_INTF_TABLE` | `mclaglink.cpp` L1357/1412/1460/1503/1520/1533/1584/1633/1733 |
| COUNTERS_DB | なし (読取のみ) | — | `p_counters_db->hgetall(...)` (`mclaglink.cpp:66`) のみで書込呼出 0 件 |
| ASIC_DB | なし (直接) | — | `mclagsyncd` から SAI 呼出なし。`fdborch`/`isolationgrouporch` 経由で APPL_DB から間接書込 |
| FLEX_COUNTER_DB / LOGLEVEL_DB | なし | — | 参照 0 件 |
| `iccpd` 経由 | なし | — | iccpd は IPC のみ。Redis 直書きコード無し |

STATE_DB 側書込は本ページ本文 L54 で「`mclagsyncd` が直接行う」と既に言及済み
だが、Phase F としては副次 DB 書込を明示するブロックを追加し、消費者である
`mclagcli` / `mclagdctl` (show mclag ...) が STATE_DB を読みに行く経路を示す。
