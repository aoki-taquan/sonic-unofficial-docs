# subscription-config — Phase B 書込み順依存スキャンノート

対象テーブル: `TELEMETRY_CLIENT|Global` / `TELEMETRY_CLIENT|DestinationGroup_<name>` / `TELEMETRY_CLIENT|Subscription_<name>`
Consumer: `dialout_client.go` (`sonic-gnmi/dialout/dialout_client/dialout_client.go`)
スキャン範囲: `DialOutRun()`, `processTelemetryClientConfig()`, `setupDestGroupClients()`, `closeDestGroupClient()`, `NewInstance()` 全行精読

---

## 検出した順序依存・タイミング依存

### 1. DestinationGroup → Subscription の先行必須（最重要）

`Subscription_<name>` エントリを処理する際、`cs.destGroupName` に指定した DestinationGroup が
`destGrpNameMap` に存在しない場合、`NewInstance()` は即座に失敗して接続を試みない：

```go
dests, ok := destGrpNameMap[cs.destGroupName]
if !ok {
    log.V(2).Infof("Destination group %v doesn't exist", cs.destGroupName)
    return fmt.Errorf("Destination group %v doesn't exist", cs.destGroupName)
}
```

（`dialout_client.go:181-184`）

- **順序依存**: `TELEMETRY_CLIENT|DestinationGroup_<name>` を先に CONFIG_DB に書いてから
  `TELEMETRY_CLIENT|Subscription_<name>` を書かなければ、Subscription が接続されない。
- 逆順で書いた場合、Subscription は `cs.destGroupName == "" → return nil` でサイレントにスキップ
  されるか、`DestinationGroup X doesn't exist` エラーで NewInstance が失敗する。
- `DialOutRun()` の初期ロード時は `redisDb.Keys(dbkey_prefix+"*")` の結果順序が保証されないため、
  CONFIG_DB の SET 順ではなく Redis の key 列挙順に依存する（`dialout_client.go:707-714`）。
  このため、初回起動時は DestinationGroup が先に処理されるとは限らない。
  ただし Global 変更時に `setupDestGroupClients()` が再呼び出しされるため最終的には収束する。

### 2. Global 変更 → 全 DestinationGroup の再起動

`Global` エントリが変更されると、`processTelemetryClientConfig()` は全 DestinationGroup に対して
`closeDestGroupClient()` → `setupDestGroupClients()` を順に呼ぶ：

```go
// Apply changes to all running instances
for grpName := range destGrpNameMap {
    closeDestGroupClient(grpName)
    setupDestGroupClients(ctx, grpName)
}
```

（`dialout_client.go:509-512`）

- **副作用**: `Global` の任意フィールド（`retry_interval`, `src_ip`, `encoding`, `unidirectional`）を
  1 つでも変更すると、**全 Subscription のダイアルアウト接続が一時切断・再接続**される。
  変更中に送信途中のテレメトリメッセージは破棄される可能性がある。
- **推奨順序**: Global 設定は Subscription 運用開始前に確定しておく。
  運用中の変更は全接続リセットを伴うことを前提に計画する。

### 3. DestinationGroup 変更 → 参照 Subscription の再起動

`DestinationGroup_<name>` エントリが変更されると、そのグループを参照する全 Subscription が
`closeDestGroupClient()` で停止され、`setupDestGroupClients()` で再起動される：

```go
closeDestGroupClient(destGroupName)
// ...
destGrpNameMap[destGroupName] = dests
setupDestGroupClients(ctx, destGroupName)
```

（`dialout_client.go:520`, `549-550`）

- **順序依存**: `DestinationGroup` の `dst_addr` を変更する場合、参照中の Subscription が
  一時切断される。変更完了後に自動再接続するため最終的には収束するが、
  接続切断中はテレメトリ送信が停止する。

### 4. DestinationGroup DEL → 参照 Subscription のブロック

`DestinationGroup` を DEL しようとした際、`DestGrp2ClientSubMap[destGroupName]` に
参照している Subscription が存在する場合はエラーを返し DEL を拒否する：

```go
if _, ok := DestGrp2ClientSubMap[destGroupName]; ok {
    log.V(1).Infof("%v is being used: %v", destGroupName, DestGrp2ClientSubMap)
    return fmt.Errorf("%v is being used: %v", destGroupName, DestGrp2ClientSubMap)
}
```

（`dialout_client.go:523-525`）

- **順序依存（DEL 時）**: `DestinationGroup` を削除する場合は、先に参照している
  `Subscription_<name>` エントリを DEL してから `DestinationGroup` を DEL する必要がある。
  逆順では DestinationGroup DEL が失敗する。

### 5. 初期ロードの key 列挙順の非決定性

`DialOutRun()` は起動時に `redisDb.Keys(dbkey_prefix+"*")` で CONFIG_DB の全 TELEMETRY_CLIENT キーを
列挙してから `processTelemetryClientConfig()` を順に呼ぶ（`dialout_client.go:707-714`）。
Redis の `Keys` コマンドは返却順序を保証しないため、`Subscription_<name>` が
`DestinationGroup_<name>` より先に処理される場合がある。

その際の挙動:
- `cs.destGroupName` が `destGrpNameMap` に未登録 → `NewInstance()` が `Destination group X doesn't exist` エラーを返す
- ただし `configMu` ロックのスコープ内でエラー処理されるため、その後の DestinationGroup 処理が完了した時点で状態が矛盾する（Subscription は登録済みだが接続なし）
- 修復トリガー: Global エントリが存在すれば Global の処理で `setupDestGroupClients()` が全グループに対して呼ばれる。ただし Global エントリがない構成では自動修復されない

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | DestinationGroup → Subscription | **強制先行**（後述順では NewInstance 失敗） | Global 変更 or 手動 Subscription 再設定で収束 |
| 2 | Global 変更 → 全 DestinationGroup/Subscription 再起動 | 即時（全接続リセット） | 運用開始前に Global 確定 |
| 3 | DestinationGroup 変更 → 参照 Subscription 再接続 | 即時（切断 → 自動再接続） | 変更中はテレメトリ送信停止 |
| 4 | Subscription DEL → DestinationGroup DEL | **強制先行**（逆順は DestGrp DEL 失敗） | Subscription を先に DEL |
| 5 | 初期ロード key 列挙順の非決定性 | startup 時のみ | Global エントリ存在で自動収束 |

## 証跡

- `sonic-gnmi/dialout/dialout_client/dialout_client.go:172-210` (`NewInstance`)
- `sonic-gnmi/dialout/dialout_client/dialout_client.go:436-460` (`closeDestGroupClient`, `setupDestGroupClients`)
- `sonic-gnmi/dialout/dialout_client/dialout_client.go:464-644` (`processTelemetryClientConfig`)
- `sonic-gnmi/dialout/dialout_client/dialout_client.go:646-746` (`DialOutRun`)
