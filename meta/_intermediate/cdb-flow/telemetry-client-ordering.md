# TELEMETRY_CLIENT — Phase B 書込み順依存スキャンノート

対象テーブル: `TELEMETRY_CLIENT`
Consumer: `sonic-gnmi` (`dialout/dialout_client/dialout_client.go`) の `processTelemetryClientConfig()` / `DialOutRun()`
スキャン範囲: `DialOutRun()` 全行、`processTelemetryClientConfig()` 全行、`setupDestGroupClients()` / `closeDestGroupClient()` 精読
スキャン日: 2026-05-18

---

## 検出した順序依存・タイミング依存

### 1. DestinationGroup → Subscription 先行必須（書き込み順）

- 起動時の一括読み込み (`DialOutRun` L705-714) は Redis `KEYS` コマンドの返却順序に依存する。`KEYS` はランダム順で返すため、`DestinationGroup_*` より先に `Subscription_*` が処理された場合、`destGrpNameMap[destGroupName]` が未登録のため `setupDestGroupClients()` で接続が確立されない中間状態が生じる。
- 最終的には `DestinationGroup_` が処理された時点で接続が確立されるが、起動直後に接続確立が遅れる可能性がある。
- オンライン変更時は keyspace notification 経由で 1 キーずつ通知されるため順序は制御可能。
- **推奨順**: `DestinationGroup_<name>` を先に書き込んでから `Subscription_<name>` を書き込む。
- evidence: `dialout_client.go` L705-714 (Keys iteration), L514-551 (DestinationGroup 処理), L552-641 (Subscription 処理)

### 2. Subscription DEL → DestinationGroup DEL（削除順序）

- `DestinationGroup_<name>` を DEL しようとした際、`DestGrp2ClientSubMap[destGroupName]` にエントリが残っている場合は `"%v is being used"` エラーで拒否される (L523-526)。
- `Subscription_<name>` の DEL 処理では `DestGrp2ClientSubMap` から自身を除去する (L566-573)。
- **強制順序**: Subscription を全て DEL してから DestinationGroup を DEL する。逆順は拒否される。
- evidence: `dialout_client.go` L522-528, L566-573

### 3. Global 変更 → 全DestinationGroup クライアント再起動

- `Global` キーへの HSET 処理末尾で `destGrpNameMap` の全グループに対して `closeDestGroupClient()` → `setupDestGroupClients()` を実行する (L509-512)。
- すべての gRPC dial-out 接続が一時断してから再確立される。
- **推奨順**: `Global` の `src_ip` / `retry_interval` は `DestinationGroup_` / `Subscription_` を投入する前に書いておくことで接続再起動を回避できる。起動後に `Global` を変更すると全接続が一斉再起動される。
- evidence: `dialout_client.go` L483-513

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `TELEMETRY_CLIENT\|DestinationGroup_<name>` → `TELEMETRY_CLIENT\|Subscription_<name>` | **推奨先行**（起動時は KEYS 順不定のため逆順では中間状態あり） | 最終的には自動回復。オンライン変更は通知順を制御可能 |
| 2 | `Subscription_` DEL → `DestinationGroup_` DEL | **強制先行**（逆順は `is being used` エラーで拒否） | Subscription を全 DEL してから DestinationGroup を DEL |
| 3 | `Global` 先書き → `DestinationGroup_` / `Subscription_` 書き込み | **推奨先行**（逆順では Global 変更時に全接続再起動コスト発生） | 機能上は逆順でも最終的に動作する |
