# CHASSIS_APP_DB — Phase E: コード定数・魔法数値

調査日: 2026-05-17
調査対象:
- `sonic-swss-common/common/schema.h` @ 158de8d3463ff4b841653f6d57190bb142b80d9c
- `sonic-swss-common/common/database_config.json` @ 158de8d3463ff4b841653f6d57190bb142b80d9c
- `sonic-swss/orchagent/lagid.h` @ 4305596
- `sonic-swss/orchagent/lagids.lua` @ 4305596
- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd` @ 4ba9612
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_device_global.py` @ 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd

---

## 1. DB ID / Redis インスタンス定数 (schema.h / database_config.json)

| 定数名 | 値 | 定義箇所 |
|-------|----|--------|
| `CHASSIS_APP_DB` | `12` | `schema.h:25` |
| `CHASSIS_STATE_DB` | `13` | `schema.h:26` |
| redis_chassis ホスト | `redis_chassis.server` | `database_config.json` |
| redis_chassis ポート | `6380` | `database_config.json` |
| redis_chassis Unix ソケット | `/var/run/redis/redis_chassis.sock` | `database_config.json` |
| CHASSIS_APP_DB separator | `|` | `database_config.json` |

## 2. テーブル名文字列定数 (schema.h)

| #define | 値 | 行 |
|---------|----|----|
| `CHASSIS_APP_SYSTEM_INTERFACE_TABLE_NAME` | `"SYSTEM_INTERFACE"` | `schema.h:411` |
| `CHASSIS_APP_SYSTEM_NEIGH_TABLE_NAME` | `"SYSTEM_NEIGH"` | `schema.h:412` |
| `CHASSIS_APP_LAG_TABLE_NAME` | `"SYSTEM_LAG_TABLE"` | `schema.h:413` |
| `CHASSIS_APP_LAG_MEMBER_TABLE_NAME` | `"SYSTEM_LAG_MEMBER_TABLE"` | `schema.h:414` |

## 3. LAG ID アロケータエラーコード (lagid.h)

| #define | 値 | 意味 |
|---------|----|------|
| `LAG_ID_ALLOCATOR_ERROR_DELETE_ENTRY_NOT_FOUND` | `0` | 削除対象エントリが存在しない（エラーではなくノーオプとして処理） |
| `LAG_ID_ALLOCATOR_ERROR_TABLE_FULL` | `-1` | フリーリストが空でこれ以上 LAG ID を払い出せない |
| `LAG_ID_ALLOCATOR_ERROR_GET_ENTRY_NOT_FOUND` | `-2` | 取得対象の LAG エントリが SYSTEM_LAG_ID_TABLE にない |
| `LAG_ID_ALLOCATOR_ERROR_INVALID_OP` | `-3` | 無効な操作（ Lua スクリプトへの op コードが不正） |
| `LAG_ID_ALLOCATOR_ERROR_DB_ERROR` | `-4` | Redis Lua スクリプト実行でエラー応答が返った |

注意: `LAG_ID_ALLOCATOR_ERROR_DELETE_ENTRY_NOT_FOUND = 0` は「正常 (no-op)」を示す慣習的な 0 値であり、本来エラーではない。`lagIdDel()` が 0 を返しても削除失敗ではない。

## 4. LAG ID 範囲 Redis キー (lagids.lua)

`SYSTEM_LAG_ID_START` / `SYSTEM_LAG_ID_END` はプラットフォーム固有の初期化スクリプトが `CHASSIS_APP_DB` に string として書き込む。
lagids.lua はこれらを `tonumber()` で取得し、有効範囲 [start, end] 内かチェックする。
- テスト環境での実例: start=1, end=2 (`test_virtual_chassis.py:28-29`)
- 本番値はプラットフォーム定義に依存（ハードコードなし）

## 5. chassisd 動作定数 (chassisd)

| 定数名 | 値 | 意味 |
|-------|----|------|
| `CHASSIS_DB_CLEANUP_MODULE_DOWN_PERIOD` | `30` (分) | ラインカード down 検知後、CHASSIS_APP_DB エントリをクリーンアップするまでの待機時間 |
| `CHASSIS_INFO_UPDATE_PERIOD_SECS` | `10` (秒) | chassisd のメインループ周期 |
| `SELECT_TIMEOUT` | `1000` (ms) | swsscommon `sel.select()` のタイムアウト |
| `DEFAULT_LINECARD_REBOOT_TIMEOUT` | `180` (秒) | ラインカードリブート最大待機時間 |
| `DEFAULT_DPU_REBOOT_TIMEOUT` | `360` (秒) | DPU リブート最大待機時間 |
| `CHASSIS_LOAD_ERROR` | `1` | chassis プラグインロード失敗時の exit code |
| `CHASSIS_NOT_SUPPORTED` | `2` | chassis API 未サポート時の exit code |

## 6. BGP_DEVICE_GLOBAL フィールドのデフォルト文字列 (managers_device_global.py)

| クラス定数 | 値 | フィールド名 |
|-----------|----|-----------| 
| `TSA_DEFAULTS` | `"false"` | `tsa_enabled` |
| `WCMP_DEFAULTS` | `"false"` | `wcmp_enabled` |
| `IDF_DEFAULTS` | `"unisolated"` | `idf_isolation_state` |

これらはフィールドが存在しない場合に `DeviceGlobalCfgMgr.__init__()` から `directory.put()` で書き込まれる (lines 42-49)。
