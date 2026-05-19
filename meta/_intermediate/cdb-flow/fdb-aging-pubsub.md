# fdb-aging Phase G (pubsub) 調査メモ

## 調査対象
- `sonic-swss/orchagent/switchorch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-buildimage/dockers/docker-orchagent/swssconfig.sh`

## 通信経路の特殊性

`fdb_aging_time` は CONFIG_DB ではなく APPL_DB にのみ存在する。
- 書き込み元: `swssconfig switch.json` (switch.json.j2 展開後)
- 購読先: `SwitchOrch` (Orch 基底クラスの ConsumerStateTable)

## 購読方式

### SwitchOrch のコンストラクタ引数 (orchdaemon.cpp:197-213)
```cpp
TableConnector app_switch_table(m_applDb, APP_SWITCH_TABLE_NAME);
// ...
vector<TableConnector> switch_tables = {
    conf_switch_hash,
    conf_switch_trim,
    conf_switch_fast_linkup,
    conf_asic_sensors,
    conf_suppress_asic_sdk_health_categories,
    app_switch_table  // ← APPL_DB SWITCH_TABLE
};
gSwitchOrch = new SwitchOrch(m_applDb, switch_tables, stateDbSwitchTable);
```

`Orch(connectors)` は各 `TableConnector` に対して `ConsumerStateTable` を生成。
Redis keyspace notification で APPL_DB SWITCH_TABLE 変化を受け取る。

### warm-reboot パス (orchdaemon.cpp:1068)
`gSwitchOrch->setAgingFDB(0)` は APPL_DB を経由せず直接 SAI を呼ぶ。
keyspace notification なし。

## 2 段構成の有無
なし。`fdb_aging_time` は CONFIG_DB に存在しないため fabricmgrd のような中継デーモン不要。

## 設定反映レイテンシ
- swssconfig → SwitchOrch: Select ループ (最大 1 秒 + swssconfig.sh の sleep 1)
- warm-reboot setAgingFDB(0): 即時 (直接 SAI 呼び出し)
