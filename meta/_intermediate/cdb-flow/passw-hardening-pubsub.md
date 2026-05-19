# passw-hardening — Phase G 調査証跡 (pubsub / 通信メカニズム)

調査日: 2026-05-19
調査対象: sonic-net/sonic-host-services/scripts/hostcfgd

## 概要

`PASSW_HARDENING` テーブルは `hostcfgd` の `ConfigDBConnector.subscribe()` + `listen()` 方式で購読される。
`swsscommon.SubscriberStateTable` / `ConsumerStateTable` (PUBLISH/SUBSCRIBE チャネル方式) は使用しない。

## 購読登録箇所

```
hostcfgd:2477
self.config_db.subscribe('PASSW_HARDENING', make_callback(self.passwh_handler))
```

`make_callback` は `(key, op, data)` を生成するヘルパー。
`config_db.listen(init_data_handler=self.load)` (hostcfgd:2528) で イベントループを開始する。

## ハンドラ実装

```python
# hostcfgd:2293-2296
def passwh_handler(self, key, op, data):
    self.passwcfg.passw_policies_update(key, data)
    syslog.syslog(syslog.LOG_INFO, 'PASSW_HARDENING Update: key: {}, op: {}, data: {}'.format(key, op, data))
```

## 起動時スナップショット

```python
# hostcfgd:2244
passwh = init_data['PASSW_HARDENING']

# hostcfgd:2264
self.passwcfg.load(passwh)

# PasswHardening.load (hostcfgd:881-885)
def load(self, policies_conf):
    for row in policies_conf:
        self.passw_policies_update(row, policies_conf[row], modify_conf=False)
```

`load()` は `wait_till_system_init_done()` 完了後に呼ばれる。PAM サブシステム安定後の初期適用となる。

## Redis 通知フロー

```
HSET "PASSW_HARDENING|POLICIES" state "enabled"
  → Redis PUBLISH "__keyspace@4__:PASSW_HARDENING|POLICIES" "hset"
  → ConfigDBConnector.listen() パターンマッチ
  → HGETALL "PASSW_HARDENING|POLICIES" で全フィールド再取得
  → make_callback() → passwh_handler(key="POLICIES", op=SET, data={...})
  → passw_policies_update() → modify_passw_conf_file() + set_passw_hardening_policies()
```

## 他プロセスからの購読

`PASSW_HARDENING` テーブルを `subscribe()` で購読するプロセスは `hostcfgd` のみ。
PAM モジュールはファイルシステムの `/etc/pam.d/common-password` を直接参照するため Redis を購読しない。

## サービス再起動なし

PAM 設定変更後のデーモン restart は行わない。PAM は認証処理時に設定ファイルを動的に読み込む設計のため、
`hostcfgd` がファイルを書き換えれば次回ログイン / パスワード変更から新ポリシーが有効になる。
