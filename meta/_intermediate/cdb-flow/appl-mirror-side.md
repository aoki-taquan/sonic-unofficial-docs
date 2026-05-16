# APPL_DB FIXED_MIRROR_SESSION_TABLE 副次 DB 書込スキャン (Phase F)

スコープ: `sonic-net/sonic-swss @ 4305596156d70e9797e8a881b3d19b46de0bce0d`

対象 SET / DEL ハンドラ:

- `orchagent/p4orch/mirror_session_manager.cpp` (P4RT / APPL_DB 経路)
- 対比対象として `orchagent/mirrororch.cpp` (CONFIG_DB 経路 `MirrorOrch`)

## 1. P4RT 経路 (APPL_DB FIXED_MIRROR_SESSION_TABLE) — 実際の副次書込

### 1.1 APPL_STATE_DB への応答 publish (`ResponsePublisher`)

`MirrorSessionManager` は STATE_DB / COUNTERS_DB / FLEX_COUNTER_DB を**直接書込まない**。
唯一の副次書込は **`P4Orch::m_publisher` (`ResponsePublisher`) による APPL_STATE_DB 上の応答テーブル**である。

```cpp
// orchagent/p4orch/p4orch.cpp:38-43 (constructor)
m_publisher("APPL_DB", /*bool buffered=*/true,
            /*db_write_thread=*/true, zmqServer)
```

```cpp
// orchagent/p4orch/mirror_session_manager.cpp:82
m_publisher->publish(APP_P4RT_TABLE_NAME, kfvKey(key_op_fvs_tuple),
                     kfvFieldsValues(key_op_fvs_tuple), status,
                     /*replace=*/true);
// orchagent/p4orch/mirror_session_manager.cpp:111
m_publisher->publish(APP_P4RT_TABLE_NAME, kfvKey(key_op_fvs_tuple),
                     kfvFieldsValues(key_op_fvs_tuple), status,
                     /*replace=*/true);
```

`ResponsePublisher` の宛先は **`APPL_STATE_DB`** のレスポンステーブルで、processAddRequest / processUpdateRequest / processDeleteRequest の結果ステータスを P4RT クライアント向けに書き戻す。
APPL_DB の元エントリ書込みではなく、別 DB（APPL_STATE_DB）への副次効果である。

- key: 元 APPL_DB key と同じ (`kfvKey(key_op_fvs_tuple)`)
- value: `ReturnCode` (status_code + メッセージ)
- ZMQ buffered フラッシュで非同期送出

### 1.2 STATE_DB は対象外

`MirrorSessionManager` クラスのメンバには `Table m_stateTable` / `m_countersTable` / FlexCounterManager 等が**一切存在しない**。
`mirror_session_manager.h` (~80 行) と `mirror_session_manager.cpp` (~600 行) 全体にわたって STATE_DB / COUNTERS_DB / FLEX_COUNTER_DB への DBConnector / Table 宣言は無い。

CONFIG_DB 経路 `MirrorOrch` が書く `STATE_DB|MIRROR_SESSION_TABLE` (status = "active"/"inactive") は P4RT 経路では発火しない。
P4RT クライアントは APPL_STATE_DB の応答経由でセッション作成成否を確認する設計。

### 1.3 COUNTERS_DB / FLEX_COUNTER_DB は対象外

`MirrorSessionManager` は mirror session 単位のカウンタを SAI から取得せず、FLEX_COUNTER_GROUP の登録も行わない。
ACL 連携経由 (`AclRuleManager` の mirror action) でルールカウンタは ACL_COUNTER 側に登録されるが、これは `FIXED_MIRROR_SESSION_TABLE` の副次効果ではなく `ACL_*_TABLE` 側の Phase F 範疇。

### 1.4 SAI MIRROR_SESSION 作成 (P4 OID マッパ更新)

副次 DB 書込ではないが、ハンドラは以下のインメモリ副作用を伴う:

- `m_p4OidMapper->setOID(SAI_OBJECT_TYPE_MIRROR_SESSION, key, oid)` — P4Orch 内 OID マッパへの登録
- `gPortsOrch->increasePortRefCount(port)` — PortsOrch ref count 増加 (UPDATE 時は old を decrease → new を increase)

これらは DB 副次書込みではなくプロセス内データ構造の更新。

## 2. CONFIG_DB 経路 (`MirrorOrch`) との対比 (参考)

CONFIG_DB 経路は対照的に **`STATE_DB MIRROR_SESSION_TABLE`** へ active/inactive status を書込む:

- `MirrorOrch::setSessionState()` (`orchagent/mirrororch.cpp` 周辺) が `STATE_DB|MIRROR_SESSION_TABLE|<name>` の `status` フィールドを `"active"` / `"inactive"` で更新
- セッションの実 activate (next hop 解決成功 → SAI create_mirror_session 完了) で `"active"`、解決不能なら `"inactive"`
- COUNTERS_DB / FLEX_COUNTER_DB への mirror session 単位の書込みは CONFIG_DB 経路でも発火しない (ASIC 側 mirror counter は ACL 経路に紐づくため)

両経路の差異:

| 副次 DB | CONFIG_DB MIRROR_SESSION | APPL_DB FIXED_MIRROR_SESSION_TABLE |
|---|---|---|
| STATE_DB MIRROR_SESSION_TABLE | `status` を `"active"`/`"inactive"` で更新 | 書込みなし |
| APPL_STATE_DB レスポンス | 書込みなし | `ResponsePublisher` で ReturnCode を publish |
| COUNTERS_DB / FLEX_COUNTER_DB | 書込みなし (session 単位カウンタなし) | 書込みなし |

## 3. まとめ

`APPL_DB FIXED_MIRROR_SESSION_TABLE` の SET / DEL に伴う副次 DB 書込は次の 1 経路のみ:

1. **APPL_STATE_DB レスポンス**: `ResponsePublisher` が ZMQ + buffered 書込で `ReturnCode` を返却 (`mirror_session_manager.cpp:82, 111`)

STATE_DB / COUNTERS_DB / FLEX_COUNTER_DB への直接書込みは行われない。
CONFIG_DB 経路の `MirrorOrch` が書く `STATE_DB MIRROR_SESSION_TABLE.status` 相当の状態確認は、P4RT クライアント側で APPL_STATE_DB の応答を見る形になる。

## 引用元

- `orchagent/p4orch/p4orch.cpp:36-43` — `m_publisher("APPL_DB", buffered=true, db_write_thread=true, zmqServer)` 宣言
- `orchagent/p4orch/mirror_session_manager.cpp:82, 111` — `m_publisher->publish(...)` 呼出 2 箇所
- `orchagent/p4orch/mirror_session_manager.h` 全体 — STATE_DB / COUNTERS_DB Table メンバ不在
- `orchagent/mirrororch.cpp` — CONFIG_DB 側 `MirrorOrch` の `STATE_DB MIRROR_SESSION_TABLE.status` 書込 (対比参考)
