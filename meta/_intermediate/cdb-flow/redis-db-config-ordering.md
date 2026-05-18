# redis-db-config — Phase B: 初期化順序依存調査

## 対象ファイル

- `sonic-net/sonic-swss-common/common/dbconnector.cpp` (SonicDBConfig::initialize / initializeGlobalConfig / getDbInfo)
- `sonic-net/sonic-swss-common/common/dbconnector.h` (DEFAULT_SONIC_DB_CONFIG_FILE 定数)
- `sonic-net/sonic-buildimage/dockers/docker-database/docker-database-init.sh` (生成スクリプト)

---

## 1. `database_config.json` 生成フロー

`docker-database-init.sh` が docker-database コンテナ起動時に実行され、以下の優先順位で `database_config.json` を生成する:

1. `/etc/sonic/database_config.json` が存在 → そのままコピー
2. `/etc/sonic/enable_multidb` が存在 → `multi_database_config.json.j2` でレンダリング
3. それ以外 → `database_config.json.j2` でレンダリング

出力先: `/var/run/redis/sonic-db/database_config.json`

---

## 2. SonicDBConfig 初期化シーケンス

### `initialize()` (dbconnector.cpp L182-204)

- `m_init` フラグで二重初期化を防ぐ。二重初期化は `runtime_error` をスロー。
- ファイルを `parseDatabaseConfig()` で解析し、`m_inst_info` / `m_db_info` / `m_db_separator` に格納。
- `m_init = true` をセット。

### 自動遅延初期化 (dbconnector.cpp L253)

- `getDbInfo()` / `getDbId()` / `getDbSock()` / `getSeparator()` 等が `m_init == false` のとき、`initialize(DEFAULT_SONIC_DB_CONFIG_FILE)` を自動実行。
- アプリ側で明示的初期化が不要な通常ケースはこれで対応。

### `initializeGlobalConfig()` (dbconnector.cpp L89-180)

- マルチ ASIC / SmartSwitch 環境で `database_global.json` を読み込む。
- `m_global_init` フラグをセット。
- namespace 指定 API 使用前に必須。未実行で namespace 指定 API を呼ぶと `SWSS_LOG_THROW` で即クラッシュ。

---

## 3. 検出された順序依存

| # | 依存関係 | 強度 |
|---|----------|------|
| 1 | `database_config.json` 生成 → Redis 起動 | 強制先行 |
| 2 | `initialize()` の一度限り実行 → 全 DB API | 強制先行 |
| 3 | `initializeGlobalConfig()` → namespace API | 強制先行 |
| 4 | 自動遅延初期化 | 自動緩和 (通常ケース) |
| 5 | VoQ Chassis 設定処理 → supervisord 生成 | 強制先行 |

---

## 4. 特記事項

- `database_config.json` は起動後に変更しても Redis や SonicDBConfig には反映されない（再起動が必要）。
- `reset()` API があるが、ユニットテスト専用。本番での使用は設計外。
- VoQ Chassis 環境では `chassisdb.conf` の `start_chassis_db` フラグにより `redis_chassis` インスタンスの有無が決まる（`docker-database-init.sh` L67-80）。

---

## 出典

- `sonic-net/sonic-swss-common/common/dbconnector.cpp` L89-204, L220-260
- `sonic-net/sonic-swss-common/common/dbconnector.h` L87-95 (定数定義)
- `sonic-net/sonic-buildimage/dockers/docker-database/docker-database-init.sh` (全体)
