# ZMQ CONFIG_DB フィールド — 失敗挙動調査 (Phase D)

## 調査対象

- `DEVICE_METADATA|localhost` の `orch_northbond_dash_zmq_enabled` / `orch_northbond_route_zmq_enabled`
- `DPU|<name>` の `orchagent_zmq_port`
- ZMQ レイヤ: `zmqserver.cpp`, `zmqclient.cpp`, `orch_zmq_config.cpp`

## 失敗系統の整理

### A. `get_feature_status()` — CONFIG_DB 読み取り失敗

`get_feature_status()` (`orch_zmq_config.cpp:83-110`) は try/catch で
`std::runtime_error` を捕捉する。

```cpp
catch (const std::runtime_error &e)
{
    SWSS_LOG_ERROR("Not found feature %s failed with exception: %s", feature.c_str(), e.what());
    return default_value;
}
```

Redis 接続エラー等で hget が失敗した場合、エラーログを出力して `default_value` を返す。
- `orch_northbond_dash_zmq_enabled` → `true` (DASH ZMQ 有効扱い)
- `orch_northbond_route_zmq_enabled` → `false` (ROUTE ZMQ 無効扱い)

orchagent は起動を継続し、ZMQ チャネルの有効/無効はデフォルト値で固定される。
**retry や再読み取りは行われない**。

evidence: `orch_zmq_config.cpp:83-104`

### B. `get_zmq_port()` — NAMESPACE_ID パース失敗

```cpp
catch (...)
{
    SWSS_LOG_ERROR("Failed to convert %s to int, fallback to default port", nsid_str.c_str());
}
```

`NAMESPACE_ID` 環境変数が整数でない場合、ERROR ログを出力して `ORCH_ZMQ_PORT = 8100` を使用する。
orchagent は継続動作する。

evidence: `orch_zmq_config.cpp:47-50`

### C. `ZmqServer::bind()` 失敗 → `SWSS_LOG_THROW` → プロセス abort

```cpp
int rc = zmq_bind(m_socket, m_endpoint.c_str());
if (rc != 0)
{
    SWSS_LOG_THROW("zmq_bind failed on endpoint: %s, zmqerrno: %d",
        m_endpoint.c_str(), zmq_errno());
}
```

`zmq_bind` が失敗した場合 (`EADDRINUSE` 等)、`SWSS_LOG_THROW` が例外を投げ orchagent プロセスが abort する。
`main.cpp` には `zmq_server->bind()` を wrap する try/catch がないため、例外は伝播して
`main()` を終了させる。systemd がプロセスを再起動する。

また `ZmqServer::bind()` は二重呼び出しも検出する:
```cpp
if (m_socket) {
    SWSS_LOG_THROW("ZmqServer has already been bound to the endpoint: %s", m_endpoint.c_str());
}
```

evidence: `zmqserver.cpp:67-125`, `main.cpp:1032-1037`

### D. `ZmqServer` 受信スレッド — 受信失敗 (`SWSS_LOG_THROW`)

ZMQ 受信スレッド (`mqPollThread`) 内で `zmq_recv` が失敗した場合:

```cpp
SWSS_LOG_THROW("zmq_recv failed, endpoint: %s, zmqerrno: %d", m_endpoint.c_str(), zmq_err);
```

受信データがバッファ上限を超えた場合:
```cpp
SWSS_LOG_THROW("zmq_recv message was truncated (over %d bytes, received %d), increase buffer size, message DROPPED", ...);
```

いずれも例外を投げ、受信スレッドが終了する。ZMQ サーバは再起動まで受信不可になる。
メッセージは **DROP** される (再送なし)。

evidence: `zmqserver.cpp:228-240`

### E. `ZmqServer` — ハンドラ未登録メッセージ → DROP + WARN

```cpp
auto handler = findMessageHandler(dbName, tableName);
if (handler == nullptr) {
    SWSS_LOG_WARN("ZmqServer can't find handler for received message: %s", buffer);
```

未登録テーブルへのメッセージは WARN ログを出力して **DROP** する。
redis への書き込みも行われない。

evidence: `zmqserver.cpp:171-175`

### F. `ZmqClient::sendMsg()` — 送信失敗と自動 retry

送信側 (fpmsyncd/gnmi) で `ZmqProducerStateTable::send()` → `ZmqClient::sendMsg()` が失敗した場合:

| ZMQ エラー | 挙動 | evidence |
|-----------|------|---------|
| `EAGAIN` (socket not ready) | `retry_delay=0` で即 retry、指数バックオフなし | `zmqclient.cpp:209-211` |
| `ETERM` / HWM 超過 | WARN + 指数バックオフ (10ms→20ms→...) で retry | `zmqclient.cpp:216-217` |
| 接続断 (`m_connected=false`) | ERROR + `system_error(connection_reset)` を throw | `zmqclient.cpp:220-223` |
| その他送信エラー | ERROR + `system_error(io_error)` を throw | `zmqclient.cpp:227-230` |
| retry 上限到達 | ERROR + `system_error(io_error)` を throw | `zmqclient.cpp:238-239` |

`system_error` が fpmsyncd/gnmi まで伝播した場合、各プロセスの例外ハンドラが処理する
(orchagent 自体は影響を受けない)。

fpmsyncd は `routesync.cpp` の zmqClient 利用箇所が例外になると、
フォールバックなしにプロセスが終了 → systemd 再起動の経路に入る。

evidence: `zmqclient.cpp:153-239`

### G. `ZmqClient::connect()` 失敗 → `SWSS_LOG_THROW`

```cpp
int rc = zmq_connect(m_socket, m_endpoint.c_str());
if (rc != 0) {
    m_connected = false;
    SWSS_LOG_THROW("failed to connect to zmq endpoint %s, zmqerrno: %d", ...);
}
```

`zmq_connect` 失敗は THROW → fpmsyncd/gnmi プロセス abort → systemd 再起動。

evidence: `zmqclient.cpp:140-149`

## 失敗ケース一覧

| 失敗ケース | コード根拠 | 動作 |
|-----------|---------|------|
| CONFIG_DB hget 失敗 (Redis 接続エラー) | `orch_zmq_config.cpp:93-97` | ERROR ログ → default_value 返却 → orchagent 継続 |
| NAMESPACE_ID 非整数 | `orch_zmq_config.cpp:47-50` | ERROR ログ → port=8100 フォールバック |
| `zmq_bind` 失敗 (EADDRINUSE 等) | `zmqserver.cpp:115-120` | THROW → orchagent abort → systemd 再起動 |
| ZmqServer 二重 bind | `zmqserver.cpp:71-73` | THROW → orchagent abort |
| `zmq_recv` 失敗 (受信スレッド) | `zmqserver.cpp:233` | THROW → 受信スレッド終了 → ZMQ 受信不可 |
| バッファ超過 (受信) | `zmqserver.cpp:239` | THROW + メッセージ DROP |
| ハンドラ未登録メッセージ | `zmqserver.cpp:173` | WARN + メッセージ DROP |
| `zmq_connect` 失敗 (クライアント側) | `zmqclient.cpp:144-145` | THROW → fpmsyncd/gnmi abort |
| 接続断 (送信中) | `zmqclient.cpp:220-223` | ERROR + system_error throw → プロセス abort |
| 送信 retry 上限超過 | `zmqclient.cpp:238-239` | ERROR + system_error throw → プロセス abort |
