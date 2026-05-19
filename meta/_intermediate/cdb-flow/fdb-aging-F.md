# FDB Aging Time (SWITCH_TABLE.fdb_aging_time) — Phase F: 副次 DB 書込スキャン中間ファイル

生成日: 2026-05-19 (Task F Phase F / cdb_q67_f batch880)

## 調査対象

`APPL_DB SWITCH_TABLE:switch` の `fdb_aging_time` フィールドを処理する `SwitchOrch::doAppSwitchTableTask()` および `SwitchOrch::setAgingFDB()` が、副次的に APPL_DB / STATE_DB / COUNTERS_DB / ASIC_DB その他の DB テーブルへ書き込むか。

## 走査範囲

- `.cache/sonic-sources/sonic-swss/orchagent/switchorch.cpp` (主処理: L595-748, L1671-1688)
- `.cache/sonic-sources/sonic-swss/orchagent/switchorch.h`
- `.cache/sonic-sources/sonic-swss/orchagent/orchdaemon.cpp` (warm-reboot 呼び出し側: L1060-1075)
- SwitchOrch が保持する全 DB 接続 (`m_stateDb`, `m_db`, `m_switchTable`)

## 走査コマンドと結果

### 1. switchorch.cpp の STATE_DB 書込検索

```bash
grep -n "m_stateDb\|m_switchTable\|m_asicSensorsTable\|m_asicSdkHealthEventTable\|set(\|hset\|fdb_aging" \
  .cache/sonic-sources/sonic-swss/orchagent/switchorch.cpp
```

関連ヒット:

- L152: `m_stateDb(new DBConnector("STATE_DB", 0))` — STATE_DB 接続 (SwitchOrch コンストラクタ)
- L153: `m_asicSensorsTable(new Table(m_stateDb.get(), ASIC_TEMPERATURE_INFO_TABLE_NAME))` — 温度センサーテーブル用
- L155-156: `m_stateDbForNotification`、`m_asicSdkHealthEventTable` — ASIC SDK health イベント用
- L1864-1871: `set_switch_capability()` → `m_switchTable.set("switch", values)` — STATE_DB `SWITCH_CAPABILITY_TABLE` への書込
- L664-666: `case SAI_SWITCH_ATTR_FDB_AGING_TIME: attr.value.u32 = to_uint<uint32_t>(value); break;` — **STATE_DB 書込なし。SAI 属性に変換するのみ**
- L1671-1688: `setAgingFDB()` — SAI 直接呼び出しのみ。DB 書込なし

### 2. doAppSwitchTableTask() の副次書込確認 (L595-748)

```bash
sed -n '595,748p' .cache/sonic-sources/sonic-swss/orchagent/switchorch.cpp \
  | grep -n "m_stateDb\|m_switchTable\|set(\|hset\|APPL_DB\|COUNTERS_DB\|ASIC_DB"
```

結果: **マッチ 0 件**

`doAppSwitchTableTask()` は `kfvFieldsValues` を順次処理し、`switch_attribute_map` / `switch_tunnel_attribute_map` でルックアップ後、SAI `set_switch_attribute()` を呼び出す。この処理パス全体に DB への書込呼び出しは存在しない。

### 3. setAgingFDB() の副次書込確認 (L1671-1688)

```bash
sed -n '1671,1688p' .cache/sonic-sources/sonic-swss/orchagent/switchorch.cpp
```

結果:

```cpp
bool SwitchOrch::setAgingFDB(uint32_t sec)
{
    sai_attribute_t attr;
    attr.id = SAI_SWITCH_ATTR_FDB_AGING_TIME;
    attr.value.u32 = sec;
    auto status = sai_switch_api->set_switch_attribute(gSwitchId, &attr);
    if (status != SAI_STATUS_SUCCESS)
    {
        SWSS_LOG_ERROR("Failed to set switch %" PRIx64 " fdb_aging_time attribute: %d", gSwitchId, status);
        task_process_status handle_status = handleSaiSetStatus(SAI_API_SWITCH, status);
        if (handle_status != task_success)
        {
            return parseHandleSaiStatusFailure(handle_status);
        }
    }
    SWSS_LOG_NOTICE("Set switch %" PRIx64 " fdb_aging_time %u sec", gSwitchId, sec);
    return true;
}
```

**STATE_DB / APPL_DB / COUNTERS_DB への書込なし。SAI 属性セットのみ。**

### 4. SwitchOrch が持つ STATE_DB 書込経路の整理

`SwitchOrch` は以下の STATE_DB 書込経路を持つが、いずれも `fdb_aging_time` 処理とは独立している:

| 経路 | テーブル | トリガー | fdb_aging_time との関係 |
|------|---------|---------|------------------------|
| `set_switch_capability()` → `m_switchTable.set()` | `STATE_DB SWITCH_CAPABILITY_TABLE:switch` | コンストラクタ・能力照会時 | 無関係 (PFC DLR / ASIC SDK health / TPID 等の能力フラグ) |
| `m_asicSensorsTable->set()` | `STATE_DB ASIC_TEMPERATURE_INFO_TABLE` | 温度 polling timer | 無関係 |
| `m_asicSdkHealthEventTable->set()` | `STATE_DB STATE_ASIC_SDK_HEALTH_EVENT_TABLE` | ASIC SDK health イベント通知 | 無関係 |

### 5. sonic-swss 全体でのフォールバック検索

```bash
grep -rn "fdb_aging\|FDB_AGING" .cache/sonic-sources/sonic-swss/ \
  | grep -v ".pyc\|test" \
  | grep -i "state_db\|appl_db\|counters_db\|asic_db"
```

結果: **マッチ 0 件**

`fdb_aging_time` / `FDB_AGING_TIME` と DB 書込を組み合わせたパスは sonic-swss 全体に存在しない。

## 結論

`APPL_DB SWITCH_TABLE:switch` の `fdb_aging_time` フィールドが `SwitchOrch::doAppSwitchTableTask()` に処理される際、および warm-reboot パスの `setAgingFDB()` 呼び出しの際、**副次的な DB 書込は発生しない**。

- **APPL_DB**: 書込なし
- **STATE_DB**: 書込なし (`fdb_aging_time` 処理に限定。`set_switch_capability()` による SWITCH_CAPABILITY_TABLE 書込は SwitchOrch コンストラクタ / 能力照会時にのみ発生し `fdb_aging_time` SET タスクとは独立)
- **COUNTERS_DB**: 書込なし
- **ASIC_DB**: syncd 経由で間接的に `SAI_SWITCH_ATTR_FDB_AGING_TIME` の SAI 操作が記録されるが、orchagent から ASIC_DB への直接書込は行われない
