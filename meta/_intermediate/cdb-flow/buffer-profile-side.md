# BUFFER_PROFILE 副次 DB 書込 分析 (Phase F)

ソース:
- `sonic-swss/cfgmgr/buffermgrdyn.cpp` (master HEAD)
- `sonic-swss/cfgmgr/buffermgr.cpp`
- `sonic-swss/orchagent/bufferorch.cpp`

`BUFFER_PROFILE` エントリの SET/DEL が **CONFIG_DB → APPL_DB** の主経路以外に引き起こす副次書込（STATE_DB / APPL_STATE_DB への書込）を全件列挙する。COUNTERS_DB / FLEX_COUNTER_DB への書込は BUFFER_POOL 操作に紐づくものであり、BUFFER_PROFILE 単体では発生しない。

---

## 1. APPL_DB `BUFFER_PROFILE_TABLE` (主書込 — 参考)

主経路として `buffermgrdyn.cpp` の `updateBufferProfileToDb()` が `m_applBufferProfileTable.set(name, fvVector)` を呼び出す。これは副次書込ではなく主目的の書込である。

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 / トリガ | evidence |
|------|------------------|-----------------|--------------|----------|
| `m_applBufferProfileTable.set(name, fvVector)` | APPL_DB / `BUFFER_PROFILE_TABLE` | key=`<profile_name>`, fields: pool / size / xon / xoff / xon_offset / threshold / packet_discard_action | `updateBufferProfileToDb()` — `m_bufferPoolReady==true` のとき即時、false のとき pending | `buffermgrdyn.cpp:919` |
| `m_applBufferProfileTable.del(profile_name)` | APPL_DB / `BUFFER_PROFILE_TABLE` | key=`<profile_name>` | `releaseProfile()` — reference count が 0 になり削除するとき | `buffermgrdyn.cpp:1047` |

---

## 2. STATE_DB `BUFFER_PROFILE_TABLE` 書込 (副次書込 A)

`buffermgrdyn` は APPL_DB への書込と **同時に** STATE_DB の同テーブル (`STATE_BUFFER_PROFILE_TABLE_NAME = "BUFFER_PROFILE_TABLE"`) にも書込む。これが主要な副次書込である。

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 / トリガ | evidence |
|------|------------------|-----------------|--------------|----------|
| `m_stateBufferProfileTable.set(name, fvVector)` | STATE_DB / `BUFFER_PROFILE_TABLE` | key=`<profile_name>`, fields: APPL_DB と同一 fvVector | `updateBufferProfileToDb()` 末尾 — APPL_DB 書込と同時 | `buffermgrdyn.cpp:920` |
| `m_stateBufferProfileTable.set(key, fvs)` | STATE_DB / `BUFFER_PROFILE_TABLE` | key=`<zero_profile_name>` | ゼロプロファイル (warm reboot 初期化) ロード時 | `buffermgrdyn.cpp:361` |
| `m_stateBufferProfileTable.del(profile_name)` | STATE_DB / `BUFFER_PROFILE_TABLE` | key=`<profile_name>` | `releaseProfile()` — APPL_DB 削除と同時 | `buffermgrdyn.cpp:1049` |
| `m_stateBufferProfileTable.del(zeroProfileName)` | STATE_DB / `BUFFER_PROFILE_TABLE` | key=`<zero_profile_name>` | zero profile アンロード時（全ポート admin-up 後） | `buffermgrdyn.cpp:421` |

> **フィールド内容**: APPL_DB / STATE_DB ともに同一 `fvVector` を書き込む。lossless プロファイルのみ `xon` / `xoff` / `xon_offset` を含む（lossy プロファイルでは omit）。

---

## 3. APPL_STATE_DB `BUFFER_PROFILE_TABLE` 書込 (副次書込 B — ResponsePublisher)

`BufferOrch` は `Orch` 基底クラスの `m_publisher` (`ResponsePublisher{"APPL_STATE_DB"}`) を経由して **lossless プロファイル** の SAI 反映完了通知を APPL_STATE_DB に書込む。

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 / トリガ | evidence |
|------|------------------|-----------------|--------------|----------|
| `m_publisher.publish(APP_BUFFER_PROFILE_TABLE_NAME, name, fvs, SAI_STATUS_SUCCESS, force=true)` | APPL_STATE_DB / `BUFFER_PROFILE_TABLE` | key=`<profile_name>`, fields: kfvFieldsValues(tuple) のコピー | `processBufferProfile()` SET 成功 かつ `is_lossless==true`（`xoff` フィールドが存在する場合）のみ | `bufferorch.cpp:824-833` |
| `m_publisher.publish(APP_BUFFER_PROFILE_TABLE_NAME, name, [], SAI_STATUS_SUCCESS, force=true)` | APPL_STATE_DB / `BUFFER_PROFILE_TABLE` | key=`<profile_name>`, fvs 空 | `processBufferProfile()` DEL 成功 かつ `is_lossless==true` | `bufferorch.cpp:875-880` |

> **lossy プロファイル（`xoff` フィールドなし）は APPL_STATE_DB に publish されない。** `is_lossless` フラグは SET 時に `xoff` フィールドの有無で判定し、DEL 時は `m_bufHlpr.getBufferConfig()` で既存エントリを参照して判定する。

---

## 4. COUNTERS_DB / FLEX_COUNTER_DB — BUFFER_PROFILE は対象外

| DB | 状況 |
|----|------|
| COUNTERS_DB `COUNTERS_BUFFER_POOL_NAME_MAP` | BUFFER_POOL 作成/削除時のみ更新（`processBufferPool()`）。BUFFER_PROFILE には対応する name map なし |
| FLEX_COUNTER_DB `FLEX_COUNTER_TABLE` | BUFFER_POOL watermark カウンタの SAI OID 登録用。BUFFER_PROFILE 操作では FLEX_COUNTER_DB への書込なし |
| COUNTERS_DB / FLEX_COUNTER_DB (PG/Queue) | BUFFER_PG / BUFFER_QUEUE への profile attach 完了後に `gPortsOrch` が間接的に更新するが、BUFFER_PROFILE エントリ自体の SET/DEL 起点ではない |

---

## 5. 副次書込の発火順序（典型: BUFFER_PROFILE 新規 SET）

```
1. buffermgrd(yn) が CONFIG_DB BUFFER_PROFILE|<name> SET を受信
2. updateBufferProfileToDb() 呼出
   2a. APPL_DB BUFFER_PROFILE_TABLE|<name> SET   ← 主書込
   2b. STATE_DB BUFFER_PROFILE_TABLE|<name> SET  ← 副次書込 A (同時)
3. orchagent BufferOrch processBufferProfile() が APPL_DB イベントを受信
4. SAI create_buffer_profile() → ASIC_DB
5. (is_lossless==true のとき)
   APPL_STATE_DB BUFFER_PROFILE_TABLE|<name> publish ← 副次書込 B
```

---

## 6. 検証コマンド (実機 dump)

```sh
# APPL_DB
sonic-db-cli APPL_DB hgetall 'BUFFER_PROFILE_TABLE|pg_lossless_100000_5m_profile'

# STATE_DB (副次書込 A)
sonic-db-cli STATE_DB hgetall 'BUFFER_PROFILE_TABLE|pg_lossless_100000_5m_profile'

# APPL_STATE_DB (副次書込 B — lossless のみ存在)
sonic-db-cli APPL_STATE_DB hgetall 'BUFFER_PROFILE_TABLE|pg_lossless_100000_5m_profile'
```

---

## 7. 証跡カバレッジ

- `buffermgrdyn.cpp` L920: `m_stateBufferProfileTable.set(name, fvVector)` — APPL_DB と同時に STATE_DB 書込
- `buffermgrdyn.cpp` L919: `m_applBufferProfileTable.set(name, fvVector)` — 主書込
- `buffermgrdyn.cpp` L361: zero profile 初期化時の STATE_DB 書込
- `buffermgrdyn.cpp` L421: zero profile 削除時の STATE_DB DEL
- `buffermgrdyn.cpp` L1047, L1049: releaseProfile() での APPL_DB / STATE_DB DEL
- `bufferorch.cpp` L832: lossless SET 成功後の APPL_STATE_DB publish
- `bufferorch.cpp` L880: lossless DEL 成功後の APPL_STATE_DB publish (fvs 空)
- `orchagent/orch.h` L382: `ResponsePublisher m_publisher{"APPL_STATE_DB"}` — publish 先の確認
