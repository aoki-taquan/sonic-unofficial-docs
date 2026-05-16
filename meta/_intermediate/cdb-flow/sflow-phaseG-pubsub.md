# SFLOW — Phase G 通信メカニズム 証跡

## 調査ソース

- `sonic-swss/cfgmgr/sflowmgr.cpp`
- `sonic-swss/orchagent/sfloworch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`

## CONFIG_DB Subscribe (sflowmgrd)

`SflowMgr::SflowMgr()` が `Orch(tableNames)` で以下のテーブルを Consumer 登録:

| テーブル | DB | 目的 |
|---|---|---|
| CFG_SFLOW_TABLE_NAME | CONFIG_DB | グローバル設定 (admin_state, polling_interval, agent_id, sample_direction) |
| CFG_SFLOW_SESSION_TABLE_NAME | CONFIG_DB | per-port セッション (admin_state, sample_rate, sample_direction) |
| CFG_PORT_TABLE_NAME | CONFIG_DB | ポート速度取得 (default sampling rate 算出) |
| STATE_PORT_TABLE_NAME | STATE_DB | oper_speed 変化監視 (オートネゴ時のレート自動更新) |

## hsflowd との通信

`sflowmgrd` は hsflowd とプロセス制御コマンドで通信（Redis Pub/Sub ではない）:

```cpp
// sflowmgr.cpp:51-78
void SflowMgr::sflowHandleService(bool enable)
{
    if (enable)  cmd << "service hsflowd restart";
    else         cmd << "service hsflowd stop";
    int ret = swss::exec(cmd.str(), res);
}
```

## APP_DB Publish (sflowmgrd → SflowOrch)

`sflowmgrd` は ProducerStateTable で APP_DB に書き込む:

```cpp
// sflowmgr.cpp:13-16
m_appSflowTable(appDb, APP_SFLOW_TABLE_NAME),
m_appSflowSessionTable(appDb, APP_SFLOW_SESSION_TABLE_NAME)
```

## SflowOrch 登録 (orchdaemon)

```cpp
// orchdaemon.cpp:439-444
vector<string> sflow_tables = {
    APP_SFLOW_TABLE_NAME,
    APP_SFLOW_SESSION_TABLE_NAME,
    APP_SFLOW_SAMPLE_RATE_TABLE_NAME
};
SflowOrch *sflow_orch = new SflowOrch(m_applDb, sflow_tables);
```

## SAI samplepacket_api 呼び出し (sfloworch.cpp)

| API | 条件 | 行 |
|---|---|---|
| `create_samplepacket()` | 新レートのセッション未存在 | sfloworch.cpp:29 |
| `remove_samplepacket()` | ref_count==0 | sfloworch.cpp:49 |
| `set_port_attribute(SAI_PORT_ATTR_INGRESS_SAMPLEPACKET_ENABLE)` | direction=rx or both | sfloworch.cpp:122 |
| `set_port_attribute(SAI_PORT_ATTR_EGRESS_SAMPLEPACKET_ENABLE)` | direction=tx or both | sfloworch.cpp:140 |

セッションは `m_sflowRateSampleMap` で ref_count 管理し、同レートを共有するポートがあればセッション再利用する。

## メッセージフロー

```
CONFIG_DB SFLOW|global (admin_state=up)
  └─ sflowmgrd
       ├─ APP_DB APP_SFLOW_TABLE         → SflowOrch.sflowStatusSet()
       ├─ APP_DB APP_SFLOW_SESSION_TABLE → SflowOrch.doTask()
       │    └─ sai_samplepacket_api->create_samplepacket()
       │    └─ sai_port_api->set_port_attribute(INGRESS/EGRESS)
       └─ service hsflowd restart  (UDP export to collector)
```
