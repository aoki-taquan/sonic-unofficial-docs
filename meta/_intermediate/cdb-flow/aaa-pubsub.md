# AAA テーブル — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `AAA` テーブル（および付帯テーブル `TACPLUS` / `TACPLUS_SERVER` / `RADIUS` / `RADIUS_SERVER` / `LDAP` / `LDAP_SERVER`）。

## 1. 購読 API — `ConfigDBConnector.subscribe()` (channel ベースではない)

`hostcfgd` は `swsscommon.SubscriberStateTable` を**直接は使わず**、`swsscommon` の Python ラッパ `ConfigDBConnector` の `subscribe(table, callback)` でハンドラを登録する。

```python
# sonic-host-services/scripts/hostcfgd:2468-2476
self.config_db.subscribe('KDUMP', make_callback(self.kdump_handler))
# Handle AAA, TACACS and RADIUS related tables
self.config_db.subscribe('AAA',            make_callback(self.aaa_handler))
self.config_db.subscribe('TACPLUS',        make_callback(self.tacacs_global_handler))
self.config_db.subscribe('TACPLUS_SERVER', make_callback(self.tacacs_server_handler))
self.config_db.subscribe('RADIUS',         make_callback(self.radius_global_handler))
self.config_db.subscribe('RADIUS_SERVER',  make_callback(self.radius_server_handler))
self.config_db.subscribe('LDAP',           make_callback(self.ldap_global_handler))
self.config_db.subscribe('LDAP_SERVER',    make_callback(self.ldap_server_handler))
...
# hostcfgd:2528
self.config_db.listen(init_data_handler=self.load)
```

- `ConfigDBConnector.listen()` が内部で Redis の **keyspace 通知** (`__keyspace@<dbId>__:<TABLE>|*` の PSUBSCRIBE) を購読し、テーブル名にマッチしたコールバックへ `(key, op, data)` をディスパッチする。
- channel ベースの `PUBLISH/SUBSCRIBE` (`ConsumerStateTable` 形式) は使用していない。CONFIG_DB は publisher (sonic-cfggen / config CLI) が `HSET` するのみで明示的な `PUBLISH` を行わず、Redis 側の keyspace notification (`Kxxx` / `notify-keyspace-events`) が変更を通知する。
- TTL は CONFIG_DB の全エントリで設定されない（CONFIG_DB は永続前提）。

## 2. キー単位ディスパッチ

`make_callback()` は以下のラッパを生成する:

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

- `key`: `AAA|authentication` 等の `|` 区切り key の右辺 (`authentication` / `authorization` / `accounting`)。
- `op`: `data is None` の場合 `DEL`、それ以外は `SET` (区別は data 有無のみ; `HSET` vs `DEL` の Redis 操作種別は見ない)。
- `data`: 通知後に hostcfgd 側が **HGETALL で再取得した** dict (keyspace 通知本体には値は含まれず操作名のみ)。

## 3. 各ハンドラの動作

| 購読テーブル | ハンドラ (hostcfgd) | `AaaCfg` メソッド | 副作用 |
|--------------|---------------------|--------------------|--------|
| `AAA`            | `aaa_handler` (2289)            | `aaa_update`            | PAM/NSS テンプレ再生成 + `handle_nslcd_service()` 呼び出し (LDAP) |
| `TACPLUS`        | `tacacs_global_handler` (2310)  | `tacacs_global_update`  | `modify_conf_file()` 経由で `tacplus_nss.conf` + `common-auth-sonic` 再生成 |
| `TACPLUS_SERVER` | `tacacs_server_handler` (2303)  | `tacacs_server_update`  | サーバリスト更新 → テンプレ再生成 → `audisp-tacplus` に `SIGHUP` |
| `RADIUS`         | `radius_global_handler` (2324)  | `radius_global_update`  | `radius_nss.conf` + `pam_radius_auth.d/*.conf` 再生成 |
| `RADIUS_SERVER`  | `radius_server_handler` (2317)  | `radius_server_update`  | 上記 + `radius-stats` 起動制御 |
| `LDAP`           | `ldap_global_handler` (2331)    | `ldap_global_update`    | `ldap.conf` 再生成 + `handle_nslcd_service()` |
| `LDAP_SERVER`    | `ldap_server_handler` (2338)    | `ldap_server_update`    | 同上 |

## 4. サービス再起動トリガー

`AaaCfg` は単純なテンプレ再生成（ファイル書き換え）以外に、以下の外部サービス操作を伴う:

| トリガー | 操作 | コード |
|---------|------|--------|
| `is_ldap_config_complete()` が変化 | `systemctl unmask/restart nslcd` または `stop/mask nslcd` | `restart_service()` / `handle_nslcd_service()` — hostcfgd:230-251, 434-435, 553, 564 |
| `TACPLUS_SERVER` 変化 | `audisp-tacplus` プロセスに `SIGHUP` (PAM ホット再読込) | `notify_audisp_tacplus_reload_config` — hostcfgd:483-493 |
| `RADIUS_SERVER` 変化 | `radius-stats` daemon 起動制御 | hostcfgd:839 付近 |

PAM ファイル (`/etc/pam.d/common-auth` 等) と `nsswitch.conf` は **デーモン restart なしで直接書き換え** され、次回ログイン (`pam_start()`) から有効になる。進行中の SSH/コンソールセッションには影響しない (PAM は認証時のみ設定を読む)。

## 5. 起動時スナップショット

`hostcfgd` は `config_db.listen()` の前に `init_data_handler=self.load` を渡し、`HostConfigDaemon.load()` 内で `init_data['AAA']` / `TACPLUS*` / `RADIUS*` / `LDAP*` を一括取得して `AaaCfg.load()` (hostcfgd:399-417) でまとめて適用してから Subscribe ループへ入る。これにより:

- 起動直後にも CONFIG_DB の既存 AAA エントリが PAM/NSS/`nslcd` 設定に反映される。
- ループ内で来る通知は差分扱い (load 中の自己 SET は keyspace 通知も来るが冪等)。

## 6. keyspace 通知パターン

| Redis 通知 | hostcfgd 受信 |
|-----------|---------------|
| `__keyspace@4__:AAA|authentication` `hset` | `aaa_handler("authentication", SET, {...})` |
| `__keyspace@4__:AAA|authentication` `del`  | `aaa_handler("authentication", DEL, {})` |
| `__keyspace@4__:TACPLUS_SERVER|10.0.0.1` `hset` | `tacacs_server_handler("10.0.0.1", SET, {...})` |
| `__keyspace@4__:LDAP|global` `hset` | `ldap_global_handler("global", SET, {...})` |

dbId は CONFIG_DB の通常 4 (sonic-swss-common の `database_config.json` 既定)。

## 7. ConsumerStateTable / NotificationProducer 非使用の確認

- `AAA` テーブルは `swsscommon.ConsumerStateTable` (channel ベース) の購読者なし。grep 結果でも `hostcfgd` のみが該当テーブルを購読。
- `NotificationProducer` で AAA 関連の通知を出す箇所は SONiC ソース内になし。
- 結論: AAA は **CONFIG_DB → hostcfgd(keyspace 通知) → ファイル書き換え → PAM/NSS** の一方向で完結し、APPL_DB/STATE_DB の中継・通知パスを持たない。

## 8. 参考行番号

- `sonic-host-services/scripts/hostcfgd`
  - 2454-2466: `make_callback`
  - 2468-2476: `subscribe('AAA' / 'TACPLUS*' / 'RADIUS*' / 'LDAP*')`
  - 2528: `self.config_db.listen(init_data_handler=self.load)`
  - 2289-2343: 各 *_handler 実装
  - 399-417: `AaaCfg.load()` 初期スナップショット適用
  - 419-435: `aaa_update()`
  - 230-251: `restart_service` / `handle_nslcd_service`
  - 483-493: `notify_audisp_tacplus_reload_config`
