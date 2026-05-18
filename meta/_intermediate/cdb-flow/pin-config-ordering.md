# P4RT テーブル (PINS p4rt 設定) — Phase B 書込み順依存スキャンノート

対象テーブル: `CONFIG_DB P4RT` (`P4RT|certs`, `P4RT|p4rt_app`)
Consumer: `p4rt.sh` → `sonic-cfggen -d -t p4rt_vars.j2` → `p4rt` バイナリ起動引数変換
スキャン範囲: `p4rt.sh` L1–99, `p4rt_vars.j2` L1–5

---

## 検出した順序依存・タイミング依存

### 1. 起動時単回読込み（ライブリロードなし）

- `p4rt.sh` L13: `sonic-cfggen -d -t ${P4RT_VARS_FILE}` で CONFIG_DB を**一度だけ**読み込む。以降は DB を再参照しない。
- 順序依存: `P4RT|certs` および `P4RT|p4rt_app` のエントリは **`p4rt` コンテナ起動前**に CONFIG_DB に存在しなければ反映されない。起動後に DB を更新しても `systemctl restart p4rt` を実行するまで有効にならない。
- evidence: `p4rt.sh:L13`

### 2. `P4RT|certs` 存否チェック → `DEVICE_METADATA|localhost|x509` フォールバック順序

- `p4rt_vars.j2` L2–4: テンプレートは `P4RT["certs"]` → `P4RT["p4rt_app"]` → `DEVICE_METADATA["x509"]` の順で評価し、`p4rt.sh` に渡す JSON を構築する。
- `p4rt.sh` L21–57: `${CERTS}` が非空なら `P4RT|certs` を優先使用し、空であれば `${X509}` （= `DEVICE_METADATA|localhost|x509`）を参照する。両方が空なら `--use_insecure_server_credentials` にフォールバックする。
- 順序依存: **`P4RT|certs` の存否が `DEVICE_METADATA|localhost|x509` の参照可否を決定する**。両テーブルが起動前に存在する場合、`P4RT|certs` が常に優先される（`DEVICE_METADATA|localhost|x509` は無視）。
- evidence: `p4rt_vars.j2:L2–4`, `p4rt.sh:L21–57`

### 3. `server_crt` / `server_key` の同時存在必須

- `p4rt.sh` L22–28: `${CERTS}` 内で `server_crt` と `server_key` の**両方**が非空かどうかをチェックする。どちらか一方でも空の場合は TLS が有効化されず `--use_insecure_server_credentials` が付与される（エラー終了ではなく insecure 起動）。
- 順序依存: `P4RT|certs` を CONFIG_DB に書き込む際は `server_crt` と `server_key` を**アトミックに（同一コマンドで）書き込む**こと。片方だけ先に書き込んで `p4rt` を起動した場合、意図せず平文 gRPC で起動してしまう。
- evidence: `p4rt.sh:L22–28`

### 4. `ca_crt` → `cert_crl_dir` の依存

- `p4rt.sh` L30–37: `cert_crl_dir` を有効にするには `ca_crt` が非空であることが前提。`ca_crt` が空の場合、`cert_crl_dir` があっても CRL チェックの引数は付与されない。
- 順序依存: CRL チェックを有効にするには `ca_crt` と `cert_crl_dir` を同時に設定する必要がある（`ca_crt` なしの `cert_crl_dir` 単独設定は無効）。
- evidence: `p4rt.sh:L30–37`
