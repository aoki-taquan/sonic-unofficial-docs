# redis-db-config — Phase H platform 調査メモ

## 調査対象ソース

- `sonic-net/sonic-buildimage` `dockers/docker-database/docker-database-init.sh`
- `sonic-net/sonic-buildimage` `dockers/docker-database/database_config.json.j2`
- `sonic-net/sonic-buildimage` `dockers/docker-database/multi_database_config.json.j2`
- `sonic-net/sonic-swss-common` `common/dbconnector.cpp`

## 主要な platform 分岐

### `DATABASE_TYPE` 環境変数による分岐 (docker-database-init.sh)

`docker-database-init.sh` の冒頭で `DATABASE_TYPE` に応じた初期化経路が分岐する。

| `DATABASE_TYPE` | 起動文脈 | 生成テンプレート | 特殊処理 |
|-----------------|---------|---------------|---------|
| `""` (空・未設定) | 通常ノード / multi-ASIC (host namespace) | `database_config.json.j2` | デフォルト構成 |
| `dpudb` | SmartSwitch の NPU 側から見た DPU 用 DB コンテナ | `database_config.json.j2` (DPU 向けエントリ付き) | `host_ip=169.254.200.254`、`redis_port=6381+DPU_ID` |
| `bmcdb` | BMC 搭載ノード | `database_config.json.j2` | BMP DB エントリ除外 |
| `chassisdb` | VoQ Chassis Supervisor 専用 DB コンテナ | supervisord config のみ生成し `exit 0` | `update_chassisdb_config -k` で chassis 専用設定を保持 |

証跡: `docker-database-init.sh:22-46` (`DATABASE_TYPE` 分岐)、`docker-database-init.sh:84-100` (`chassisdb` 分岐)

### `NAMESPACE_ID` による multi-ASIC 対応 (docker-database-init.sh)

`NAMESPACE_ID` が空の場合は host namespace。非空の場合は `asic0` / `asic1` 等の ASIC namespace 専用コンテナとして動作する。

| `NAMESPACE_ID` | インターフェース | REDIS_DIR |
|----------------|---------------|----------|
| `""` (空) | `lo` (loopback) | `/var/run/redis/sonic-db/` |
| `asic0` 等 | `eth0` (docker0 ブリッジ経由) | `/var/run/redisasic0/sonic-db/` |

`database_global.json` の生成は `NAMESPACE_ID == "" && DATABASE_TYPE == "" && (NAMESPACE_COUNT > 1 || NUM_DPU > 1)` の条件を満たす場合のみ行われる（host namespace かつ multi-ASIC / SmartSwitch 構成時のみ）。

証跡: `docker-database-init.sh:5-9` (INTFC 分岐)、`docker-database-init.sh:51` (REDIS_DIR)、`docker-database-init.sh:104-110` (database_global.json 生成)

### VoQ Chassis 用 `chassisdb.conf` によるエントリ制御

プラットフォームが VoQ Chassis の場合、`/usr/share/sonic/platform/chassisdb.conf` が存在し `start_chassis_db` / `chassis_db_address` / `chassis_db_port` を定義する。

- `start_chassis_db=1`: `CHASSIS_APP_DB` / `CHASSIS_STATE_DB` エントリを最終 `database_config.json` に含める
- `start_chassis_db=0` (デフォルト / 非VoQ): chassis エントリを `update_chassisdb_config -d` で削除

また VoQ ラインカードでは Redis の protected mode が **無効化** される（ラインカード外部の midplane ネットワークから supervisor の `redis_chassis` への接続を許可するため）。

証跡: `docker-database-init.sh:74-78` (chassisdb.conf 読み込み)、`docker-database-init.sh:117-120` (linecard protected mode 無効化)

### `IS_DPU_DEVICE` / `IS_BMC_DEVICE` 環境変数

SmartSwitch の DPU ノード自体 (`IS_DPU_DEVICE=true`) では midplane IP (`eth0-midplane`) を取得して `DATABASE_TYPE=dpudb`・`REMOTE_DB_IP`・`REMOTE_DB_PORT` を自動設定する。BMC 搭載ノード (`IS_BMC_DEVICE=true`) では `DATABASE_TYPE=bmcdb` が設定される。

証跡: `docker-database-init.sh:31-46`

## SonicDBConfig はプラットフォーム非依存

`SonicDBConfig` クラス (`dbconnector.cpp`) 自体はプラットフォーム識別文字列 (`broadcom` / `mellanox` 等) を一切参照しない。プラットフォーム差はすべて `docker-database-init.sh` が生成する `database_config.json` の**内容**の差として現れ、`SonicDBConfig` はそのファイルを単純に読み込む。

証跡: `dbconnector.cpp` 全体 (`broadcom` / `mellanox` / `platform` 等でヒットなし)
