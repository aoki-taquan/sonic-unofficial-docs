# TELEMETRY_CLIENT — Phase D 失敗挙動スキャンノート

調査対象: `sonic-net/sonic-gnmi/dialout/dialout_client/dialout_client.go`
コミット: eb635b7679b260c3fd0786a6d0734fc8e82c9a22

## SET 処理の失敗経路

### Global キー

| 失敗条件 | 検出箇所 | 結果 | ログ | evidence |
|---|---|---|---|---|
| `op == "hdel"` — Global の DEL 操作 | `processTelemetryClientConfig()` L484-486 | `"Invalid delete operation for TELEMETRY_CLIENT|Global"` を返してエラー終了。既存設定は維持 | `log.V(2)` | L484-486 |
| `retry_interval` が uint64 に変換不可 | L494-499 | `"Invalid retry_interval <value>"` をログして `continue`（当該フィールドをスキップ）。旧 `RetryInterval` が維持される | `log.V(2)` | L494-499 |
| `src_ip` / `encoding` / `unidirectional` フィールドのパース失敗 | L489-506 | 型チェックなし。文字列をそのまま代入するか無視（encoding/unidirectional は強制固定値）。エラーを返さない | なし | L489-506 |
| Global 設定変更後 `setupDestGroupClients()` 内で `newClient()` タイムアウト | L508-512, L260-272 | gRPC Dial タイムアウト → `goto restart` で再試行。エラーは publishRun ゴルーチン内でログ (`log.V(1)`) のみ。processTelemetryClientConfig() はエラーを返さない | `log.V(1)` | L306-317 |

### DestinationGroup キー

| 失敗条件 | 検出箇所 | 結果 | ログ | evidence |
|---|---|---|---|---|
| 空の DestinationGroup 名 (`DestinationGroup_`) | L516-518 | `"Empty Destination Group name <key>"` を返してエラー終了 | なし（caller が受け取る） | L516-518 |
| DEL 対象が他 Subscription から参照中 (`DestGrp2ClientSubMap` に存在) | L522-525 | `"<name> is being used: <map>"` を返して DEL 拒否。Subscription を先に削除する必要あり | `log.V(1)` | L522-525 |
| `dst_addr` のアドレス検証失敗 (`Destination.Validate()`) | L538-541 | `"Invalid destination address <addrs>"` を返してエラー終了。既存 destGrpNameMap は更新されない | `log.V(2)` | L538-541 |
| `dst_addr` 以外の未知フィールドが含まれる場合 | L544-546 | `"Invalid DestinationGroup value <value>"` を返してエラー終了。dests が空のままなので destGrpNameMap 更新なし | `log.V(2)` | L544-546 |
| gRPC 接続失敗 (コレクタ到達不能 / タイムアウト) | `newClient()` L260-272 | `goto restart` で無限リトライ。コンテキストキャンセルまで継続。processTelemetryClientConfig() はエラーを返さない | `log.V(1)` | L314-316 |

### Subscription キー

| 失敗条件 | 検出箇所 | 結果 | ログ | evidence |
|---|---|---|---|---|
| 空の Subscription 名 (`Subscription_`) | L554-556 | `"Empty Subscription_ name <key>"` を返してエラー終了 | なし | L554-556 |
| `report_interval` が uint64 に変換不可 | L593-597 | `"Invalid report_interval <value>"` をログして `continue`（デフォルト 5000ms が維持される） | `log.V(2)` | L593-597 |
| `paths` が ygot StringToPath で parse 失敗 | L607-611 | `"Invalid paths <value>"` を返してエラー終了。Subscription は登録されない | `log.V(2)` | L607-611 |
| 未知フィールドが含まれる | L616-618 | `"Invalid field <field> value <value>"` を返してエラー終了 | `log.V(2)` | L616-618 |
| `dst_group` が未設定 (空文字列) | L622-624 | サイレントリターン (`return nil`)。Subscription が登録されない。エラーなし | なし | L622-624 |
| 参照先 DestinationGroup が未作成 (`DestGrp2ClientSubMap` に存在しない) | L627-636 | DestGrp2ClientSubMap に新エントリとして登録されるが、publishRun 内で `Destination group <name> doesn't exist` エラーが返って gRPC 接続が確立されない | `log.V(2)` | L450-460 |

## DEL 処理の失敗経路

DestinationGroup DEL 時の `is being used` チェックと Subscription DEL 時の `cancel()` 呼び出しは正常系と同一の失敗経路（上表参照）。

## retry / 復旧挙動補足

- **gRPC 接続失敗の無限 retry**: `publishRun()` は `goto restart` でコンテキストキャンセルまで無限再試行。コレクタが一時的に到達不能でも自動復旧する。
- **データ読み取りエラー (Periodic モード)**: `cs.dc.Get()` が失敗した場合 `continue` でスキップし次のポーリング周期を待つ（エラーログのみ）。
- **Stream モード gRPC Send 失敗**: `cs.Close()` → `cs.w.Wait()` → `time.Sleep(clientCfg.RetryInterval)` → `goto restart`。`RetryInterval == 0` の場合は即再試行になるため CPU スピン状態になりえる。
- **`processTelemetryClientConfig()` エラーは非致命的**: エラーを返しても `DialOutRun()` のイベントループは継続する。設定変更失敗が上位に伝播しない点に注意。
