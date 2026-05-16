# CABLE_LENGTH — 副次 DB 書込み (Phase F)

ソース: `sonic-swss/cfgmgr/buffermgr.cpp`, `buffermgrdyn.cpp`

## static モード (buffermgr)

CABLE_LENGTH 更新 → `doCableTask()` → `doSpeedUpdateTask()`

| 書込み先 | テーブル | 操作 | 条件 | evidence |
|---------|---------|------|------|----------|
| CONFIG_DB | `BUFFER_PROFILE` | `set(pg_lossless_<speed>_<cable>_profile, ...)` | プロファイル未存在時のみ作成 | buffermgr.cpp:274 |
| CONFIG_DB | `BUFFER_PG` | `set(<port>|<pg>, {profile: ...})` | lossless PG が未設定の場合 | buffermgr.cpp:305 |
| CONFIG_DB | `BUFFER_PG` | `del(<port>|<pg>)` | admin-down (Mellanox/Barefoot) かつ default profile 一致時 | buffermgr.cpp:224 |

- static モードでは CONFIG_DB に直接書き込む（APPL_DB への pass-through は `doBufferTableTask` 経由で別途実施）。
- `"0m"` → `doSpeedUpdateTask` が early return、書込みなし (buffermgr.cpp:159-163)。
- `"None"` → `doCableTask` がスキップ、書込みなし (buffermgr.cpp:104)。

## dynamic モード (buffermgrdyn)

CABLE_LENGTH 更新 → `handleCableLenTable()` → `refreshPgsForPort()` → `allocateProfile()` / `updateBufferObjectToDb()` / `updateBufferProfileToDb()`

| 書込み先 | テーブル | 操作 | 条件 | evidence |
|---------|---------|------|------|----------|
| APPL_DB | `BUFFER_PROFILE_TABLE` | `set(pg_lossless_<speed>_<cable>_<mtu>_profile, xon/xoff/size/pool/threshold)` | プロファイル未存在時。`allocateProfile()` 内 `updateBufferProfileToDb()` | buffermgrdyn.cpp:919, 999 |
| STATE_DB | `BUFFER_PROFILE_TABLE` | `set(同名プロファイル, 同フィールド)` | APPL_DB 書込みと同時 | buffermgrdyn.cpp:920 |
| APPL_DB | `BUFFER_PG_TABLE` | `set(<port>|<pg>, {profile: <name>})` | `updateBufferObjectToDb(key, newProfile, true)` | buffermgrdyn.cpp:943, 1568 |
| APPL_DB | `BUFFER_PG_TABLE` | `del(<port>|<pg>)` | `cable_length == "0m"` かつ lossless PG 存在時 | buffermgrdyn.cpp:1505 |
| APPL_DB | `BUFFER_PROFILE_TABLE` | `del(old_profile)` | 旧プロファイルの参照ポート数がゼロになった時 (`releaseProfile`) | buffermgrdyn.cpp:1047 |
| STATE_DB | `BUFFER_PROFILE_TABLE` | `del(old_profile)` | 同上 | buffermgrdyn.cpp:1049 |
| STATE_DB | `BUFFER_POOL_TABLE` | `set(ingress_lossless_pool, size/xoff)` | headroom 更新後 `checkSharedBufferPoolSize()` が SHP サイズを再計算した場合 | buffermgrdyn.cpp:887 |

### admin-down ポートの例外
- `PORT_ADMIN_DOWN` 状態では `refreshPgsForPort()` 冒頭で early return → APPL_DB / STATE_DB への書込みなし (buffermgrdyn.cpp:1454-1458, 2191-2194)。

### mtu 未設定時の暫定書込み
- mtu 空の場合 `DEFAULT_MTU_STR="9100"` で計算して APPL_DB に書き込む。mtu が後で設定されると再計算・上書き (buffermgrdyn.cpp:2174)。

### STATE_DB への二重書込み
- `updateBufferProfileToDb()` は APPL_DB (`m_applBufferProfileTable`) と STATE_DB (`m_stateBufferProfileTable`) に同一内容を同時書込みする (buffermgrdyn.cpp:919-920)。
- `updateBufferPoolToDb()` は APPL_DB (`m_applBufferPoolTable`) と STATE_DB (`m_stateBufferPoolTable`) に同時書込み (buffermgrdyn.cpp:885-887)。
