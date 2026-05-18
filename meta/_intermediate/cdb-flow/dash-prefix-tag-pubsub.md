# DASH_PREFIX_TAG_TABLE — Phase G pubsub research

## 調査対象

- `sonic-swss/orchagent/dash/dashaclorch.cpp`
- `sonic-swss/orchagent/dash/dashaclorch.h`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/orchagent/dash/dashtagmgr.cpp`

## 購読メカニズム

### 継承関係

`DashAclOrch` → `ZmqOrch` → `Orch`

`ZmqOrch` は ZMQ ソケット（PUSH/PULL）経由でメッセージを受信する Orch サブクラス。
`ORCH_NORTHBOND_DASH_ZMQ_ENABLED` フラグで ZMQ / Redis の切り替えが可能。

### テーブル登録 (orchdaemon.cpp:1371-1381)

```cpp
vector<string> dash_acl_tables = {
    APP_DASH_PREFIX_TAG_TABLE_NAME,
    APP_DASH_ACL_IN_TABLE_NAME,
    APP_DASH_ACL_OUT_TABLE_NAME,
    APP_DASH_ACL_GROUP_TABLE_NAME,
    APP_DASH_ACL_RULE_TABLE_NAME
};
DashAclOrch *dash_acl_orch = new DashAclOrch(m_dpu_appDb, dash_acl_tables, dash_orch, m_dpu_appstateDb, dash_zmq_server);
```

`DASH_PREFIX_TAG_TABLE` は `DPU_APPL_DB` を source DB とする。

### STATE_DB publish なし

`DashTagMgr` は `swsscommon::Table` / `StateTable` を保持しない。create/update/remove は
すべて `m_tag_table`（`unordered_map<string, DashTag>`）への書き込みのみ。
STATE_DB 応答は発生しない。

## 結論

- DASH_PREFIX_TAG_TABLE の書き込みは ZMQ 優先 (デフォルト) / Redis フォールバック の二系統
- SDN コントローラから orchagent への一方向フロー
- orchagent から外部への publish / notify は一切なし
