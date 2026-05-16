# SWITCH fdb_aging_time — Phase B 書込み順依存スキャンノート

対象フィールド: `SWITCH_TABLE:switch` の `fdb_aging_time`
Consumer: `orchagent` / `SwitchOrch::doAppSwitchTableTask()` (`sonic-swss/orchagent/switchorch.cpp`)
スキャン範囲: `switch_attribute_map` 定義 (L42-54)、`doAppSwitchTableTask()` (L595-748)、`setAgingFDB()` (L1671-1687)、`orchdaemon.cpp:1068` 全行精読

---

## SAI fdb_aging_time 設定順序

### 1. フィールドマッピング定義

`switch_attribute_map` (switchorch.cpp:49) で `fdb_aging_time` は `SAI_SWITCH_ATTR_FDB_AGING_TIME` に静的マップされている:

```cpp
// switchorch.cpp:42-54
const map<string, sai_switch_attr_t> switch_attribute_map =
{
    {"fdb_unicast_miss_packet_action",      SAI_SWITCH_ATTR_FDB_UNICAST_MISS_PACKET_ACTION},
    {"fdb_broadcast_miss_packet_action",    SAI_SWITCH_ATTR_FDB_BROADCAST_MISS_PACKET_ACTION},
    {"fdb_multicast_miss_packet_action",    SAI_SWITCH_ATTR_FDB_MULTICAST_MISS_PACKET_ACTION},
    {"ecmp_hash_seed",                      SAI_SWITCH_ATTR_ECMP_DEFAULT_HASH_SEED},
    {"lag_hash_seed",                       SAI_SWITCH_ATTR_LAG_DEFAULT_HASH_SEED},
    {"fdb_aging_time",                      SAI_SWITCH_ATTR_FDB_AGING_TIME},
    ...
};
```

### 2. doAppSwitchTableTask() 内の fdb_aging_time 処理フロー

`doAppSwitchTableTask()` (switchorch.cpp:595-748) は APP_DB `SWITCH_TABLE:switch` の SET イベントを処理する。`fdb_aging_time` の処理フロー:

```
APP_DB SWITCH_TABLE:switch SET {fdb_aging_time: <sec>}
  │
  ├─ [1] switch_non_sai_attribute_set チェック
  │       → fdb_aging_time は非該当、次へ
  │
  ├─ [2] switch_attribute_map チェック (switchorch.cpp:618-622)
  │       → 該当: SAI_SWITCH_ATTR_FDB_AGING_TIME
  │
  ├─ [3] switch 文 (switchorch.cpp:642-705)
  │       case SAI_SWITCH_ATTR_FDB_AGING_TIME:
  │           attr.value.u32 = to_uint<uint32_t>(value);
  │           break;
  │       ※ capacity 確認不要 (ecmp/lag_hash_offset と異なりスキップなし)
  │       ※ invalid_attr / unsupported_attr セットなし
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

### 3. setAgingFDB() — orchdaemon 経由の直接呼び出しパス

`setAgingFDB()` (switchorch.cpp:1671-1687) は `doAppSwitchTableTask()` とは**別の**コードパスで呼ばれる。`orchdaemon.cpp:1068` で `gSwitchOrch->setAgingFDB(0)` が呼ばれ、shutdown 時に aging を 0（無効化）に設定する:

```cpp
// switchorch.cpp:1671-1687
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

**呼び出しパス**: `orchdaemon.cpp:1068` → `gSwitchOrch->setAgingFDB(0)` はシャットダウン時のクリーンアップシーケンスで発生する。

### 4. 処理順序の確定図

```
orchagent 起動
  │
  ├─ [1] SAI create_switch → gSwitchId 確定（orchagent main.cpp）
  │
  ├─ [2] SwitchOrch コンストラクタ起動（switchorch.cpp:148-175）
  │        ※ この時点で gSwitchId に対する SAI 問い合わせが可能になる
  │
  ├─ [3] orchagent メインループ開始（APP_DB / CONFIG_DB Consumer 購読）
  │
  └─ [4] APP_DB SWITCH_TABLE:switch に fdb_aging_time SET が来た場合
           doAppSwitchTableTask()
             ├─ attr.id  = SAI_SWITCH_ATTR_FDB_AGING_TIME
             ├─ attr.value.u32 = to_uint<uint32_t>(value)  ← uint32 変換のみ
             └─ sai_switch_api->set_switch_attribute(gSwitchId, &attr)
                  └─ SAI_STATUS_SUCCESS → SWSS_LOG_NOTICE ログ → erase（完了）
                     失敗 → handleSaiSetStatus → task_need_retry → it++ → 再試行

orchagent シャットダウン
  └─ [5] gSwitchOrch->setAgingFDB(0)（orchdaemon.cpp:1068）
           → SAI_SWITCH_ATTR_FDB_AGING_TIME = 0（aging 無効化）
```

---

## 検出した順序依存

### 依存 1: SAI create_switch → fdb_aging_time SET（強制先行）

`set_switch_attribute(gSwitchId, &attr)` の呼び出しには有効な `gSwitchId` が必要。`gSwitchId` は orchagent 起動時の `create_switch` で確定するため、orchagent が起動するまで `fdb_aging_time` は適用されない。

- **方向**: `create_switch` 完了 → `fdb_aging_time` SET
- **強度**: hard（gSwitchId なし = SAI 呼び出し不可）
- **緩和策**: orchagent が保証（ユーザー操作不要）
- **evidence**: `switchorch.cpp:22-27`（extern gSwitchId 宣言）

### 依存 2: 不明フィールドが同一エントリに存在する場合 → break で後続フィールドがスキップされる

`doAppSwitchTableTask()` では `kfvFieldsValues` を順に処理し、`switch_attribute_map` にも `switch_tunnel_attribute_map` にも存在しない属性を検出すると `break`（switchorch.cpp:616-633）。`fdb_aging_time` より**後に**不明フィールドを記述した場合は問題なし。`fdb_aging_time` より**前に**不明フィールドがある場合、`fdb_aging_time` の適用が行われない。

- **方向**: 不明フィールド（`fdb_aging_time` より前） → fdb_aging_time スキップ
- **強度**: medium（フィールド順序依存）
- **緩和策**: 有効なフィールドのみ書き込む。または `fdb_aging_time` を単独キーで SET する
- **evidence**: `switchorch.cpp:616-633`

### 依存 3: 不正なパケットアクション値 → break（fdb_aging_time も含む後続フィールドへ影響）

`fdb_unicast/broadcast/multicast_miss_packet_action` に `drop` / `forward` / `trap` 以外の値を書くと `invalid_attr = true` → `break` で以降の全フィールド（`fdb_aging_time` を含む）が適用されない（switchorch.cpp:647-660）。

- **方向**: 不正パケットアクション値（`fdb_aging_time` より前） → fdb_aging_time スキップ
- **強度**: medium
- **緩和策**: パケットアクション値は必ず `drop` / `forward` / `trap` を使用する
- **evidence**: `switchorch.cpp:647-660`, `switchorch.cpp:706-714`

### 依存 4: SAI 失敗時の再試行（retry ループ）

`sai_switch_api->set_switch_attribute` が失敗すると `handleSaiSetStatus` が呼ばれ、`task_need_retry` の場合は `retry = true` → `it++` で次のイベントループで再試行される（switchorch.cpp:723-729）。同一エントリの後続フィールドは再試行ループまでスキップされる（`break` で抜けるため）。

- **方向**: SAI 失敗 → 同一エントリの後続フィールド未適用 + 次ループで再試行
- **強度**: soft（一時的失敗は自動回復）
- **evidence**: `switchorch.cpp:723-735`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 強度 | 緩和策 |
|---|----------|------|------|--------|
| 1 | SAI create_switch → fdb_aging_time SAI set | 強制先行 | hard | orchagent が保証 |
| 2 | 不明フィールド（fdb_aging_time より前）→ スキップ | break による中断 | medium | 有効属性のみ書き込む |
| 3 | 不正パケットアクション値 → 以降フィールドスキップ | break による中断 | medium | drop/forward/trap のみ使用 |
| 4 | SAI 失敗 → retry ループ（後続フィールド一時未適用） | 一時スキップ + 自動再試行 | soft | SAI/ASIC が正常稼働していれば解消 |

---

注記: `switch.md` / `switch-table.md` が `docs/reference/config-db/` に存在しないため、
`<!-- ordering -->` ブロックのドキュメント挿入はスキップ（Task F Phase B skip 条件に合致）。
本ファイルは将来 switch 系ドキュメント新規作成時の参照用として保持する。
evidence 一次ソース: `sonic-swss/orchagent/switchorch.cpp:42-54,595-748,1671-1687`、`sonic-swss/orchagent/orchdaemon.cpp:1068`
