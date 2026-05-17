# CABLE_LENGTH — Phase 6/7 Derivation Grep Evidence

ソース: `sonic-swss/cfgmgr/buffermgr.cpp`, `sonic-swss/cfgmgr/buffermgrdyn.cpp`

---

## Phase 6: 値による他フィールド自動派生

CABLE_LENGTH の `length` 値変化が引き金となって、他テーブル・他フィールドへ自動派生する経路を列挙する。

### static モード (buffermgr)

`doCableTask()` (buffermgr.cpp:101) が呼ばれ、`doSpeedUpdateTask()` (buffermgr.cpp:142) へ連鎖。

| 条件 | 派生先テーブル・フィールド | evidence |
|---|---|---|
| `length != "None"` かつ 変化あり | `BUFFER_PROFILE` に `pg_lossless_<speed>_<cable>_profile` エントリを新規 set | buffermgr.cpp:274 |
| lossless PG が未設定ポート | `BUFFER_PG.<port>\|<pg>.profile` を `pg_lossless_*` プロファイル名に set | buffermgr.cpp:305 |
| `length == "0m"` | `doSpeedUpdateTask` が early return → BUFFER_PROFILE / BUFFER_PG への書込みなし | buffermgr.cpp:159-163 |
| `length == "None"` | `doCableTask` がスキップ → 派生なし | buffermgr.cpp:104 |

### dynamic モード (buffermgrdyn)

`handleCableLenTable()` (buffermgrdyn.cpp:2124) → `refreshPgsForPort()` (buffermgrdyn.cpp:1445) → `allocateProfile()` へ連鎖。

| 条件 | 派生先テーブル・フィールド | evidence |
|---|---|---|
| speed・mtu が揃っており `PORT_READY` / `PORT_INITIALIZING` | APPL_DB `BUFFER_PROFILE_TABLE` に `pg_lossless_<speed>_<cable>_<mtu>_profile` を set | buffermgrdyn.cpp:919 |
| 上記と同条件 | STATE_DB `BUFFER_PROFILE_TABLE` に同名プロファイルを set (二重書込み) | buffermgrdyn.cpp:920 |
| 上記と同条件 | APPL_DB `BUFFER_PG_TABLE.<port>\|<pg>.profile` を新プロファイル名に set | buffermgrdyn.cpp:1568 |
| `length == "0m"` かつ lossless PG が存在 | APPL_DB `BUFFER_PG_TABLE.<port>\|<pg>` を del | buffermgrdyn.cpp:1505 |
| 旧プロファイルの参照ポート数がゼロになった場合 | APPL_DB / STATE_DB `BUFFER_PROFILE_TABLE` から旧プロファイルを del (`releaseProfile`) | buffermgrdyn.cpp:1047-1049 |
| headroom 更新後 SHP サイズ変化 | STATE_DB `BUFFER_POOL_TABLE.ingress_lossless_pool.size` / `xoff` を set | buffermgrdyn.cpp:887 |
| `PORT_INITIALIZING` → 初回 cable_length 設定 | ポート状態を `PORT_READY` に遷移 | buffermgrdyn.cpp:2184 |

---

## Phase 7: 条件付き module/manager 登録

CABLE_LENGTH テーブルを購読するマネージャの条件付き登録状況。

| 条件 | 登録 module | evidence |
|---|---|---|
| `DEVICE_METADATA.buffer_model == "dynamic"` | `BufferMgrDynamic` が CABLE_LENGTH を `m_bufferTableHandlerMap` に登録 | buffermgrdyn.cpp:450 |
| `buffer_model != "dynamic"` (static モード) | `BufferMgr` が CABLE_LENGTH を `m_cfgCableLenTable` で購読 | buffermgr.cpp:24 |

どちらか一方のみが起動し、両者が同時に CABLE_LENGTH を購読することはない。`buffer_model` フィールドは `DEVICE_METADATA|localhost` テーブルで決定される。

---

## grep カバレッジサマリ

- buffermgr.cpp: `doCableTask` (L101-111) + `doSpeedUpdateTask` (L142-330) スキャン済み
- buffermgrdyn.cpp: `handleCableLenTable` (L2124-2290) + `refreshPgsForPort` (L1445-1600) + `allocateProfile` スキャン済み
- 派生先: BUFFER_PROFILE (CONFIG_DB/APPL_DB), BUFFER_PG (CONFIG_DB/APPL_DB), BUFFER_POOL (STATE_DB) の計 6 経路
- 条件付き manager 登録: 2 件 (buffermgr vs buffermgrdyn、buffer_model で排他選択)
