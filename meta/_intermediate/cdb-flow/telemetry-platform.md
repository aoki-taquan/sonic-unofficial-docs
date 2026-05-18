# TELEMETRY — Phase H プラットフォーム差スキャンノート

対象テーブル: `TELEMETRY`
スキャン範囲: `telemetry.sh`、`docker-telemetry-entry.sh`、`telemetry.go`、`server.go`、`sonic_db_config/db_config.go`、`sonic_data_client/json_client.go` を ASIC/platform/namespace/VOQ/chassis キーワードで grep + 精読

---

## 調査結果

### 1. ASIC 種別（Broadcom / Mellanox / Marvell / Innovium 等）

`telemetry.sh`、`server.go`、`telemetry.go` に ASIC 種別を参照するコードはない。
`gnmi_server` は SAI / ASIC_DB に直接アクセスせず、CONFIG_DB / STATE_DB / DATA_DB / COUNTERS_DB を
Redis プロトコルで読み取るのみ。

- grep: `telemetry.sh`, `server.go`, `telemetry.go` を "broadcom|mellanox|marvell|innovium|asic_id|chip" で検索 → 0 ヒット

### 2. multi-asic（namespace 対応）

`sonic_db_config/db_config.go` は namespace マップを管理し、multi-asic 環境では複数の
redis インスタンスを扱う。しかし `TELEMETRY` テーブル自体は常に host namespace の CONFIG_DB
(db 4) にある 1 エントリであり、ASIC namespace 数に依存しない。

gNMI クライアントが購読する**データパス**（COUNTERS_DB 等）は namespace 指定で multi-asic の
各 ASIC インスタンスを参照できるが、`TELEMETRY` テーブルの内容（port, cert, auth 設定等）は
変わらない。

- grep: `server.go` を "namespace|multi_npu|is_multi_npu" で検索 → 0 ヒット

### 3. VOQ chassis（supervisor + line cards）

VOQ 構成固有のコードは `telemetry.sh` / `server.go` / `telemetry.go` に存在しない。
各ラインカードで `docker-sonic-telemetry` コンテナが独立に動作するため、
`TELEMETRY` テーブルはラインカードごとに独立した CONFIG_DB に存在する。

- grep: `telemetry.sh`、`server.go` を "VOQ|chassis|linecard|supervisor" で検索 → 0 ヒット

### 4. platform 固有 Dockerfile / テンプレート分岐

`docker-sonic-telemetry/Dockerfile.j2` に platform 条件分岐 (`{%if platform%}`) は存在しない。
`telemetry_vars.j2` は `TELEMETRY` / `DEVICE_METADATA` のみ参照し、platform 名を参照しない。

### 5. k8s 環境 (launch_by=k8s)

`docker-telemetry-entry.sh` の Part 1 は k8s 起動時のみ `/usr/share/sonic/platform` シンボリックリンクを生成する。これは HW スケルトン（HWSKU / platform ディレクトリ）へのパス設定であり、`TELEMETRY` テーブルの処理とは無関係。

---

## 結論

`TELEMETRY` テーブルの設定・処理において、ASIC 種別・multi-asic・VOQ chassis 構成・ベンダー固有挙動は検出されなかった。
