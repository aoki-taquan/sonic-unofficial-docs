# FEATURE テーブル — ハードコード定数調査 (Phase E)

調査対象ソース:
- `sonic-host-services/scripts/featured`

## 発見定数一覧

| 定数名 | 値 | 定義場所 | 用途 |
|--------|-----|---------|------|
| `HOSTCFGD_MAX_PRI` | `10` | `featured:22` | featured の CONFIG_DB subscriber 優先度 (select キュー内の処理順序) |
| `DEFAULT_SELECT_TIMEOUT` | `1000` (ms) | `featured:23` | `selector.select()` のポーリング間隔 (= 1 秒ごとに PORT_INIT タイムアウト判定を実施) |
| `PORT_INIT_TIMEOUT_SEC` | `180` (秒) | `featured:24` | `delayed=True` フィーチャーを強制起動するまでのポート初期化待ちタイムアウト。経過後 `handle_port_table_timeout()` が呼ばれ全 delayed フィーチャーを enable する |
| `WAIT_FOR_STABLE_TIMEOUT` | `60` (秒) | `featured:426` | `disable_feature()` が `wait_for_service_stable()` で systemd unit の `activating` 状態抜けを待つ最大時間 |
| `WAIT_FOR_STABLE_POLL_INTERVAL` | `1` (秒) | `featured:427` | `wait_for_service_stable()` 内のポーリング間隔。`time.sleep(1)` で繰り返し `systemctl is-active` を実行 |

## 定数の用途詳細

### PORT_INIT_TIMEOUT_SEC (180 秒)

```python
# featured:654-661
def start(self, init_time):
    while True:
        state, selectable_ = self.selector.select(DEFAULT_SELECT_TIMEOUT)  # 1秒ごとに再評価
        if state == self.selector.TIMEOUT:
            if int(time.time() - init_time) > PORT_INIT_TIMEOUT_SEC:      # 180秒経過で強制起動
                self.feature_handler.handle_port_table_timeout()
```

`delayed=True` のフィーチャー（例: `bgp`、`teamd`）は通常 PortInitDone イベントを受信するまで起動を保留する。ただし 180 秒経過してもイベントが来ない場合（ポート不在のプラットフォーム等）は強制的に全 delayed フィーチャーを起動する。

### WAIT_FOR_STABLE_TIMEOUT / WAIT_FOR_STABLE_POLL_INTERVAL (60 秒 / 1 秒)

```python
# featured:426-449
WAIT_FOR_STABLE_TIMEOUT = 60
WAIT_FOR_STABLE_POLL_INTERVAL = 1

def wait_for_service_stable(self, unit):
    deadline = time.time() + self.WAIT_FOR_STABLE_TIMEOUT
    while time.time() < deadline:
        # ... systemctl is-active <unit> ...
        if state != "activating":
            return state
        time.sleep(self.WAIT_FOR_STABLE_POLL_INTERVAL)
    # タイムアウト後は警告ログを出力してそのまま stop を実行
```

`disable_feature()` はコンテナ停止前に `systemctl stop` を送る前にこの関数を呼び出す。サービスが `activating` (ExecStartPre 中) に stop を送ると ExecStop が実行されずコンテナが孤立するリスクがあるため、最大 60 秒ポーリングして安定状態を待つ。

### HOSTCFGD_MAX_PRI (10) と subscriber 優先度

```python
# featured:644-648
self.subscribe(self.cfg_db_conn, FEATURE_TBL,
               make_callback(self.feature_handler.handler), HOSTCFGD_MAX_PRI)    # pri=10

self.subscribe(self.appl_db_conn, PORT_TBL,
               make_callback(self.feature_handler.port_listener), HOSTCFGD_MAX_PRI-1)  # pri=9
```

FEATURE テーブルの subscriber が priority 10、PORT テーブル (PortInitDone 検出用) が priority 9。`swsscommon.Select` は高優先度キューを先に処理する。hostcfgd 内の他ハンドラとの処理順序を管理するための値。

### DEFAULT_SELECT_TIMEOUT (1000 ms)

```python
# featured:656
state, selectable_ = self.selector.select(DEFAULT_SELECT_TIMEOUT)
```

主イベントループの `selector.select()` タイムアウト値。1 秒ごとに TIMEOUT イベントが返り、PORT_INIT_TIMEOUT_SEC の経過チェックが行われる。通常のイベント駆動処理には影響しないが、delayed フィーチャーの強制起動チェックの分解能を決定する。

## queue サイズ

`swsscommon.TableConsumable.DEFAULT_POP_BATCH_SIZE` を subscriber に渡している（`featured:630`）が、この値は swsscommon ライブラリ側で定義されており featured スクリプト内にはハードコードされていない。

## retry

`featured` スクリプトには明示的な retry カウンタのハードコード定数はない。`config_db.connect(wait_for_init=True, retry_on=True)` は swsscommon ライブラリ側が管理する。

## 証跡

- `sonic-host-services/scripts/featured:22-24` — モジュール定数
- `sonic-host-services/scripts/featured:426-449` — `wait_for_service_stable()`
- `sonic-host-services/scripts/featured:630,644-648` — subscriber 登録
- `sonic-host-services/scripts/featured:654-661` — メインループ
