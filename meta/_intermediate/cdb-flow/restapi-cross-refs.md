# RESTAPI テーブル — 暗黙参照テーブル (Phase C) 調査メモ

調査日: 2026-05-19
対象ファイル: docs/reference/config-db/restapi.md

## 調査ソース

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-restapi.yang` (YANG leafref 確認)
- `sonic-buildimage/dockers/docker-sonic-mgmt-framework/rest-server.sh` (実装依存)
- `sonic-buildimage/dockers/docker-sonic-mgmt-framework/mgmt_vars.j2` (テンプレート依存)
- `sonic-buildimage/src/sonic-config-engine/minigraph.py` L2689-2702 (書込み経路)
- `sonic-utilities/scripts/db_migrator.py` L608-619 (マイグレーション)
- `sonic-buildimage/src/sonic-config-engine/tests/mock_tables/config_db.json` (FEATURE|restapi 確認)

## YANG leafref 確認

`sonic-restapi.yang` には leafref / must / when 文はゼロ件。
YANG スキーマレベルでの明示的 cross-table 参照は存在しない。

## 実装レベルの暗黙参照

### 1. DEVICE_METADATA|localhost.x509 (cert フォールバック)

`mgmt_vars.j2` L3:
```
"x509" : {% if "x509" in DEVICE_METADATA.keys() %}{{ DEVICE_METADATA["x509"] }}{% else %}""{% endif %}
```
`rest-server.sh` L27-41:
- `RESTAPI|certs` の `server_crt` / `server_key` / `ca_crt` が全て空の場合に `DEVICE_METADATA|localhost.x509` を参照
- `x509` はサブオブジェクト (`server_crt`, `server_key`, `ca_crt`) を含む

### 2. FEATURE|restapi (サービス有効化制御)

`config_db.json` に `FEATURE|restapi` エントリが存在し、restapi コンテナの auto_restart / has_global_scope などを制御。
RESTAPI テーブル自体は `FEATURE|restapi.state` が `enabled` の場合のみ実際にサービスが起動して読まれる。

### 3. 書き込みソース間の暗黙依存

- `minigraph.py` が `RESTAPI` と `FEATURE` を同一処理パスで生成
- `db_migrator.py` が既存エントリ優先で書き込む（RESTAPI|config / RESTAPI|certs が空の場合のみ）

## 範囲外

- APPL_DB への書き込みなし（restapi は管理プレーン機能）
- STATE_DB / COUNTERS_DB 参照なし
- leafref による明示的 cross-table 参照なし
