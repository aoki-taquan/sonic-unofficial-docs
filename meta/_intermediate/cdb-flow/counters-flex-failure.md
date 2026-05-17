# counters-flex Phase D — 失敗挙動・retry / recovery スキャンノート

Generated: 2026-05-17  
Target doc: docs/reference/config-db/counters-flex.md

対象テーブル: `FLEX_COUNTER_DB|FLEX_COUNTER_TABLE|<group>|<oid>` (`*_COUNTER_ID_LIST` / `*_ATTR_ID_LIST` フィールド)  
Consumer: `orchagent` — `FlexCounterOrch::doTask()` + `PortsOrch::generateXxxMap()` / `addXxxFlexCounters()`  
スキャン範囲: `flexcounterorch.cpp:145-418`、`flex_counter_manager.cpp:203-260`、`portsorch.cpp:9102-9165`

---

## 失敗パターン一覧

### 1. 無効グループキー → 即削除・retry なし

`FLEX_COUNTER_TABLE` に `flexCounterGroupMap` 未登録のキーが書かれた場合:

```cpp
// flexcounterorch.cpp:183-188
if (!flexCounterGroupMap.count(key))
{
    SWSS_LOG_NOTICE("Invalid flex counter group input, %s", key.c_str());
    consumer.m_toSync.erase(it++);
    continue;
}
```

- **挙動**: `NOTICE` ログ出力後エントリ即削除。retry なし
- **復旧**: 正しいキーで再書き込みが必要
- **per-OID エントリへの影響**: なし（FLEX_COUNTER_DB は変更されない）

### 2. `allPortsReady() = false` → m_toSync 保留（自動回復）

PortsOrch の初期化が完了していない間、`FlexCounterOrch::doTask()` は全エントリを `m_toSync` に残してリターンする（flexcounterorch.cpp:164-167）。

- **挙動**: エントリが `m_toSync` に保持され、`allPortsReady()` が true になった後の最初のイベントループで自動処理される
- **上限**: なし（PortInitDone が発行されるまで永遠に保留）
- **復旧**: 自動（portsyncd が PortInitDone を発行した時点で一括処理）

### 3. Warm-reboot 遅延（60 秒）→ m_toSync 全保留

Warm-reboot 時にコンストラクタ（flexcounterorch.cpp:127-136）が 60 秒タイマーを起動し、タイムアウトまで `doTask()` が全リターンする。

- **挙動**: FLEX_COUNTER_TABLE へのすべての SET/DEL が 60 秒間処理されない
- **上限**: `FLEX_COUNTER_DELAY_SEC = 60` 秒（ハードコード定数）
- **復旧**: 自動（60 秒後に `doTask(SelectableTimer&)` が `m_delayTimerExpired = true` に変更）
- **cold-start では発生しない**: コンストラクタで即 `m_delayTimerExpired = true`

### 4. 未サポートフィールド → silent skip

`FLEX_COUNTER_STATUS` / `POLL_INTERVAL` / `BULK_CHUNK_SIZE` 以外のフィールドが含まれている場合（flexcounterorch.cpp:396-398）:

- **挙動**: `SWSS_LOG_NOTICE("Unsupported field %s", field.c_str())` 出力のみ。エントリは削除されず、他フィールドの処理は継続
- **per-OID エントリへの影響**: なし

### 5. `setCounterIdList()` → Redis 操作失敗でクラッシュ

`FlexCounterManager::setCounterIdList()` は Redis へ書き込む `startFlexCounterPolling()` を呼び出す。内部で `RedisReply` 例外が発生した場合（Redis 接続断等）、これはキャッチされず orchagent プロセスがクラッシュする。

- **挙動**: orchagent クラッシュ → supervisor が再起動するまで FlexCounter 全停止
- **復旧**: supervisor (supervisord) による orchagent 自動再起動後に warm-reboot 相当の遅延（60 秒）ありで再初期化
- **頻度**: 通常は発生しない（Redis 接続は systemd socket activation で確保される）

### 6. 未対応 CounterType → SWSS_LOG_ERROR + silent return

`FlexCounterManager::setCounterIdList()` の `counter_id_field_lookup.find(counter_type)` が end() を返した場合（flex_counter_manager.cpp:215-219）:

```cpp
SWSS_LOG_ERROR("Could not update flex counter id list for group '%s': counter type not found.",
               group_name.c_str());
return;
```

- **挙動**: `ERROR` ログ出力後、関数を return。FLEX_COUNTER_DB への書き込みは行われない
- **復旧**: orchagent 実装バグのため、コード修正なしに回復不可
- **実運用での発生**: 通常発生しない（`counter_id_field_lookup` は静的に初期化される）

### 7. `m_isPortCounterMapGenerated` ガードによる silent no-op

`generatePortCounterMap()` 等が既に一度実行されている状態で再度 `enable` を書いた場合:

- **挙動**: ガードフラグが true のため関数先頭で即 return。FLEX_COUNTER_DB は変更されない
- **ログ**: なし（silent）
- **注意**: `disable` → `enable` の繰り返しでは per-OID エントリが再生成されない。これはバグではなく設計（初期化コスト削減）

### 8. DEVICE_METADATA 読み込み失敗 → ERROR ログ + デフォルト値使用

コンストラクタ（flexcounterorch.cpp:110-124）で `create_only_config_db_buffers` を読み込む際に `std::system_error` が発生した場合:

```cpp
catch(const std::system_error& e)
{
    SWSS_LOG_ERROR("System error reading create_only_config_db_buffers: %s", e.what());
}
```

- **挙動**: `ERROR` ログ出力後、`m_createOnlyConfigDbBuffers = false`（デフォルト）で初期化継続
- **影響**: QUEUE/PG カウンタが「全ポート・全キュー」対象で登録される（バッファプロファイル設定に依存しないモード）

---

## 失敗パターンサマリ

| # | トリガー | ログレベル | FLEX_COUNTER_DB への影響 | 自動回復 | 証拠 |
|---|---------|---------|----------------------|---------|------|
| 1 | 無効グループキー | NOTICE | なし | なし（再書き込みが必要） | flexcounterorch.cpp:183 |
| 2 | `allPortsReady() = false` | なし | 保留 | 自動（PortInitDone 後） | flexcounterorch.cpp:164 |
| 3 | Warm-reboot 60 秒タイマー | NOTICE（タイムアウト後） | 保留 | 自動（60 秒後） | flexcounterorch.cpp:128-136 |
| 4 | 未サポートフィールド | NOTICE | なし | 不要（他フィールドは継続） | flexcounterorch.cpp:396 |
| 5 | Redis 接続断 | — (例外) | 不定（orchagent クラッシュ） | supervisor 再起動後 | flex_counter_manager.cpp |
| 6 | 未対応 CounterType | ERROR | なし（書き込みスキップ） | なし（コード修正要） | flex_counter_manager.cpp:216 |
| 7 | 既に `m_isXxxMapGenerated = true` | なし | なし | 不要（設計上の冪等） | portsorch.cpp:generateXxxMap |
| 8 | DEVICE_METADATA 読み込み失敗 | ERROR | なし | 自動（デフォルト false で継続） | flexcounterorch.cpp:122 |
