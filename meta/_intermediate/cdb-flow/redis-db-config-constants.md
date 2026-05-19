# redis-db-config — Phase E ハードコード定数 調査メモ

## 対象ソース
- `sonic-net/sonic-swss-common` `common/schema.h` ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
- `sonic-net/sonic-swss-common` `common/dbconnector.h` ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
- `sonic-net/sonic-swss-common` `common/dbconnector.cpp` ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
- `sonic-net/sonic-buildimage` `dockers/docker-database/docker-database-init.sh` ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd

## JSON 構造キー定数

`parseDatabaseConfig()` で参照するすべての JSON キー名はハードコードされている。
- `"INSTANCES"` — dbconnector.cpp:45
- `"DATABASES"` — dbconnector.cpp:59
- `"hostname"` — dbconnector.cpp:54
- `"port"` — dbconnector.cpp:55
- `"unix_socket_path"` — dbconnector.cpp:49 (find() による省略可能フィールド)
- `"instance"` — dbconnector.cpp:62
- `"id"` — dbconnector.cpp:63
- `"separator"` — dbconnector.cpp:64

## DB ID マクロ定数 (schema.h:12-33)

schema.h で定義される DB ID マクロ (0-20):
- APPL_DB=0, ASIC_DB=1, COUNTERS_DB=2, LOGLEVEL_DB=3, CONFIG_DB=4
- PFC_WD_DB=5, FLEX_COUNTER_DB=5 (同一 Redis DB)
- STATE_DB=6, SNMP_OVERLAY_DB=7, RESTAPI_DB=8
- GB_ASIC_DB=9, GB_COUNTERS_DB=10, GB_FLEX_COUNTER_DB=11
- CHASSIS_APP_DB=12, CHASSIS_STATE_DB=13, APPL_STATE_DB=14
- DPU_APPL_DB=15, DPU_APPL_STATE_DB=16, DPU_STATE_DB=17, DPU_COUNTERS_DB=18
- EVENT_DB=19, BMP_STATE_DB=20

## パス・ポート定数

- DEFAULT_SONIC_DB_CONFIG_FILE = `/var/run/redis/sonic-db/database_config.json` (dbconnector.h:90)
- DEFAULT_SONIC_DB_GLOBAL_CONFIG_FILE = `/var/run/redis/sonic-db/database_global.json` (dbconnector.h:91)
- DEFAULT_UNIXSOCKET = `/var/run/redis/redis.sock` (dbconnector.h:169,206)
- redis_port デフォルト = 6379 (docker-database-init.sh:20)
- DPU インスタンスポート = 6381 + DPU_ID (docker-database-init.sh:28)
- REMOTE_DB_PORT (DPU) = 6380 + d (docker-database-init.sh:40)
- BMP_DB_PORT = 6400 (docker-database-init.sh:49)
- REDIS_DIR = /var/run/redis${NAMESPACE_ID} (docker-database-init.sh:51)
- KEY_DEL_CHUNK_SIZE = 128 (dbconnector.cpp:23, Redis キー一括削除バッファサイズ)
