# P4RT テーブル (PINS p4rt 設定) — Phase D 失敗挙動スキャンノート

対象テーブル: `CONFIG_DB P4RT` (`P4RT|certs`, `P4RT|p4rt_app`)
Consumer: `p4rt.sh` → `sonic-cfggen -d -t p4rt_vars.j2` → `p4rt` バイナリ
スキャン範囲: `p4rt.sh` L1–99, `p4rt_vars.j2` L1–5

---

## 検出した失敗経路

### 1. テンプレートファイル不在（起動即 exit）

- `p4rt.sh` L6–9: `${P4RT_VARS_FILE}` (`/usr/share/sonic/templates/p4rt_vars.j2`) が存在しない場合、`exit ${EXIT_P4RT_VARS_FILE_NOT_FOUND}` (=1) で即終了。
- 影響: `p4rt` プロセスが起動せず gRPC サーバは立ち上がらない。`systemctl` が failed 状態になる。
- evidence: `p4rt.sh:L6–9`

### 2. `P4RT|certs` の部分書込み（insecure 起動へのサイレントフォールバック）

- `p4rt.sh` L22–28: `server_crt` / `server_key` のいずれかが空文字列の場合、エラー終了ではなく `--use_insecure_server_credentials` を付与して平文 gRPC で起動する。
- 影響: TLS 有効のつもりで片方だけ設定した場合に意図せず平文起動になる。ログ出力なし（syslog への警告もない）。
- evidence: `p4rt.sh:L24–25`

### 3. `P4RT|certs` も `DEVICE_METADATA|localhost|x509` も不在（insecure 起動）

- `p4rt.sh` L55–57: `${CERTS}` も `${X509}` も空の場合、`--use_insecure_server_credentials` にフォールバックして平文 gRPC で起動する。
- 影響: 証明書が未設定のまま gRPC サーバが public に listen している場合、認証なしで接続可能になる。
- evidence: `p4rt.sh:L55–57`

### 4. `p4rt_unix_socket` のディレクトリ不在（自動 mkdir）

- `p4rt.sh` L92–96: `p4rt_unix_socket` が設定されている場合、`dirname` でディレクトリパスを取得し、存在しなければ `mkdir -p` で自動作成する。
- 影響: 失敗ではなく自動回復。ただし親ディレクトリへの書き込み権限がない場合は `mkdir -p` が失敗し、その後の `p4rt` バイナリ起動時に socket bind エラーになる（`p4rt.sh` 自体は exit しない）。
- evidence: `p4rt.sh:L92–96`

### 5. 不明フィールドのサイレント無視

- `p4rt.sh` の各フィールド取得は `jq -r '.field // empty'` パターンを使用する。未知フィールドや typo フィールドは `empty` として評価され、対応する起動引数が付与されないだけで、エラー終了も警告出力もない。
- 影響: フィールド名の typo（例: `ports` と書いて `port` にならない）は検出されず、意図した設定が黙って無視される。YANG モデルが存在しないため CLI 経由の事前バリデーションもない。
- evidence: `p4rt.sh:L60–97`（全フィールド共通パターン）

---

## 失敗挙動サマリ

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `p4rt_vars.j2` テンプレートファイル不在 | `p4rt.sh:L6–9` | `exit 1`（gRPC サーバ未起動） | `"P4rt vars template file not found"` を stdout 出力 | `p4rt.sh:L8` |
| `server_crt` または `server_key` が空 | `p4rt.sh:L24–25` | `--use_insecure_server_credentials` で平文 gRPC 起動（エラーなし） | なし | `p4rt.sh:L25` |
| `P4RT\|certs` も `DEVICE_METADATA\|localhost\|x509` も不在 | `p4rt.sh:L55–57` | `--use_insecure_server_credentials` で平文 gRPC 起動（エラーなし） | なし | `p4rt.sh:L56` |
| `ca_crt` なしで `cert_crl_dir` のみ設定 | `p4rt.sh:L30–37` | `cert_crl_dir` が無視され CRL チェックなしで TLS 起動 | なし | `p4rt.sh:L30–37` |
| `p4rt_unix_socket` ディレクトリ不在 | `p4rt.sh:L92–96` | `mkdir -p` で自動作成（成功すれば問題なし） | なし（mkdir 失敗時は p4rt バイナリが socket bind エラー） | `p4rt.sh:L94–95` |
| 未知フィールド / typo フィールド | `p4rt.sh:L60–97` | 該当引数なしで起動（サイレント無視） | なし | 各 jq パターン |
