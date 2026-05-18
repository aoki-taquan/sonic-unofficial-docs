# SYSLOG_CONFIG 通信メカニズム調査メモ (Phase G)

ソース: `sonic-host-services/scripts/hostcfgd` (c5bbbe8b07b96f078fa4b761316627404b01bd04)

## 購読方式の確認

### subscribe 登録箇所

```
L2499-2503:
    # Handle SYSLOG_CONFIG and SYSLOG_SERVER changes
    self.config_db.subscribe(swsscommon.CFG_SYSLOG_CONFIG_TABLE_NAME,
                             make_callback(self.rsyslog_config_handler))
    self.config_db.subscribe(swsscommon.CFG_SYSLOG_SERVER_TABLE_NAME,
                             make_callback(self.rsyslog_server_handler))
```

- `ConfigDBConnector.subscribe()` を使用 → Redis keyspace 通知 (PSUBSCRIBE)
- `SubscriberStateTable` / `ConsumerStateTable` は非使用

### 起動時スナップショット

```
L2250-2251:
    syslog_cfg = init_data.get(swsscommon.CFG_SYSLOG_CONFIG_TABLE_NAME, {})
    syslog_srv = init_data.get(swsscommon.CFG_SYSLOG_SERVER_TABLE_NAME, {})
...
L2269:
    self.rsyslogcfg.load(syslog_cfg, syslog_srv)
```

`config_db.listen(init_data_handler=self.load)` (L2528) で Subscribe 開始前に全テーブルをスナップショット取得し `RSyslogCfg.load()` で初期化。

### ハンドラチェーン

```
rsyslog_config_handler(key, op, data)  [L2421-2423]
    → rsyslog_handler()  [L2410-2415]
        → get_table(CFG_SYSLOG_CONFIG_TABLE_NAME)
        → get_table(CFG_SYSLOG_SERVER_TABLE_NAME)
        → RSyslogCfg.update_rsyslog_config(config, servers)  [L1715-1743]
            → キャッシュ比較
            → systemctl reset-failed rsyslog-config rsyslog  [L1732-1733]
            → systemctl restart rsyslog-config  [L1734]
```

### 他プロセスの購読

grep 調査: SYSLOG_CONFIG を購読する他プロセスなし。
rsyslogd は /etc/rsyslog.conf を直接読み、Redis を購読しない。

## 結論

- 通信方式: ConfigDBConnector.subscribe() / Redis keyspace 通知
- 購読者: hostcfgd のみ (RSyslogCfg クラス)
- 起動時: init_data_handler でスナップショット適用
- 変更時: 両テーブルまとめて再取得 → キャッシュ比較 → rsyslog-config 再起動
