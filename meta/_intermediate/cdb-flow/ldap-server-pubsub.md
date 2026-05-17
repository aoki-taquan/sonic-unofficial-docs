# LDAP_SERVER テーブル — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `LDAP_SERVER` テーブル（および `LDAP|global`）。

## 1. 購読 API — `ConfigDBConnector.subscribe()` (channel ベースではない)

`hostcfgd` は `swsscommon.SubscriberStateTable` を**直接は使わず**、`swsscommon` の Python ラッパ `ConfigDBConnector` の `subscribe(table, callback)` でハンドラを登録する。

```python
# sonic-host-services/scripts/hostcfgd:2475-2476
self.config_db.subscribe('LDAP',        make_callback(self.ldap_global_handler))
self.config_db.subscribe('LDAP_SERVER', make_callback(self.ldap_server_handler))
...
# hostcfgd:2528
self.config_db.listen(init_data_handler=self.load)
```

- `ConfigDBConnector.listen()` が内部で Redis の **keyspace 通知** (`__keyspace@<dbId>__:<TABLE>|*` の PSUBSCRIBE) を購読し、テーブル名にマッチしたコールバックへ `(key, op, data)` をディスパッチする。
- channel ベースの `PUBLISH/SUBSCRIBE` (`ConsumerStateTable` 形式) は使用していない。CONFIG_DB は publisher (sonic-cfggen / config CLI) が `HSET` するのみで明示的な `PUBLISH` を行わず、Redis 側の keyspace notification (`Kxxx` / `notify-keyspace-events`) が変更を通知する。
- TTL は CONFIG_DB の全エントリで設定されない（CONFIG_DB は永続前提）。

## 2. make_callback ラッパ

```python
# hostcfgd:2454-2466
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

- `key`: `LDAP_SERVER|<ip>` の右辺 (IPアドレス / FQDN)。`LDAP|global` の場合は `global`。
- `op`: `data is None` の場合 `DEL`、それ以外は `SET`（`HSET` / `HDEL` の Redis 操作種別は区別しない）。
- `data`: 通知後に hostcfgd 側が **HGETALL で再取得した** dict（keyspace 通知本体には値は含まれず操作名のみ）。

## 3. ハンドラ定義

| 購読テーブル | ハンドラ (hostcfgd 行) | `AaaCfg` メソッド | 副作用 |
|---|---|---|---|
| `LDAP` | `ldap_global_handler` (L.2331) | `ldap_global_update` | `modify_conf_file()` → `nslcd.conf` / `ldap.conf` 再生成 + `handle_nslcd_service()` |
| `LDAP_SERVER` | `ldap_server_handler` (L.2338) | `ldap_server_update` | サーバリスト更新 → `modify_conf_file()` → 同上 |

```python
# hostcfgd:2331-2343
def ldap_global_handler(self, key, op, data):
    self.aaacfg.ldap_global_update(key, data)
    log_data = copy.deepcopy(data)
    if 'passkey' in log_data:
        log_data['passkey'] = obfuscate(log_data['passkey'])
    syslog.syslog(syslog.LOG_INFO, 'LDAP Global update: key: {}, op: {}, data: {}'.format(key, op, log_data))

def ldap_server_handler(self, key, op, data):
    self.aaacfg.ldap_server_update(key, data)
    log_data = copy.deepcopy(data)
    if 'passkey' in log_data:
        log_data['passkey'] = obfuscate(log_data['passkey'])
    syslog.syslog(syslog.LOG_INFO, 'LDAP_SERVER update: key: {}, op: {}, data: {}'.format(key, op, log_data))
```

## 4. keyspace 通知パターン (Redis dbId=4 が CONFIG_DB の通常値)

| Redis 通知チャンネル | 操作 | hostcfgd 受信 |
|---|---|---|
| `__keyspace@4__:LDAP\|global` | `hset` | `ldap_global_handler("global", SET, {...})` |
| `__keyspace@4__:LDAP\|global` | `del` | `ldap_global_handler("global", DEL, {})` |
| `__keyspace@4__:LDAP_SERVER\|10.0.0.1` | `hset` | `ldap_server_handler("10.0.0.1", SET, {priority:"1",...})` |
| `__keyspace@4__:LDAP_SERVER\|10.0.0.1` | `del` | `ldap_server_handler("10.0.0.1", DEL, {})` |

## 5. AAA テーブルとの連携

`AAA|authentication.login` フィールドの変更も `hostcfgd` が購読し `aaa_handler` → `aaa_update` → `is_ldap_config_complete()` 評価を行う。`LDAP_SERVER` 自体が変更されなくても AAA の変更が `nslcd` 起動/停止をトリガーする（相互依存）。

## 6. 起動時スナップショット

`hostcfgd` は `config_db.listen()` 前に `init_data_handler=self.load` を渡し、`HostConfigDaemon.load()` で `init_data['LDAP']` / `init_data['LDAP_SERVER']` を一括取得して `AaaCfg.load()` (hostcfgd:399-417) でまとめて適用してから Subscribe ループへ入る。

- 起動直後にも CONFIG_DB の既存 LDAP エントリが nslcd 設定に反映される。
- ループ内で来る通知は差分扱い（load 中の自己 SET は keyspace 通知も来るが冪等）。

## 7. ConsumerStateTable / NotificationProducer 非使用の確認

- `LDAP_SERVER` テーブルは `swsscommon.ConsumerStateTable` (channel ベース) の購読者なし。
- `NotificationProducer` で LDAP 関連の通知を出す箇所は SONiC ソース内になし（APPL_DB / STATE_DB 中継なし）。
- 結論: LDAP_SERVER は **CONFIG_DB → hostcfgd (keyspace 通知) → ファイル書き換え + nslcd 再起動** の一方向で完結し、APPL_DB/STATE_DB の中継・通知パスを持たない。

## 8. 参考行番号

- `sonic-host-services/scripts/hostcfgd`
  - 2454-2466: `make_callback`
  - 2475-2476: `subscribe('LDAP' / 'LDAP_SERVER')`
  - 2528: `self.config_db.listen(init_data_handler=self.load)`
  - 2331-2343: `ldap_global_handler` / `ldap_server_handler`
  - 399-417: `AaaCfg.load()` 初期スナップショット適用
  - 547-564: `ldap_global_update` / `ldap_server_update`
  - 437-442: `is_ldap_config_complete()`
  - 241-251: `handle_nslcd_service()`
