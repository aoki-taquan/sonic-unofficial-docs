# RESTAPI — Phase F 副次 DB 書込スキャン

生成日: 2026-05-19

## スキャン対象

- `sonic-host-services/scripts/hostcfgd` (FipsCfg クラス、L100-L103, L1756-1845)
- `sonic-buildimage/dockers/docker-sonic-mgmt-framework/rest-server.sh`
- `sonic-buildimage/dockers/docker-sonic-mgmt-framework/supervisord.conf`
- `sonic-utilities/scripts/db_migrator.py` (migrate_restapi, L608-619)

## 主要発見

### 1. FIPS 設定変更時の restapi サービス再起動 (hostcfgd)

`hostcfgd` の `FipsCfg` クラスは `DEFAULT_FIPS_RESTART_SERVICES = ['ssh', 'telemetry.service', 'restapi']`
を保持しており（L103）、FIPS 設定が変更されると `fips_handler()` → `update()` → `update_noneenforce_config()` →
`restart()` 呼び出しにより `systemctl restart restapi` が実行される（L1826-1833）。

これは RESTAPI テーブル自体への書込みではなく、**FIPS テーブル変更** が RESTAPI コンテナを副次的に再起動させる
側面効果。STATE_DB の `FIPS_STATS|state` に `config_datetime` が書き込まれる（L1792）が、これは FIPS 固有の
STATE_DB エントリであり、RESTAPI テーブルの直接副産物ではない。

### 2. 副次 DB 書込みなし

RESTAPI テーブルへの書込み → 副次的な DB 書込みは検出されなかった:

- APPL_DB への ProducerStateTable 書込み: **なし**
- STATE_DB への直接 hset: **なし**（RESTAPI 変更に対応した state 書込み経路なし）
- COUNTERS_DB / FLEX_COUNTER_DB: **なし**（管理プレーン機能のため SAI 経由なし）
- ASIC_DB / LOGLEVEL_DB: **なし**

### 3. ファイルシステム副作用（DB 外）

`rest-server.sh` が証明書未設定時に `/tmp/cert.pem` / `/tmp/key.pem` を自動生成する（rest-server.sh:46-49）。
これは DB 副作用ではなくファイルシステム副作用。

## 結論

RESTAPI は管理プレーン専用テーブルであり、CONFIG_DB 書込みが他の DB テーブルに副次的に書き込む経路は存在しない。
唯一の間接的な副次効果は FIPS 変更時の `systemctl restart restapi` トリガ（DB 外の OS レベルの副作用）。
