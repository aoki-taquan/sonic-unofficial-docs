# gnmi-dialin Phase B — 書込み順依存スキャンノート

調査日: 2026-05-19
対象ページ: `docs/reference/config-db/gnmi-dialin.md`
フェーズ: Phase B (書込み順依存・タイミング依存)

## 調査対象ソース

| ファイル | リポジトリ | SHA | 役割 |
|---------|-----------|-----|------|
| `dockers/docker-sonic-gnmi/gnmi-native.sh` | sonic-net/sonic-buildimage | 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd | 起動スクリプト。CONFIG_DB を 1 回読んでフラグを組み立てる |
| `telemetry/telemetry.go` | sonic-net/sonic-gnmi | eb635b7679b260c3fd0786a6d0734fc8e82c9a22 | gNMI サーバ本体。フラグパース後に fsnotify で証明書をウォッチ |

## 検出した順序依存・タイミング依存

### 1. CONFIG_DB は起動時の 1 回読み取りのみ — hot reload なし

- `gnmi-native.sh` は `sonic-cfggen -d -t $TELEMETRY_VARS_FILE` (L19) と `sonic-db-cli CONFIG_DB hget` (L88, L93) で CONFIG_DB を読み取る。
- 読み取りはスクリプト実行時の **1 回のみ**。その後は `exec /usr/sbin/telemetry ${TELEMETRY_ARGS}` (L150) でバイナリを起動し、スクリプトはプロセスを引き渡す。
- **順序依存**: CONFIG_DB の `GNMI|gnmi` / `GNMI|certs` / `DEVICE_METADATA|localhost` / `MGMT_VRF_CONFIG|vrf_global` への変更は、コンテナを再起動するまで `telemetry` バイナリへ反映されない。config が変わっても running config は旧値のまま。
- evidence: `gnmi-native.sh:19-22`, `gnmi-native.sh:150`

### 2. 証明書ファイルは fsnotify で動的リロード — CONFIG_DB は非連動

- `telemetry` バイナリは `startGNMIServer()` 内で `iNotifyCertMonitoring()` を goroutine 起動し、証明書ファイルへの `CloseWrite` / `MovedTo` / `Create` イベントを監視する (telemetry.go:340-400)。
- 証明書ファイルが更新されると `serverControlSignal <- ServerStart` が送られ、gRPC サーバが再ビルドされる (telemetry.go:378-379)。
- **順序依存**: 証明書ファイルの書き込みと gRPC サーバ再起動の間には `iNotifyCertMonitoring` が証明書ペアの妥当性を検証する待機窓が存在する。検証中は旧サーバが継続稼働し、新サーバへの切替は検証成功後に行われる (telemetry.go:371-379)。
- **注意**: `GNMI|certs` の CONFIG_DB 値は起動時にシェル変数へコピー済み。その後 CONFIG_DB の `certs` が変わっても `iNotifyCertMonitoring` はファイルシステム変更のみを監視するため、「CONFIG_DB を書き換えただけでは再読み込みは起きない」。
- evidence: `telemetry.go:452-457`, `telemetry.go:340-400`

### 3. SmartSwitch / MGMT_VRF の読み取り順序

- `gnmi-native.sh` は `DEVICE_METADATA|localhost.subtype` を `sonic-db-cli` で読み取り (L88)、次に `MGMT_VRF_CONFIG|vrf_global.mgmtVrfEnabled` を読み取る (L93)。どちらも `sonic-cfggen` より後に呼ばれるが、`GNMI` テーブル読み取りよりは後 (L19-22 vs L88, L93)。
- **順序依存なし**（並列扱い可能）: これら 2 つの読み取りは独立しており、双方が存在する場合は両フラグが付与される。ただし、両値ともに起動時スナップショットである点は同じ。
- evidence: `gnmi-native.sh:86-95`

### 4. VRF 有効時の gRPC listen 順序

- `--vrf mgmt` フラグが付与された場合、`telemetry` は管理 VRF 内でポートをバインドする。
- **前提条件**: 管理 VRF インタフェース (`mgmt`) が `up` 状態にある必要がある。管理 VRF が未確立の状態でバインドを試みると telemetry バイナリが起動エラーになる。
- この依存は CONFIG_DB だけでは制御できない（ネットワーク namespace の準備タイミングに依存）。
- evidence: `gnmi-native.sh:93-95`

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | CONFIG_DB `GNMI` 読み取り → telemetry バイナリ起動 | 強制先行（1 回限り） | 設定変更後はコンテナ再起動が必要 |
| 2 | 証明書ファイル更新 → iNotify 検証 → gRPC サーバ再起動 | 非同期（検証待機窓あり） | 証明書更新後は検証成功まで旧サーバが継続稼働 |
| 3 | SmartSwitch / MGMT_VRF 読み取り | 独立（並列可） | 起動時スナップショット; 動的変更は不可 |
| 4 | 管理 VRF `up` → VRF 内 gRPC バインド | 外部依存（ネットワーク NS） | container startup 前に mgmt VRF が up であること |

## ページ反映方針

- `<!-- ordering -->` ブロックを `<!-- ref-triangle:start -->` セクションの直前に挿入する。
- 既存の `<!-- defaults -->` / `<!-- value-behavior -->` / `<!-- cdb-mermaid -->` / `<!-- cdb-exceptions -->` は触らない。
- サマリ表 + 主要制約の散文（依存 #1 / #2 を主軸）を含める。
