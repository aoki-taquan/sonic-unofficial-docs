# fdb_aging_time (SWITCH_TABLE) — Phase B 書込み順依存スキャンノート

対象フィールド: `SWITCH_TABLE:switch` の `fdb_aging_time`
Consumer: `orchagent` / `SwitchOrch::doAppSwitchTableTask()` (`sonic-swss/orchagent/switchorch.cpp`)
スキャン範囲: `switch_attribute_map` 定義 (L42-54)、`doAppSwitchTableTask()` (L595-748)、`setAgingFDB()` (L1671-1688)、`orchdaemon.cpp:1060-1079` 精読
スキャン日: 2026-05-16

---

## データフローの概要

`fdb_aging_time` は CONFIG_DB には存在しない。`switch.json.j2` テンプレートが orchagent コンテナ起動時に展開され、`switch.json` として `swssconfig` が APPL_DB `SWITCH_TABLE:switch` へ書き込む経路が唯一の起動時注入パスとなる。

```
docker-orchagent 起動
  └─ docker-init.j2:16 (sonic-cfggen -t switch.json.j2,/etc/swss/config.d/switch.json)
       └─ switch.json 生成 (fdb_aging_time: "600" 固定値)
            └─ swssconfig.sh:96-101: swssconfig /etc/swss/config.d/switch.json
                 └─ APPL_DB SWITCH_TABLE:switch SET {fdb_aging_time: "600"}
                      └─ SwitchOrch::doAppSwitchTableTask()
                           └─ attr.id  = SAI_SWITCH_ATTR_FDB_AGING_TIME
                              attr.value.u32 = 600
                              sai_switch_api->set_switch_attribute(gSwitchId, &attr)
```

---

## SAI fdb_aging_time 設定フロー

### 1. フィールドマッピング定義

`switch_attribute_map` (switchorch.cpp:42-54) で `fdb_aging_time` は `SAI_SWITCH_ATTR_FDB_AGING_TIME` に静的マップされている:

```cpp
// switchorch.cpp:42-54
const map<string, sai_switch_attr_t> switch_attribute_map =
{
    {"fdb_unicast_miss_packet_action",      SAI_SWITCH_ATTR_FDB_UNICAST_MISS_PACKET_ACTION},
    ...
    {"fdb_aging_time",                      SAI_SWITCH_ATTR_FDB_AGING_TIME},
    ...
};
```

### 2. doAppSwitchTableTask() 内の処理フロー

```
APPL_DB SWITCH_TABLE:switch SET {fdb_aging_time: <sec>}
  │
  ├─ [1] switch_non_sai_attribute_set チェック (switchorch.cpp:612)
  │       → fdb_aging_time は非該当、次へ
  │
  ├─ [2] switch_attribute_map チェック (switchorch.cpp:617-622)
  │       → 該当: SAI_SWITCH_ATTR_FDB_AGING_TIME
  │
  ├─ [3] switch 文 (switchorch.cpp:664-666)
  │       case SAI_SWITCH_ATTR_FDB_AGING_TIME:
  │           attr.value.u32 = to_uint<uint32_t>(value);
  │           break;
  │       ※ capacity 確認不要 (ecmp/lag_hash_offset と異なりスキップなし)
  │
  ├─ [4] sai_switch_api->set_switch_attribute(gSwitchId, &attr)
  │       (switchorch.cpp:722)
  │       → SAI_STATUS_SUCCESS: SWSS_LOG_NOTICE で成功ログ
  │       → 失敗: handleSaiSetStatus → task_need_retry → retry=true → it++ (再試行)
  │
  └─ [5] erase or retry
          retry==false → it = consumer.m_toSync.erase(it)（完了）
          retry==true  → it++ （次のイベントループで再試行）
```

### 3. setAgingFDB() — シャットダウン時の別経路

`setAgingFDB()` (switchorch.cpp:1671-1688) は `doAppSwitchTableTask()` とは**別コードパス**。`orchdaemon.cpp:1068` で warm-reboot 時に `gSwitchOrch->setAgingFDB(0)` が呼ばれ、aging を 0（無効化）に設定する:

```cpp
// orchdaemon.cpp:1065-1068
if (!gSwitchOrch->checkRestartNoFreeze())
{
    // Disable FDB aging
    gSwitchOrch->setAgingFDB(0);
```

---

## 検出した順序依存

### 依存 1: SAI create_switch → fdb_aging_time SET（強制先行）

`set_switch_attribute(gSwitchId, &attr)` には有効な `gSwitchId` が必要。orchagent 起動時の `create_switch` で確定するため、orchagent が起動するまで `fdb_aging_time` は適用されない。

- **方向**: `create_switch` 完了 → `fdb_aging_time` SET
- **強度**: hard（gSwitchId なし = SAI 呼び出し不可）
- **緩和策**: orchagent が保証（ユーザー操作不要）
- **evidence**: `switchorch.cpp:22-27`（extern gSwitchId 宣言）

### 依存 2: swssconfig 実行タイミング — orchagent メインループ開始後

`swssconfig.sh:96-101` は `swssconfig switch.json` 後に `sleep 1` を挟みながら複数 json を適用する。`swssconfig` が APPL_DB に書き込む前に `SwitchOrch` がメインループを開始している必要がある。orchagent 起動シーケンス上、`SwitchOrch` コンストラクタ完了 → Consumer 登録 → メインループ開始 → `swssconfig` 書込 の順序が `swssconfig.sh` の `sleep` によって担保されている。

- **方向**: orchagent メインループ開始 → swssconfig switch.json 書込
- **強度**: soft（sleep 1 による時間的分離）
- **緩和策**: swssconfig.sh が sleep 1 を入れているため通常は問題なし。ただし orchagent 起動が遅延した場合、SWITCH_TABLE エントリが Consumer のキューに積まれ次回ループで処理される

### 依存 3: 不明フィールドが同一エントリに存在する場合 → break で後続フィールドがスキップされる

`doAppSwitchTableTask()` では `kfvFieldsValues` を順に処理し、`switch_attribute_map` にも `switch_tunnel_attribute_map` にも存在しない属性を検出すると `break`（switchorch.cpp:617-623）。`fdb_aging_time` より**前に**不明フィールドがある場合、`fdb_aging_time` の適用が行われない。

- **方向**: 不明フィールド（fdb_aging_time より前）→ fdb_aging_time スキップ
- **強度**: medium（フィールド順序依存）
- **緩和策**: 有効なフィールドのみ書き込む。または `fdb_aging_time` を単独 SET で書き込む
- **evidence**: `switchorch.cpp:617-623`

### 依存 4: warm-reboot 時のセーフガード — setAgingFDB(0) による aging 一時無効化

warm-reboot で `checkRestartNoFreeze()` が false の場合（通常の warm-reboot パス）、`orchdaemon.cpp:1068` が `setAgingFDB(0)` を呼び aging を 0（無効化）にする。これは warm-reboot 中に MAC エントリが aging で失われないようにするための意図的な一時無効化であり、warm-reboot 完了後は再度 `swssconfig switch.json` で 600 秒が設定し直される。

- **方向**: warm-reboot 検出 → aging 0（無効）→ 再起動後 swssconfig → aging 600（復元）
- **強度**: hard（意図的設計）
- **緩和策**: warm-reboot 完了後に自動復元されるため、ユーザー操作不要

### 依存 5: SAI 失敗時の再試行

`sai_switch_api->set_switch_attribute` 失敗時は `handleSaiSetStatus` → `task_need_retry` → `retry = true` → `it++` で次ループ再試行（switchorch.cpp:723-728）。同一エントリの後続フィールドは break でスキップされる。

- **方向**: SAI 失敗 → 同一エントリの後続フィールド未適用 + 次ループ再試行
- **強度**: soft（一時的失敗は自動回復）
- **evidence**: `switchorch.cpp:723-728`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 強度 | 緩和策 |
|---|----------|------|------|--------|
| 1 | SAI create_switch → fdb_aging_time SAI set | 強制先行 | hard | orchagent が保証 |
| 2 | orchagent メインループ開始 → swssconfig switch.json 書込 | 時間的分離 | soft | sleep 1 により担保 |
| 3 | 不明フィールド（fdb_aging_time より前）→ スキップ | break による中断 | medium | 有効属性のみ書き込む |
| 4 | warm-reboot → aging 0 → 再起動後 aging 復元 | 意図的一時無効化 | hard | 自動復元 (swssconfig) |
| 5 | SAI 失敗 → retry ループ（後続フィールド一時未適用） | 一時スキップ + 自動再試行 | soft | SAI/ASIC が正常稼働していれば解消 |

---

evidence 一次ソース:
- `sonic-swss/orchagent/switchorch.cpp:42-54,595-748,1671-1688`
- `sonic-swss/orchagent/orchdaemon.cpp:1060-1079`
- `sonic-buildimage/dockers/docker-orchagent/switch.json.j2:34-49`
- `sonic-buildimage/dockers/docker-orchagent/swssconfig.sh:96-101`
- `sonic-buildimage/dockers/docker-orchagent/docker-init.j2:16`
