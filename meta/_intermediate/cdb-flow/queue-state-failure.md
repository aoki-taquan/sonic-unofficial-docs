# STATE_DB QUEUE_COUNTER_CAPABILITIES 失敗挙動・エラーパス調査メモ

調査日: 2026-05-18
対象: STATE_DB QUEUE_COUNTER_CAPABILITIES テーブル（portsorch::initCounterCapabilities）

## 調査対象ファイル

- `sonic-swss/orchagent/portsorch.cpp` — `initCounterCapabilities()` (L1850-1969)
- `sonic-utilities/scripts/wredstat` — consumer 側エラーハンドリング
- `sonic-utilities/utilities_common/portstat.py` — consumer 側エラーハンドリング（L297-330）

---

## 1. SAI クエリ失敗（第 1 回）

`portsorch.cpp:1882-1922` に記述されたメインフロー:

```cpp
sai_status_t status = sai_query_stats_capability(switchId, SAI_OBJECT_TYPE_QUEUE, &queue_stats_capability);
if (status == SAI_STATUS_BUFFER_OVERFLOW)
{
    qstat_cap_list.resize(queue_stats_capability.count, stat_initializer);
    queue_stats_capability.list = qstat_cap_list.data();
    status = sai_query_stats_capability(switchId, SAI_OBJECT_TYPE_QUEUE, &queue_stats_capability);
}
if (status == SAI_STATUS_SUCCESS)
{
    // ... isSupported = "true" 上書き ...
}
else
{
    SWSS_LOG_NOTICE("Queue stat capability get failed: WRED queue stats can not be enabled, rv:%d", status);
}
```

**挙動**:
- 第 1 回クエリが `SAI_STATUS_BUFFER_OVERFLOW` を返した場合 → リストをリサイズして第 2 回クエリを発行
- 第 1 回クエリが `SAI_STATUS_BUFFER_OVERFLOW` **以外**のエラーを返した場合 → 即座に else ブランチへ
- どちらの場合も最終的に `status != SAI_STATUS_SUCCESS` なら `SWSS_LOG_NOTICE` を出力し全フラグを `"false"` のまま確定
- **リカバー手段なし**: orchagent を再起動するまで再クエリは行われない

---

## 2. SAI クエリ失敗（第 2 回 — BUFFER_OVERFLOW リトライ失敗）

第 1 回が `SAI_STATUS_BUFFER_OVERFLOW` を返し、リスト拡張後の第 2 回クエリも失敗した場合:

- `status != SAI_STATUS_SUCCESS` → 同じ `SWSS_LOG_NOTICE` が出力され全フラグが `"false"` のまま
- ログ: `"Queue stat capability get failed: WRED queue stats can not be enabled, rv:<status_code>"`
- **自動リトライなし**: 再起動まで状態は変化しない

---

## 3. orchagent 起動前に consumer がアクセス

`initCounterCapabilities()` が呼ばれる前（PortsOrch 初期化完了前）に `wredstat` や `portstat.py` が STATE_DB を参照した場合:

- STATE_DB にキーが存在しない → `state_db.get()` / `db.get()` が `None` を返す
- `portstat.py:297-315`: `isSupported` が `None` の場合 → `!= "true"` 判定が成立し対応 SAI 統計を `counter_bucket_dict` から削除
- `wredstat`: COUNTERS_DB にキューカウンタが存在しないため `counter_data is None` → `STATUS_NA` 表示
- **影響**: WRED/ECN カウンタが表示されない（N/A）。orchagent 起動完了後に再実行すれば正常表示される

---

## 4. 中間状態の観測（初期化 → クエリ間の競合）

`initCounterCapabilities()` の冒頭で全 4 キーに `isSupported = "false"` を書き込み、その後 SAI クエリを実行して成功分を `"true"` に上書きする（2 ステップ書き込み）。この間に consumer が参照すると:

- 全フラグが `"false"` の中間状態を観測する可能性がある
- ただし `initCounterCapabilities()` は orchagent 起動シーケンス中の 1 回のみ実行され、通常運用時の動的更新は発生しない
- SAI クエリは同期呼び出しのため中間状態の継続時間は SAI 応答待ち時間（通常ミリ秒未満）

---

## 5. WRED_ECN_QUEUE_WRED_DROPPED_BYTE_COUNTER が STATE_DB に出ない

既存の `消費者` セクションでは `wredstat` が `COUNTERS_DB` から WRED カウンタを読む点が述べられているが、FlexCounter に登録されないと COUNTERS_DB にも存在しない:

- `isSupported = "false"` → `FlexCounterOrch::addWredQueueFlexCounters()` 内でそのキューは `setCounterIdList()` 対象外
- 結果: COUNTERS_DB に `SAI_QUEUE_STAT_WRED_DROPPED_BYTES` キーが出現しない
- `wredstat` が `counter_data is None` → `STATUS_NA` 表示（`wredstat:202-203`）

---

## 6. 失敗挙動サマリ

| 条件 | ログ | STATE_DB への影響 | リカバー |
|------|------|------------------|---------|
| SAI クエリ初回失敗（BUFFER_OVERFLOW 以外） | SWSS_LOG_NOTICE | 全 4 キーが `"false"` のまま | orchagent 再起動 |
| SAI クエリ BUFFER_OVERFLOW → リトライ失敗 | SWSS_LOG_NOTICE | 全 4 キーが `"false"` のまま | orchagent 再起動 |
| orchagent 初期化完了前に consumer が参照 | なし（consumer 側で N/A 表示） | STATE_DB にキーが存在しない | orchagent 起動完了後に再実行 |
| 一部キーのみ SAI 未サポート | なし（正常フロー） | 未サポートキーは `"false"`、サポートキーは `"true"` | N/A（仕様通り） |
| FlexCounter 未登録（isSupported = false） | なし | COUNTERS_DB に対応カウンタが出現しない | N/A（isSupported true にするにはプラットフォーム変更が必要） |
