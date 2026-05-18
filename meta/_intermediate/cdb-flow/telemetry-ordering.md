# TELEMETRY — Phase B 書込み順依存スキャンノート

対象テーブル: `TELEMETRY`
Consumer: `telemetry` / `gnmi` (`docker-sonic-telemetry` / `docker-gnmi`)
スキャン範囲: `telemetry.sh`、`docker-telemetry-entry.sh`、`supervisord.conf`、`telemetry.service`、`telemetry.go`、`server.go` 全行精読

---

## 検出した順序依存・タイミング依存

### 1. `FEATURE|telemetry` が STATE_DB に存在・`enabled` でないとコンテナが起動しない

`docker-telemetry-entry.sh` (L39-48) は `redis-cli -n 4 HGET "FEATURE|telemetry" state` の値が
`"enabled"` になるまで 10 秒ごとにポーリングして待機する。`CONFIG_DB` への `TELEMETRY` 書き込みが
完了していても、`STATE_DB` の `FEATURE|telemetry.state` が `"enabled"` でなければコンテナはアイドル状態を維持する。

- evidence: `docker-sonic-telemetry/docker-telemetry-entry.sh` L39-48

### 2. `TELEMETRY` は起動時の一括読み込みのみ — CONFIG_DB に事前存在が必須

`telemetry.sh` (L40) は `sonic-cfggen -d -t telemetry_vars.j2` を一度だけ実行して
`TELEMETRY|certs` / `TELEMETRY|gnmi` / `DEVICE_METADATA|x509` の値を取得し、
コマンドライン引数として `/usr/sbin/telemetry` プロセスに渡す。

これは**起動時の一括読み込み**であり、実行中の CONFIG_DB 変更はプロセス再起動なしには反映されない。
`TELEMETRY|gnmi` エントリが CONFIG_DB に存在しない場合、`telemetry.sh` は `port` にデフォルト値
`8080` を使用して起動する（L83-91 のフォールバック処理）。

- **順序依存**: `TELEMETRY|gnmi` / `TELEMETRY|certs` は telemetry コンテナ起動**前**に CONFIG_DB に
  書き込んでおく必要がある。起動後の変更はコンテナ再起動（`systemctl restart telemetry`）まで無視される。
- evidence: `docker-sonic-telemetry/telemetry.sh` L40, L83-91

### 3. `TELEMETRY|certs` の証明書ファイルが先行存在必須

`server.go` `SrvAdvConfig()` (L381-425) は起動時に TLS 証明書を検証する。
`server_crt` / `server_key` のいずれかが設定されているが対応するファイルが存在しない場合、
`"server certificate or key file path is empty"` または stat エラーを返してサーバが起動しない。

`client_auth=true` を設定する場合は `ca_crt` に指定したファイルも事前に存在している必要がある。

- **順序依存**: 証明書ファイルを filesystem に配置した**後**に `TELEMETRY|certs` を書き込み、
  その**後**に telemetry コンテナを起動する。
- evidence: `sonic-gnmi/gnmi_server/server.go` L395-414

### 4. `GNMI_CLIENT_CERT` テーブルがランタイムに参照される — 先行不要だが注意

`user_auth=cert` 設定時、`telemetry.sh` (L147-148) は `--config_table_name GNMI_CLIENT_CERT` を
引数に追加する。`server.go` `ClientCertAuthenAndAuthor()` (L792) は接続ごとに CONFIG_DB から
`GNMI_CLIENT_CERT` テーブルを参照してクライアント証明書の CN とロールを検証する。

`GNMI_CLIENT_CERT` はランタイムに都度読まれるため、telemetry 起動前に存在する必要はないが、
クライアントが接続する前には存在している必要がある。

- **順序依存**: `TELEMETRY|gnmi.user_auth=cert` 設定時は、クライアントの接続前までに
  `GNMI_CLIENT_CERT|<common-name>` エントリを CONFIG_DB に書いておく必要がある。
- evidence: `sonic-gnmi/gnmi_server/server.go` L792, L797

### 5. systemd サービスレベルの順序制約

`telemetry.service` は `Requires=database.service`、`After=database.service swss.service syncd.service`
を宣言している（sidecar 版）。これにより `database` コンテナ（redis）および `swss`/`syncd` が
起動している状態でのみ telemetry が起動する。

- evidence: `docker-telemetry-sidecar/systemd_scripts/telemetry.service` L3-4

### 6. コンテナ内の supervisord 起動順序

コンテナ内では `supervisord_dependent_startup` プラグインにより以下の順序が強制される:

1. `rsyslogd` → 2. `start` (container_startup.py) → 3. `telemetry` → 4. `dialout`

`dialout` プロセス（dial-out クライアント）は `telemetry:running` 状態を待ってから起動する。

- evidence: `docker-sonic-telemetry/supervisord.conf` L56, L68

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `STATE_DB FEATURE|telemetry.state == "enabled"` → コンテナ起動 | **強制先行**（ポーリング待機） | `featmgrd` が FEATURE テーブルを管理するため通常は自動保証 |
| 2 | `TELEMETRY|gnmi` / `TELEMETRY|certs` → コンテナ起動 | **推奨先行**（起動時一括読み込み） | 欠如時は `port=8080`/`noTLS` でフォールバック起動 |
| 3 | 証明書ファイル (`server_crt`/`server_key`/`ca_crt`) → コンテナ起動 | **強制先行**（ファイル不在でサーバ不起動） | ファイル不在時の回復はコンテナ再起動が必要 |
| 4 | `GNMI_CLIENT_CERT|<cn>` → クライアント接続 (`user_auth=cert` 時) | 接続前に必要（ランタイム都度参照） | 接続前に追加可能、削除は即時効果 |
| 5 | `database.service` + `swss.service` + `syncd.service` → `telemetry.service` | systemd 依存（自動保証） | systemd が順序を管理 |
| 6 | `telemetry` プロセス起動 → `dialout` プロセス起動 | コンテナ内 supervisord で強制 | `telemetry:running` を supervisord が待機 |
