# P4RT テーブル — Phase C 暗黙参照スキャンノート

対象テーブル: `P4RT`
Consumer: `p4rt.sh` + `p4rt_vars.j2` (`sonic-buildimage/dockers/docker-sonic-p4rt/`)
スキャン範囲: `p4rt_vars.j2` L1–5 (テンプレート全体), `p4rt.sh` L1–99 (スクリプト全体)

---

## 検出した暗黙参照

### 1. DEVICE_METADATA|localhost|x509 — TLS フォールバック参照

- `p4rt_vars.j2` L4: `"x509" : {% if DEVICE_METADATA %}{% if "x509" in DEVICE_METADATA.keys() %}{{ DEVICE_METADATA["x509"] }}{% else %}""{% endif %}{% else %}""{% endif %}`
- `P4RT["certs"]` が存在しない場合のみ `DEVICE_METADATA["x509"]` を読み取る（`p4rt.sh` L38-54 の `elif [ -n "${X509}" ]` ブランチ）。
- 参照は**条件付き・読み取りのみ**。`P4RT|certs` が存在すれば `DEVICE_METADATA|localhost|x509` は完全に無視される。
- evidence: `p4rt_vars.j2:L4`, `p4rt.sh:L38-56`

### 2. ファイルシステム参照（証明書・ソケットパス）

- `server_crt` / `server_key` / `ca_crt` / `cert_crl_dir` / `authz_policy` / `save_forwarding_config_file` / `p4rt_unix_socket` の各フィールドはファイルシステムパスを値として持つ。
- `p4rt.sh` は起動時にこれらのパスの**存在チェックを行わない**（パスを直接バイナリ引数として渡す）。
- 例外: `p4rt_unix_socket` のディレクトリのみ `mkdir -p` で自動作成する（`p4rt.sh` L92-94）。
- evidence: `p4rt.sh:L21-97`

### 3. YANG leafref なし

- P4RT テーブルには専用 YANG モデルが存在しない（`sonic-buildimage/src/sonic-yang-models/yang-models/` に P4RT 用 yang なし）。
- したがって YANG leafref による他テーブルへの明示参照は存在しない。

### 4. orch レベルでの他テーブル参照なし

- `p4rt` コンテナは orchagent (`sonic-swss`) の一部ではなく独立コンテナ。
- `p4rt.sh` → `p4rt` バイナリは起動時に CONFIG_DB を 1 回読み取るのみ。APP_DB / STATE_DB の生成・購読はしない。
- `sonic-swss` 側の `p4orch/` コンポーネントは P4RT テーブルを CONFIG_DB から直接参照しない（APPL_DB の `P4RT_*` テーブルを参照する別経路）。
