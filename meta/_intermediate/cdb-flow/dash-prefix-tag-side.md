# DASH_PREFIX_TAG_TABLE — Phase F 副次 DB 書込スキャン中間ファイル

調査日: 2026-05-17
対象テーブル: APP_DB `DASH_PREFIX_TAG_TABLE`

## 調査対象ファイル

- `sonic-swss/orchagent/dash/dashtagmgr.cpp` — タグ CRUD (create/update/remove/attach/detach)
- `sonic-swss/orchagent/dash/dashaclorch.cpp` — taskUpdateDashPrefixTag / taskRemoveDashPrefixTag
- `sonic-swss/orchagent/dash/dashaclgroupmgr.cpp` — ACL group/rule 管理 (CRM 連携あり)

## 走査範囲・方針

`DASH_PREFIX_TAG_TABLE` のエントリが SET / DEL されたときに、主購読者 (`DashAclOrch` / `DashTagMgr`) が APPL_DB / STATE_DB / COUNTERS_DB / FLEX_COUNTER_DB 等の **副次 DB** へ書き込みを行うか調査。SAI への書き込みは "主作用" であり対象外。

## 走査コマンドと結果

### 1. dashtagmgr.cpp — DB 書込呼出の確認

`create()` / `update()` / `remove()` / `attach()` / `detach()` 全体を精読:

- いずれも `m_tag_table` (orchagent 内部 `unordered_map`) の更新のみ
- `swsscommon::Table`、`swsscommon::ProducerStateTable`、`swsscommon::NotificationProducer` の使用なし
- DB connector (`DBConnector`) の保持なし

**結果: DB 書込 0 件**

### 2. dashaclorch.cpp — app_state_db 利用の確認

コンストラクタ引数に `DBConnector *app_state_db` が存在 (`dashaclorch.cpp:77`) するが、
コンストラクタ本体での利用なし:

```cpp
DashAclOrch::DashAclOrch(DBConnector *db, const vector<string> &tables,
    DashOrch *dash_orch, DBConnector *app_state_db, ZmqServer *zmqServer) :
    ZmqOrch(db, tables, zmqServer),
    m_dash_orch(dash_orch),
    m_group_mgr(db, dash_orch, this),
    m_tag_mgr(this)
```

`app_state_db` は引数として受け取るが初期化リストで渡されないため、`DashAclOrch` は STATE_DB を保持しない。

**DASH_PREFIX_TAG に関連する STATE_DB 書込: 0 件**

### 3. dashaclgroupmgr.cpp — CRM カウンタ更新の確認

`gCrmOrch->incCrmDashAclUsedCounter()` / `decCrmDashAclUsedCounter()` が呼ばれるが、
これは **ACL group 作成/削除時** および **ACL rule 作成時** に限定される:

- `dashaclgroupmgr.cpp:175-176` — ACL group 作成時に `CRM_DASH_IPV4/IPV6_ACL_GROUP` をインクリメント
- `dashaclgroupmgr.cpp:213-216` — ACL group 削除時にデクリメント
- `dashaclgroupmgr.cpp:374-376` — ACL rule 作成時に `CRM_DASH_IPV4/IPV6_ACL_RULE` をインクリメント

**`DASH_PREFIX_TAG_TABLE` の SET/DEL に直接対応する CRM 更新は存在しない**。タグ自体は SAI オブジェクトを作成せず orchagent 内メモリにのみ保持されるため、CRM 追跡対象外。

### 4. sonic-swss 全体での DASH_PREFIX_TAG 関連 StateDB 参照

```
grep -rn "DASH_PREFIX_TAG\|DashTagMgr\|DashTag" sonic-swss/ | grep -E "state_db|STATE_DB|StateTable|ProducerState"
```

**マッチ 0 件**

## 結論

`DASH_PREFIX_TAG_TABLE` の SET / DEL に伴う副次 DB 書き込みは **存在しない**。

- タグは orchagent 内の `m_tag_table` (`unordered_map`) にのみ保持される SAI 非経由オブジェクト
- APPL_DB / STATE_DB / COUNTERS_DB / FLEX_COUNTER_DB いずれへの書込なし
- CRM カウンタ更新は ACL group / rule レイヤで発生し、タグレイヤでは発生しない

| 副次 DB | 書込有無 | 根拠 |
|---|---|---|
| APPL_DB | なし | `DashTagMgr` / `DashAclOrch` 内に Producer / Table の書込呼出が 0 件 |
| STATE_DB | なし | `app_state_db` 引数は `DashAclOrch` に渡されるが `DashTagMgr` パスでは未使用 |
| COUNTERS_DB | なし | DASH タグは SAI オブジェクト非作成、カウンタテーブルなし |
| ASIC_DB (CRM) | なし | CRM 更新は ACL group / rule のみ。タグは CRM 追跡対象外 |
| FLEX_COUNTER_DB | なし | DASH タグに対応する flex-counter エントリなし |
