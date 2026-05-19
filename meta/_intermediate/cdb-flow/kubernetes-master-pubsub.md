# kubernetes-master pubsub 調査ノート (Phase G)

調査対象: `sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/ctrmgrd.py`
調査日: 2026-05-19

## 概要

`ctrmgrd` は `MainServer.register_handler()` を通じて全テーブルを
`swsscommon.SubscriberStateTable` で購読する (ctrmgrd.py:204-217)。
`KUBERNETES_MASTER` への書き込みは `swsscommon.Table.set()` を経由し、
Redis keyspace 通知として `SubscriberStateTable` に配信される。
APPL_DB 中継・ProducerStateTable・ConsumerStateTable は一切使わない。

## 購読チャンネル一覧

| チャンネル | DB | テーブル名 | 購読クラス | 購読クラス定義場所 |
|---|---|---|---|---|
| CONFIG_DB → ctrmgrd | CONFIG_DB | `KUBERNETES_MASTER` | `SubscriberStateTable` | ctrmgrd.py:333-334 |
| CONFIG_DB → ctrmgrd | CONFIG_DB | `FEATURE` | `SubscriberStateTable` | ctrmgrd.py:471-472 |
| STATE_DB → ctrmgrd | STATE_DB | `FEATURE` | `SubscriberStateTable` | ctrmgrd.py:473-474 |
| STATE_DB → ctrmgrd | STATE_DB | `KUBE_LABELS` | `SubscriberStateTable` | ctrmgrd.py:642 |

## 各チャンネルの詳細

### CONFIG_DB:KUBERNETES_MASTER (`RemoteServerHandler`)

`RemoteServerHandler.__init__()` (ctrmgrd.py:329-359) が
`server.register_handler(CONFIG_DB_NAME, SERVER_TABLE, self.on_config_update)` を呼ぶ。
`MainServer.register_handler()` (ctrmgrd.py:204-217) が `SubscriberStateTable` を生成し
`selector.addSelectable()` で Select ループに登録する。

- Redis keyspace 通知: `PSUBSCRIBE __keyspace@4__:KUBERNETES_MASTER|*`
- 受信キー: `SERVER`（単一エントリ）
- ハンドラ: `on_config_update(key, op, data)` → `handle_update()` → `do_join()` / `do_reset()`
- 起動時スナップショット: `SubscriberStateTable` は既存エントリを buffer に流す。
  ctrmgrd.py:335-336 で `get_db_entry()` により明示的に初期値を読み出しており、
  購読開始前の既存設定も正常に反映される。

### CONFIG_DB:FEATURE + STATE_DB:FEATURE (`FeatureTransitionHandler`)

`FeatureTransitionHandler.__init__()` (ctrmgrd.py:466-475) が
CONFIG_DB と STATE_DB の両方の `FEATURE` テーブルを購読する。

- CONFIG_DB:FEATURE ハンドラ: `on_config_update()` → `handle_update()` (set_owner 変化時)
- STATE_DB:FEATURE ハンドラ: `on_state_update()` → `handle_update()` (remote_state 変化時)
- 両方のイベントが揃うまで `handle_update()` の実行を保留する設計
  (ctrmgrd.py:533-543: CONFIG_DB のみ受信済みの場合は state_db 側を待機)

### STATE_DB:KUBE_LABELS (`LabelsPendingHandler`)

`LabelsPendingHandler.__init__()` (ctrmgrd.py:640-646) が
`STATE_DB:KUBE_LABELS` を購読する。

- ハンドラ: `on_update(key, op, data)` (ctrmgrd.py:649-663)
- key == `SET` のエントリのみ処理（それ以外は無視）
- `remote_connected == True` かつ `pending == False` の場合のみ
  `kube_write_labels()` を Kubernetes API Server に送信
- `remote_connected == False` の場合はラベルをバッファリングし、
  join 成功時に `RemoteServerHandler.do_join()` がラベル更新をトリガーする

## Select ループによるディスパッチ

`MainServer.run()` (ctrmgrd.py:249-288) の select ループ:

```python
state, _ = self.selector.select(timeout)  # timeout = SELECT_TIMEOUT(1000ms) or next timer
for subscriber in self.subscribers:
    key, op, fvs = subscriber.pop()
    for callback in self.callbacks[db_name][table_name]:
        callback(key, op, dict(fvs))
```

全 `SubscriberStateTable` が同一 `Select` インスタンスに登録されており、
どのテーブルへの変化も同じ select ループで受信・ディスパッチされる。
複数テーブルへの同時更新は `self.subscribers` を順番にポーリングするため
処理順序は Python set の反復順（不定）になる可能性がある。

## 書き込み側（発行元）

| テーブル | 発行元 | 書き込み手段 |
|---|---|---|
| `CONFIG_DB:KUBERNETES_MASTER` | `sonic-utilities/config/kube.py` (CLI) | `swsscommon.Table.set()` / direct |
| `CONFIG_DB:FEATURE` | `hostcfgd`、各種 mgmt daemon | `swsscommon.Table.set()` |
| `STATE_DB:FEATURE` | `containercfgd`、systemd service proxy | `swsscommon.Table.set()` |
| `STATE_DB:KUBE_LABELS` | `ctrmgrd` 自身 (set_node_labels / FeatureTransitionHandler) | `swsscommon.Table.set()` |
