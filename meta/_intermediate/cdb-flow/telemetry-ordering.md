# TELEMETRY — Phase B 書込み順依存スキャンノート

対象テーブル: `TELEMETRY`
Consumer: `telemetry.sh` / `gnmi_server/server.go` (`sonic-gnmi`)
スキャン範囲: `telemetry.sh` 全行精読、`gnmi_server/server.go` L492-654、`supervisord.conf` 全行、`docker-telemetry-entry.sh` 全行、`telemetry.service.j2` 全行

---

## 検出した順序依存・タイミング依存

### 1. FEATURE テーブル先行必須 — telemetry コンテナ起動前提条件

- `docker-telemetry-entry.sh` L39-48: コンテナ起動直後に `redis-cli -n 4 HGET "FEATURE|telemetry" state` をポーリングし、`state == "enabled"` になるまで 10 秒ごとに待機する。
- `FEATURE|telemetry` エントリが CONFIG_DB (DB index 4) に存在しない、または `state != "enabled"` の場合、supervisord は起動せず `telemetry.sh` も実行されない。
- **順序依存**: `TELEMETRY` テーブルを設定する前に `FEATURE|telemetry.state = "enabled"` が CONFIG_DB に書かれていること。minigraph.py による自動生成（通常の起動フロー）ではこの順序が保証される。
- evidence: `docker-telemetry-entry.sh:39-48`

### 2. systemd サービス依存順 — database.service / swss.service が先行必須

- `telemetry.service.j2` L3-4: `Requires=database.service`、`After=database.service swss.service syncd.service`。
- telemetry サービスは `database.service` (Redis / CONFIG_DB) が起動し、さらに `swss.service` と `syncd.service` が起動してから開始する。
- `sonic.target` 達成後にも `After=sonic.target` で制約が追加される。
- **順序依存**: TELEMETRY テーブルの読み込みは `database.service` が完全に Ready になった後。Redis が起動前に telemetry が CONFIG_DB を読もうとすることはない。
- evidence: `telemetry.service.j2:3-4`, `gnmi.service.j2:3-4`

### 3. supervisord 内部起動順 — start:exited 待ちで telemetry.sh が実行される

- `supervisord.conf` 内プロセス起動順:
  1. `rsyslogd` (priority=1、autostart=false、`dependent_startup=true`)
  2. `start` = `/usr/bin/start.sh` (priority=2、`dependent_startup_wait_for=rsyslogd:running`)
  3. `telemetry` = `/usr/bin/telemetry.sh` (priority=3、`dependent_startup_wait_for=start:exited`)
  4. `dialout` (priority=4、`dependent_startup_wait_for=telemetry:running`)
- `telemetry.sh` は `start.sh` の正常終了後に起動される。`start.sh` は `container_startup.py` を呼んで FEATURE フラグ確認・バージョン整合チェックを行う。
- `dialout.sh` は `telemetry` プロセスが `running` 状態になってから起動する。dialout (gRPC dial-out) を有効にする場合は、先に gNMI サーバが listenしている必要がある。
- **順序依存**: `telemetry.sh` 実行前に `start.sh` が終了していること（FEATURE チェック完了が前提）。
- evidence: `supervisord.conf:31-68`

### 4. CONFIG_DB 読み込みは起動時一括 — runtime 変更は再起動まで無効

- `telemetry.sh` L40: `sonic-cfggen -d -t $TELEMETRY_VARS_FILE` により CONFIG_DB から `TELEMETRY|certs` / `TELEMETRY|gnmi` を一括読み込みする。これは `telemetry.sh` プロセス起動時に **1 回だけ** 実行される。
- `telemetry_vars.j2` はテンプレートベースで `TELEMETRY["certs"]` / `TELEMETRY["gnmi"]` / `DEVICE_METADATA["x509"]` を参照する。
- **順序依存**: `TELEMETRY` テーブルの内容は `telemetry.sh` の実行時点で確定している必要がある。実行後に CONFIG_DB を変更しても `gnmi_server` プロセスには反映されない（`systemctl restart telemetry` が必要）。
- evidence: `telemetry.sh:40-43`

### 5. TLS 証明書ファイルは server.go 起動前に存在必須

- `gnmi_server/server.go` `SrvAdvConfig()` L398-418: `os.Stat(cfg.CaCertFile)` / `os.Stat(cfg.SrvCertFile)` / `os.Stat(cfg.SrvKeyFile)` で証明書ファイルの存在を確認する。ファイルが存在しない場合は即エラーを返してサーバが起動しない。
- `telemetry.sh` L54-65: `server_crt` / `server_key` が空の場合は `--insecure` フラグで起動（TLS 無効化）。
- **順序依存**: TLS 有効で起動する場合、`TELEMETRY|certs` に設定されたパスの証明書ファイルが **telemetry.sh 実行時点** でファイルシステム上に存在していること。`minigraph.py` は `server_crt=/etc/sonic/telemetry/streamingtelemetryserver.cer` 等のデフォルトパスを書き込むが、そのファイルは事前にプロビジョニングされていなければならない。
- evidence: `gnmi_server/server.go:398-418`, `telemetry.sh:54-65`

### 6. GNMI_CLIENT_CERT テーブル — cert 認証時の先行必須テーブル

- `telemetry.sh` L148: `user_auth=cert` の場合、`--config_table_name GNMI_CLIENT_CERT` フラグを付与してサーバを起動する。
- gnmi_server は起動後に `GNMI_CLIENT_CERT` テーブルを参照してクライアント証明書の fingerprint チェックを行う。
- **順序依存**: `user_auth=cert` を設定する場合、`GNMI_CLIENT_CERT` エントリが CONFIG_DB に存在しないと接続時に認証失敗となる。`TELEMETRY|gnmi.user_auth=cert` を設定する前に `GNMI_CLIENT_CERT` エントリを書いておくことを推奨。
- evidence: `telemetry.sh:146-149`

### 7. DEVICE_METADATA|x509 フォールバック — legacy 証明書経路

- `telemetry_vars.j2` L4: `DEVICE_METADATA["x509"]` を参照する。`TELEMETRY["certs"]` が未設定の場合、`telemetry.sh` は `x509` フォールバック経路（L66-80）で `DEVICE_METADATA|x509.server_crt` / `server_key` / `ca_crt` を使用する。
- **順序依存**: `TELEMETRY|certs` が CONFIG_DB にない場合、`DEVICE_METADATA|x509` が書かれていること。どちらも未設定の場合は `--noTLS` フラグで起動（平文）。これはデグレードではなく設計上の動作。
- evidence: `telemetry_vars.j2:2-4`, `telemetry.sh:66-80`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `FEATURE\|telemetry.state=enabled` → telemetry コンテナ起動 | 先行必須（未設定は 10s ポーリング待機） | minigraph 生成フローでは自動保証 |
| 2 | `database.service` → telemetry.service 起動 | systemd After= 強制 | Redis 未起動で起動することはない |
| 3 | `start.sh:exited` → `telemetry.sh` 実行 | supervisord dependent_startup 強制 | FEATURE チェック完了が保証される |
| 4 | CONFIG_DB 書き込み完了 → `telemetry.sh` 起動（一括読み込み） | 起動時一括読み込みのため先行必須 | runtime 変更は `systemctl restart telemetry` で反映 |
| 5 | TLS 証明書ファイル配置 → `server_crt`/`server_key`/`ca_crt` 設定 | ファイル存在確認が先行必須 | 空の場合は `--insecure` フォールバック |
| 6 | `GNMI_CLIENT_CERT` エントリ → `user_auth=cert` 設定 | 推奨先行（欠如時は接続認証失敗） | サーバ再起動必須 |
| 7 | `DEVICE_METADATA\|x509` → `TELEMETRY\|certs` 未設定時の legacy フォールバック | どちらも未設定なら `--noTLS` 起動 | 設計上の縮退動作 |
