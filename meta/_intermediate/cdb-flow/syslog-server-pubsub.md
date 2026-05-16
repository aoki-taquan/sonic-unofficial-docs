# SYSLOG_SERVER テーブル — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `SYSLOG_SERVER` テーブル。
ソース: `sonic-host-services/scripts/hostcfgd`, `sonic-buildimage/files/image_config/rsyslog/rsyslog-config.sh`

## 1. 購読 API — `ConfigDBConnector.subscribe()` (keyspace 通知ベース)

`hostcfgd` は `swsscommon.ConfigDBConnector` の `subscribe(table, callback)` で SYSLOG_SERVER への変更を購読する。

```python
# sonic-host-services/scripts/hostcfgd L2499-2503
# Handle SYSLOG_CONFIG and SYSLOG_SERVER changes
self.config_db.subscribe(swsscommon.CFG_SYSLOG_CONFIG_TABLE_NAME,
                         make_callback(self.rsyslog_config_handler))
self.config_db.subscribe(swsscommon.CFG_SYSLOG_SERVER_TABLE_NAME,
                         make_callback(self.rsyslog_server_handler))
```

- `ConfigDBConnector.listen()` が内部で Redis の **keyspace 通知** (`__keyspace@4__:SYSLOG_SERVER|*` への PSUBSCRIBE) を購読し、テーブル名にマッチしたコールバックへディスパッチする。
- channel ベースの `PUBLISH/SUBSCRIBE` (`ConsumerStateTable` 形式) は使用していない。
- `SYSLOG_SERVER` と `SYSLOG_CONFIG` は **独立した subscribe** で登録されるが、両ハンドラとも同じ `rsyslog_handler()` を呼ぶ（両テーブル一括再取得→rsyslog-config 再起動）。

## 2. キー単位ディスパッチ

```python
# hostcfgd L2456-2466
def make_callback(func):
    def callback(table, key, data):
        if data is None:
            op = "DEL"
            data = {}
        else:
            op = "SET"
        return func(key, op, data)
    return callback
```

- `key`: `SYSLOG_SERVER|<server_address>` の右辺（例: `"192.168.1.1"`）
- `op`: `data is None` の場合 `DEL`、それ以外 `SET`
- `data`: keyspace 通知後に hostcfgd が **HGETALL で再取得した** dict

## 3. ハンドラ動作フロー

```python
# hostcfgd L2417-2423
def rsyslog_server_handler(self, key, op, data):
    syslog.syslog(syslog.LOG_INFO, 'SYSLOG_SERVER table handler...')
    self.rsyslog_handler()

def rsyslog_config_handler(self, key, op, data):
    syslog.syslog(syslog.LOG_INFO, 'SYSLOG_CONFIG table handler...')
    self.rsyslog_handler()

# hostcfgd L2410-2415
def rsyslog_handler(self):
    rsyslog_config = self.config_db.get_table(
        swsscommon.CFG_SYSLOG_CONFIG_TABLE_NAME)
    rsyslog_servers = self.config_db.get_table(
        swsscommon.CFG_SYSLOG_SERVER_TABLE_NAME)
    self.rsyslogcfg.update_rsyslog_config(rsyslog_config, rsyslog_servers)
```

- どちらのハンドラも `rsyslog_handler()` を呼び、**両テーブルをまとめて再取得** してからキャッシュと比較する。
- キャッシュ比較で変化があれば `systemctl restart rsyslog-config` を発行する。

## 4. rsyslog SIGHUP / restart 経路

`rsyslog-config.service` の `ExecStart=/usr/bin/rsyslog-config.sh` が実際の設定反映を行う。

```bash
# sonic-buildimage/files/image_config/rsyslog/rsyslog-config.sh (抜粋)
sonic-cfggen -d -t /usr/share/sonic/templates/rsyslog.conf.j2 \
    -a "{...}" > "$TMPFILE"

if [ ! -f /etc/rsyslog.conf ] || ! cmp -s "$TMPFILE" /etc/rsyslog.conf; then
    # 設定変更あり → /etc/rsyslog.conf を更新して rsyslogd を完全再起動
    cp "$TMPFILE" /etc/rsyslog.conf
    systemctl restart rsyslog
else
    # 設定変更なし → SIGHUP のみ（ログファイル再オープン用）
    systemctl kill -s HUP rsyslog
fi
```

| 状況 | 操作 | 意味 |
|------|------|------|
| `/etc/rsyslog.conf` が変化 | `systemctl restart rsyslog` | rsyslogd プロセス完全再起動（設定全再読込） |
| `/etc/rsyslog.conf` が変化なし | `systemctl kill -s HUP rsyslog` | SIGHUP でログファイル再オープン（ログローテーション対応）のみ |

- **SIGHUP は「変更なし時」のログローテーション対応専用**であり、通常の設定反映は `systemctl restart rsyslog` が担う。
- `hostcfgd` 自身は SIGHUP を受け取っても無視する（`signal_handler` L111-112: `"HostCfgd: signal 'SIGHUP' is caught and ignoring.."`）。

## 5. 起動時スナップショット

```python
# hostcfgd L2251, 2269
syslog_srv = init_data.get(swsscommon.CFG_SYSLOG_SERVER_TABLE_NAME, {})
...
self.rsyslogcfg.load(syslog_cfg, syslog_srv)
```

`hostcfgd` は `config_db.listen(init_data_handler=self.load)` の前に既存の SYSLOG_SERVER エントリを一括取得し `RSyslogCfg.load()` でキャッシュに格納する。起動時に `rsyslog-config.service` は再起動されないが、`wait_till_system_init_done()` の後でテーブル変更が来た時点でトリガーされる。

## 6. keyspace 通知パターン

| Redis keyspace 通知 | hostcfgd ハンドラ呼び出し |
|---------------------|--------------------------|
| `__keyspace@4__:SYSLOG_SERVER\|192.168.1.1` `hset` | `rsyslog_server_handler("192.168.1.1", SET, {...})` |
| `__keyspace@4__:SYSLOG_SERVER\|192.168.1.1` `del`  | `rsyslog_server_handler("192.168.1.1", DEL, {})` |
| `__keyspace@4__:SYSLOG_CONFIG\|GLOBAL` `hset` | `rsyslog_config_handler("GLOBAL", SET, {...})` |

dbId は CONFIG_DB の通常 4（sonic-swss-common の `database_config.json` 既定）。

## 7. ConsumerStateTable / NotificationProducer 非使用の確認

- `SYSLOG_SERVER` テーブルは `swsscommon.ConsumerStateTable`（channel ベース）の購読者なし。
- `NotificationProducer` で SYSLOG_SERVER 関連の通知を出す箇所は SONiC ソース内になし。
- APPL_DB / STATE_DB への中継なし。
- 結論: SYSLOG_SERVER は **CONFIG_DB → hostcfgd (keyspace 通知) → rsyslog-config.service 再起動 → rsyslogd restart/SIGHUP** の一方向パスで完結する。

## 8. 参考行番号

`sonic-host-services/scripts/hostcfgd`:
- L110-113: `signal_handler` — SIGHUP 無視
- L1695-1743: `RSyslogCfg` クラス（load / update_rsyslog_config）
- L2251, 2269: init_data からの初期スナップショット取得
- L2410-2423: `rsyslog_handler` / `rsyslog_server_handler` / `rsyslog_config_handler`
- L2456-2466: `make_callback`
- L2499-2503: `subscribe(SYSLOG_CONFIG / SYSLOG_SERVER)`
- L2528: `config_db.listen(init_data_handler=self.load)`

`sonic-buildimage/files/image_config/rsyslog/rsyslog-config.sh`:
- L58-73: テンプレート展開 → diff → restart or SIGHUP 分岐
