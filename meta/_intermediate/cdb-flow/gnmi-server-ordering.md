# gnmi-server — Phase B ordering 調査ノート

## 調査対象ソース

- `sonic-buildimage/dockers/docker-sonic-gnmi/gnmi-native.sh` (sha: 9ea932ec)
- `sonic-gnmi/telemetry/telemetry.go` (sha: eb635b76)
- `sonic-gnmi/dialout/dialout_client/dialout_client.go` (sha: eb635b76)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-gnmi.yang` (sha: 9ea932ec)

## 読み取りモデル

### GNMI / GNMI_CLIENT_CERT (dial-in サーバ)

`gnmi-native.sh` は **起動時に 1 回だけ** `sonic-cfggen -d -t telemetry_vars.j2` で CONFIG_DB をスナップショット読み取りする。
その後 `telemetry` プロセスを `exec` で置き換え、以後は CONFIG_DB を一切監視しない。
変更を反映させるにはコンテナ再起動が必要。

### TELEMETRY_CLIENT (dial-out クライアント)

`dialout_client.go` は起動後に CONFIG_DB の keyspace notification を購読する:
```
pattern = "__keyspace@<dbn>__:TELEMETRY_CLIENT|*"
```
`Global` / `DestinationGroup_*` / `Subscription_*` キーの変更を受信するたびに
`processTelemetryClientConfig()` を呼び出し、ランタイムで接続先を更新する。

## 順序依存の検出

### 依存 #1: GNMI|certs → GNMI|gnmi (TLS モード, 起動時)

`gnmi-native.sh` の実行フロー:
1. CERTS ブロック (`GNMI|certs`) を読み込み → `--server_crt` / `--server_key` を組み立て
2. GNMI ブロック (`GNMI|gnmi`) を読み込み → `--port` を組み立て
3. `telemetry` プロセスを exec

TLS モード (`noTLS=false`, `--insecure` 不使用) では、スクリプトが `server_crt` / `server_key`
を未取得のまま `telemetry` を起動すると `telemetry.go:252-258` でエラー終了する。
YANG では `GNMI|certs` と `GNMI|gnmi` は独立したエントリだが、**certs を先に書かなければ
起動スクリプト実行時に TLS 引数が欠落**する。

- 影響フェーズ: 起動時のみ (gnmi-native.sh は一度しか実行されない)
- 緩和策: 両エントリ揃ったあとにコンテナを起動 (supervisord 経由) すること

### 依存 #2: DEVICE_METADATA / MGMT_VRF_CONFIG → GNMI 起動 (起動時)

gnmi-native.sh は `DEVICE_METADATA|localhost.subtype` と `MGMT_VRF_CONFIG|vrf_global.mgmtVrfEnabled`
を直接 `sonic-db-cli` で取得し、それぞれ ZMQ / VRF 引数を組み立てる (行 89-98)。
GNMI テーブル自体にフィールドはなく、これらは独立参照。GNMI テーブルより先に確定している前提。

- 影響フェーズ: 起動時のみ
- 緩和策: 通常は `DEVICE_METADATA` は初期プロビジョニング時に必ず設定済み

### 依存 #3: TELEMETRY_CLIENT|DestinationGroup_* → Subscription_* (ランタイム)

`processTelemetryClientConfig()` の Subscription 処理 (dialout_client.go:583-641):
```go
if cs.destGroupName == "" {
    // not destination configured, just return (silent no-op)
    return nil
}
```
`dst_group` が参照する `DestinationGroup_<name>` がまだ登録されていない場合、
`DestGrp2ClientSubMap[cs.destGroupName]` は空スライスとなる。Subscription は登録されるが
DestinationGroup が存在しないため接続インスタンスは生成されない。

**先行必須**: `DestinationGroup_<name>` エントリを書いてから `Subscription_<name>` を書くこと。
逆順でも CONFIG_DB エラーにはならないが、SubscriptionGroup が silent no-op となり
実際のテレメトリ送信が開始されない。後から DestinationGroup を追加してもランタイム更新で
自動回復する (keyspace 通知で再処理)。

### 依存 #4: TELEMETRY_CLIENT|Global → DestinationGroup / Subscription (推奨)

`DialOutRun()` 起動時に初期 `clientCfg` を `clientCfg = ccfg` でセットし、その後
keyspace notification ループに入る。ランタイムで `Global` エントリが来た場合は
全 DestinationGroup の接続を再起動する (`closeDestGroupClient` + `setupDestGroupClients`)。
Global が後から来ると全接続が一時切断→再接続するため、**推奨順序は Global → DestGroup → Subscription**。

## 結論

| # | 依存関係 | 方向 | 強度 |
|---|----------|------|------|
| 1 | `GNMI\|certs` (server_crt/server_key) → `GNMI\|gnmi` 書込み → コンテナ起動 | 強制先行 (TLS モード) | 起動時のみ |
| 2 | `DEVICE_METADATA` / `MGMT_VRF_CONFIG` → gnmi コンテナ起動 | 強制先行 | 起動時のみ |
| 3 | `TELEMETRY_CLIENT\|DestinationGroup_<n>` → `Subscription_<n>` | **強制先行** (silent no-op 回避) | ランタイム |
| 4 | `TELEMETRY_CLIENT\|Global` → DestGroup → Subscription | 推奨 (接続フラップ回避) | ランタイム |
