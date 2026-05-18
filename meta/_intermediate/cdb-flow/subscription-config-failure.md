# TELEMETRY_CLIENT Subscription/DestinationGroup — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-18 (q67-f-batch78-next)

ソース: `sonic-net/sonic-gnmi/dialout/dialout_client/dialout_client.go`
ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22

---

## Phase D: 失敗挙動マトリクス

### SET 処理における失敗経路

#### Global エントリ

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `retry_interval` が整数として ParseUint できない文字列 | `processTelemetryClientConfig()` | `continue` でスキップ（フィールド無視）。`clientCfg.RetryInterval` はゼロ値のまま → 次接続試行で即タイムアウト | `log.V(2)` ("Invalid retry_interval...") | `dialout_client.go:495-498` |
| Global に `hdel` 操作（DEL） | `processTelemetryClientConfig()` L484-486 | エラー `"Invalid delete operation for <key>"` を返し処理中断。Global エントリは削除不可 | `log.V(2)` ("Invalid delete operation for ...") | `dialout_client.go:484-487` |
| `encoding` に `JSON_IETF` 以外の enum 値を設定 | `processTelemetryClientConfig()` L500-502 | コメント "Flexible encoding Not supported yet" — 常に `JSON_IETF` を代入。エラーなし・ログなし（silent ignore） | なし | `dialout_client.go:500-502` |
| `unidirectional = false` を設定 | `processTelemetryClientConfig()` L503-505 | コメント "No PublishResponse supported yet" — 常に `true` を代入。エラーなし・ログなし（silent ignore） | なし | `dialout_client.go:503-505` |
| 未知フィールド名（`switch` の `default` にフォールスルー） | Global の `for field, value` ループ | `switch` に `default` ケースなし → フィールドは静かに無視される | なし | `dialout_client.go:488-507` |

#### DestinationGroup エントリ

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `destGroupName` が空文字列 | `processTelemetryClientConfig()` L516-518 | エラー `"Empty Destination Group name <key>"` を返す | なし | `dialout_client.go:516-518` |
| `dst_addr` に無効な `host:port` 値（`Validate()` 失敗） | `dst.Validate()` | エラー `"Invalid destination address <addrs>"` を返し DestinationGroup 全体が登録されない | `log.V(2)` | `dialout_client.go:538-543` |
| `dst_addr` フィールド以外の未知フィールド | `switch field` の `default` | エラー `"Invalid DestinationGroup value <value>"` を返す。DestinationGroup 全体が登録されない | `log.V(2)` | `dialout_client.go:544-547` |
| DestinationGroup の DEL — Subscription から参照中 | `processTelemetryClientConfig()` L522-526 | エラー `"<name> is being used: <DestGrp2ClientSubMap>"` を返す。DEL が拒否され DestinationGroup は残存する | `log.V(1)` | `dialout_client.go:522-526` |
| DestinationGroup の DEL — 参照なし | L527-529 | `destGrpNameMap` からのみ削除。参照元 Subscription が後から再登録されると `NewInstance()` で `"Destination group doesn't exist"` エラー | `log.V(3)` | `dialout_client.go:527-529` |

#### Subscription エントリ

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `name`（Subscription_ 以降）が空文字列 | `processTelemetryClientConfig()` L554-556 | エラー `"Empty Subscription_ name <key>"` を返す | なし | `dialout_client.go:554-556` |
| `paths` に ygot.StringToPath で解析不能なパス文字列 | `ygot.StringToPath()` | エラー `"Invalid paths <value>"` を返し Subscription 全体が登録されない | `log.V(2)` | `dialout_client.go:607-613` |
| `report_interval` が整数として ParseUint できない | L593-596 | `continue` でスキップ。`cs.interval` はデフォルト `5000ms` のまま | `log.V(2)` | `dialout_client.go:593-596` |
| 未知フィールド名 | `switch field` の `default` | エラー `"Invalid field <field> value <value>"` を返し Subscription 全体が登録されない | `log.V(2)` | `dialout_client.go:616-618` |
| `dst_group` 省略（空文字列のまま） | L622-625 | エラーなしで `return nil`。Subscription はメモリ登録もされない（サイレント無効化） | なし | `dialout_client.go:622-625` |
| `dst_group` に存在しない DestinationGroup 名を指定 | `NewInstance()` L181-185 | エラー `"Destination group <name> doesn't exist"` を返す。接続は開始されない | `log.V(2)` | `dialout_client.go:181-185` |
| `path_target` 省略（空文字列のまま） | `NewInstance()` L187-190 | エラー `"Empty target data not supported yet"` を返す。接続は開始されない | なし | `dialout_client.go:187-190` |

### 接続・ストリーム層の失敗経路 (publishRun)

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `retry_interval = 0`（ゼロ値）での `newClient()` 呼び出し | `context.WithTimeout(ctx, 0)` | `grpc.DialContext` が即タイムアウト → `goto restart` で無限高速リトライループに入る | `log.V(1)` ("Dialout connection ... failed") | `dialout_client.go:260-261, 314-317` |
| gRPC `DialContext` 失敗（ネットワーク到達不能 / コレクタ停止） | `publishRun()` L314-317 | `goto restart` でラウンドロビン次 `dst_addr` を試みる。全 addr 消化後も同サイクルを繰り返す | `log.V(1)` | `dialout_client.go:306, 314-317` |
| `Publish()` RPC 失敗 | `publishRun()` L321-326 | `c.Close()` → `cs.Close()` → `goto restart` で再接続 | `log.V(1)` ("Publish ... failed, retrying") | `dialout_client.go:321-326` |
| DB データ読み出しエラー（Periodic モード） | `cs.dc.Get()` L344-348 | `continue` でスキップ。報告がスキップされるだけでストリームは継続。エラーは蓄積されない | `log.V(2)` ("Data read error") | `dialout_client.go:344-348` |
| `send()` のストリーム送信エラー | `cs.send()` L213 → `stream.Send()` 失敗 | エラーを呼び元 (`publishRun`) に返し `goto restart` で再接続 | `log.V(1)` ("Failed to Send") | `dialout_client.go:248-249, 393-397` |
| `ctx` キャンセル（`cs.Close()` 由来） | `publishRun()` L307-312 | `case <-ctx.Done()` で正常終了。`goto restart` は実行されない | `log.V(1)` | `dialout_client.go:307-312` |

### retry / 復旧挙動補足

- **gRPC 再接続は無限リトライ**: `goto restart` ループに上限なし。`retry_interval` が `0` の場合はCPU 高消費の高速リトライになる。`retry_interval` は必ず正値で設定すること。
- **DestinationGroup のラウンドロビン**: `publishRun` は `destIdx = (destIdx + 1) % destNum` で複数 `dst_addr` をラウンドロビン。1 台の障害は次 addr への自動フォールオーバーで吸収される。
- **DB 読み出しエラーは無視**: Periodic モードの `cs.dc.Get()` エラーは `continue` でスキップされ、報告インターバル後に再試行される。永続的な DB 接続断でも `publishRun` は終了しない（ストリームは維持されたまま空送信が続く）。
- **未知フィールドはエラー扱い**: `DestinationGroup` / `Subscription` エントリに未知フィールドが含まれると エラーが返り、エントリ全体が登録されない。`Global` は unknown フィールドを静かに無視する点と対照的。
