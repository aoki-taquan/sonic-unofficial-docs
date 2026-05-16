# BANNER_MESSAGE テーブル — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `BANNER_MESSAGE` テーブル (シングルトン: `BANNER_MESSAGE|global`)。

購読者は `hostcfgd` の `BannerCfg` クラスただ 1 つ。`BannerCfg` は CONFIG_DB の変化を Redis keyspace 通知経由で受け取り、`systemctl restart banner-config` を発行して `banner-config.sh` に処理を委譲する。

## 1. 購読 API — `ConfigDBConnector.subscribe()`

`hostcfgd` は `swsscommon.ConfigDBConnector` の `subscribe(table, callback)` でハンドラを登録する。`swsscommon.SubscriberStateTable` / `ConsumerStateTable` / `NotificationConsumer` を**直接は使わず**、`ConfigDBConnector.listen()` が内部で Redis keyspace 通知 (`__keyspace@<dbId>__:<TABLE>|*` の PSUBSCRIBE) を購読してテーブル名一致のコールバックへディスパッチする方式。

```python
# sonic-host-services/scripts/hostcfgd:2519-2521
# Handle BANNER_MESSAGE changes
self.config_db.subscribe(swsscommon.CFG_BANNER_MESSAGE_TABLE_NAME,
                         make_callback(self.banner_handler))

# hostcfgd:2528 (= ConfigDBConnector.listen)
self.config_db.listen(init_data_handler=self.load)
```

- テーブル名は `swsscommon.CFG_BANNER_MESSAGE_TABLE_NAME` (= C++ 側で定義された `"BANNER_MESSAGE"`)。
- channel ベースの `PUBLISH/SUBSCRIBE` (`ConsumerStateTable`) は不使用。CONFIG_DB は publisher (sonic-cfggen / `config banner *` CLI) が `HSET` するのみで明示的な `PUBLISH` を行わない。Redis 側の keyspace notification (`notify-keyspace-events`) が変更を通知する。
- TTL は CONFIG_DB 全エントリで設定されない (永続前提)。

## 2. キー単位ディスパッチ — `make_callback()`

`make_callback()` ラッパが `(table, key, data)` → `(key, op, data)` に変換する。

```python
# hostcfgd:2480-2488 (= register_callbacks 内ローカル関数)
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

- `table`: `"BANNER_MESSAGE"` (callback では未使用)。
- `key`: シングルトンなので常に `"global"`。`BANNER_MESSAGE|foo` のような non-`global` キーも一応 dispatch されるが、`BannerCfg.banner_message()` の挙動はキー名を見ない (`global` 以外でも同様にキャッシュ比較 + restart を走らせる)。なお仕様上 `global` 以外のキーは YANG / CLI から生成されない。
- `op`: `data is None` の場合 `DEL`、それ以外 `SET`。`HSET` と `DEL` の Redis 操作種別は区別しない (`data` の有無のみ)。
- `data`: keyspace 通知本体は操作名のみで値を含まない。`ConfigDBConnector` 側で `HGETALL BANNER_MESSAGE|global` を再取得した dict が渡される。

## 3. ハンドラ — `banner_handler()` → `BannerCfg.banner_message()`

```python
# hostcfgd:2442-2444
def banner_handler(self, key, op, data):
    syslog.syslog(syslog.LOG_INFO, 'BANNER_MESSAGE table handler...')
    self.bannermsgcfg.banner_message(key, data)
```

`op` は無視され、`(key, data)` のみが `BannerCfg.banner_message()` に転送される。`DEL` 経路でも `data={}` のまま渡され、`type(data) != dict` チェックは通過する (空 dict)。差分判定 (`for k,v in data.items()`) は空ループとなり `update_required=False` のまま early return — `DEL` 時は restart されない。

```python
# hostcfgd:2084-2117 (= BannerCfg.banner_message)
def banner_message(self, key, data):
    if type(data) != dict:
        return                       # silent return (dict 型外)

    update_required = False
    for k,v in data.items():
        if v != self.cache.get(k):
            update_required = True
            break

    if update_required == False:
        return                       # キャッシュ一致 → no-op (restart skip)

    try:
        run_cmd(["systemctl", "restart", "banner-config"], True, True)
    except Exception:
        syslog.syslog(syslog.LOG_ERR, 'BannerCfg: Failed to restart '
                      'banner-config service')
        return                       # 失敗時はキャッシュ未更新 → 次変更で再試行

    for k,v in data.items():
        self.cache[k] = v
```

要点:

- 差分判定は **dict 内 1 つでもキャッシュと違えば即 restart**。complete equality ではなく早期 break する。
- キャッシュ更新は `restart` 成功後のみ。失敗時はキャッシュを更新しないため、次回 CONFIG_DB 変化 (同じ値であっても) で再 restart が走る (自動 retry)。
- `BannerCfg` 内部で例外を握りつぶす経路はここのみ。`try/except` は `run_cmd` 失敗の LOG_ERR + early return 用。

## 4. サービス再起動トリガー

| トリガー | 操作 | コード |
|---------|------|--------|
| `BANNER_MESSAGE\|global` の任意フィールド変化 (キャッシュ差分あり) | `systemctl restart banner-config` (oneshot unit) | `run_cmd(["systemctl", "restart", "banner-config"], True, True)` — hostcfgd:2111 |
| `banner-config.service` 起動 | `/usr/bin/banner-config.sh` 実行 → `/etc/issue.net` / `/etc/issue` / `/etc/motd` / `/etc/logout_message` を上書き | `banner-config.service:11` + `banner-config.sh:12-15` |

`BannerCfg` 自身は `sshd` / PAM / `pam_motd` を再起動しない (grep でも参照なし)。sshd は新規接続ごとに `/etc/issue.net` を読み直し、`pam_motd.so` はログインセッション開始時に `/etc/motd` を都度読む Debian 標準挙動に依存する。

## 5. 起動時スナップショット

`HostConfigDaemon.load()` 内で `init_data.get(swsscommon.CFG_BANNER_MESSAGE_TABLE_NAME)` を取得し、`BannerCfg.load()` (hostcfgd:2057-2082) で `state` / `login` / `motd` / `logout` の 4 キーを `banner_messages_config.get(...)` で個別に取り出して `banner_message()` を 4 回呼ぶ。各呼出しでキャッシュ差分判定 → 必要時のみ `systemctl restart banner-config`。

- **再起動回数は最大 4 回**: 全フィールドが初期 cache (`{}`) と差分ありとなるため、起動時最大 4 回 `systemctl restart banner-config` が連続発行される (hostcfgd:2079-2082)。`banner-config.service` は oneshot + `RemainAfterExit=no` なので、各 restart は新規 ExecStart 起動。
- 起動時に CONFIG_DB に `BANNER_MESSAGE|global` 自体がない場合 (`banner_messages_config` が None / falsy)、`banner_messages_config = {}` に置換した上で同じ 4 回ループを通る。各 `.get()` は `{}` を返し、`data={}` でループは空。差分なしで restart は発行されない。
- `LOG_INFO 'BannerCfg: load initial'` が `load()` 冒頭に出力されるため、journal で起動時実行を検知可能。

## 6. keyspace 通知パターン

| Redis 通知 | hostcfgd 受信 |
|-----------|---------------|
| `__keyspace@4__:BANNER_MESSAGE\|global` `hset` | `banner_handler("global", SET, {state: ..., login: ..., motd: ..., logout: ...})` |
| `__keyspace@4__:BANNER_MESSAGE\|global` `hdel` (一部フィールド削除) | 同上 `SET` 扱い (HGETALL の結果が部分 dict として渡る) |
| `__keyspace@4__:BANNER_MESSAGE\|global` `del` (キー全消去) | `banner_handler("global", DEL, {})` → 差分判定で空ループ → no-op (restart skip) |
| `__keyspace@4__:BANNER_MESSAGE\|foo` (非 global キー) | `banner_handler("foo", SET, {...})` → `banner_message("foo", ...)` で差分があれば restart 発行 (実害なし: banner-config.sh は `global` 固定参照) |

dbId は CONFIG_DB の通常 4 (`sonic-swss-common/common/database_config.json` 既定)。

## 7. ConsumerStateTable / NotificationProducer 非使用の確認

- `BANNER_MESSAGE` テーブルを `swsscommon.ConsumerStateTable` / `SubscriberStateTable` / `NotificationConsumer` で購読する箇所は SONiC ソース内に**他に存在しない** (hostcfgd の `ConfigDBConnector.subscribe` のみ)。
- `NotificationProducer` で `BANNER_MESSAGE` 関連の通知を出す箇所もなし。
- `banner-config.sh` 側は `sonic-db-cli CONFIG_DB HGET` で Redis を**ポーリング読み取り**するだけで購読しない。systemd の `restart` 経由で起動するたびに最新値を再取得する設計。
- 結論: BANNER_MESSAGE は **CONFIG_DB → hostcfgd (keyspace 通知) → systemctl restart banner-config → banner-config.sh が CONFIG_DB を再読込 → ファイル書き換え** の一方向で完結し、APPL_DB / STATE_DB / SAI / NotificationProducer 等を経由しない。

## 8. 反映タイミングと race window

- CONFIG_DB 書込み → keyspace 通知到達 → `banner_handler` 呼び出し → `systemctl restart banner-config` → `banner-config.sh` ExecStart 開始 → 4 ファイル順次 `echo -e ... >` 上書き。`O(秒)` で完了。
- **race window**: `banner-config.sh:12-15` で `/etc/issue.net` → `/etc/issue` → `/etc/motd` → `/etc/logout_message` の 4 ファイルを**順次**書き換えるため、書込み途中に SSH 接続 / login が発生した場合、新 issue.net + 旧 motd が短時間混在し得る。`set -e` 中の途中失敗時は以降の 3 ファイルが書かれず、部分書込状態が残存する。
- **複数フィールド同時更新**: 1 つの CLI 操作 (`config banner login "..."` 等) は 1 フィールド `HSET` のみ → keyspace 通知 1 回 → restart 1 回。4 フィールドを同時に変更したい場合は `sonic-db-cli HMSET` を 1 回叩くことで restart 回数を 1 回に抑えられる (UI 側 `config banner *` コマンドはフィールド単位なので、4 フィールド変更すると 4 回 restart)。
- **冪等性**: `banner-config.sh` は同じファイルを上書きするだけなので、複数回 restart されても最終状態は CONFIG_DB の値と一致。

## 9. 参考行番号

- `sonic-host-services/scripts/hostcfgd`
  - 2044-2117: `BannerCfg` クラス本体
  - 2057-2082: `BannerCfg.load()` (起動時スナップショット適用)
  - 2084-2117: `BannerCfg.banner_message()` (差分判定 + restart)
  - 2111-2114: `run_cmd(["systemctl", "restart", "banner-config"], ...)` + LOG_ERR
  - 2215-2216: `self.bannermsgcfg = BannerCfg()` インスタンス化
  - 2259: `banner_messages = init_data.get(swsscommon.CFG_BANNER_MESSAGE_TABLE_NAME)`
  - 2274: `self.bannermsgcfg.load(banner_messages)` (initial load)
  - 2442-2444: `banner_handler(key, op, data)`
  - 2480-2488: `make_callback()` (register_callbacks 内ローカル関数)
  - 2519-2521: `config_db.subscribe(CFG_BANNER_MESSAGE_TABLE_NAME, banner_handler)`
  - 2528: `self.config_db.listen(init_data_handler=self.load)`
- `sonic-buildimage/files/image_config/bannerconfig/banner-config.sh`
  - 1: shebang `#!/bin/bash -e`
  - 3-11: `sonic-db-cli CONFIG_DB HGET 'BANNER_MESSAGE|global' <field>` で CONFIG_DB 再読込
  - 12-15: 4 ファイル順次 `echo -e ... >` 上書き
- `sonic-buildimage/files/image_config/bannerconfig/banner-config.service`
  - 9-11: `Type=oneshot` / `RemainAfterExit=no` / `ExecStart=/usr/bin/banner-config.sh`
