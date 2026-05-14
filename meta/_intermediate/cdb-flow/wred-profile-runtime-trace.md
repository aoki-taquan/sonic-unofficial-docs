# WRED_PROFILE — 起動経路トレース (Direction B: CFG → APPL → SAI)

## 段階 1: Consumer 登録

`orchdaemon.cpp:375` で `CFG_WRED_PROFILE_TABLE_NAME` を QoS tables list に追加:

```cpp
CFG_WRED_PROFILE_TABLE_NAME,   // = "WRED_PROFILE"
```

`gQosOrch = new QosOrch(m_configDb, qos_tables)` (`orchdaemon.cpp:384`) で `CONFIG_DB` の `WRED_PROFILE` テーブルを購読。`QosOrch` は `orchList` に登録され (位置: `gQosOrch` as index 13 in `m_orchList`、`orchdaemon.cpp:500`)、メインループで `doTask()` が呼ばれる。

`QosOrch::doTask()` → `table_name == CFG_WRED_PROFILE_TABLE_NAME` → `handleWredProfileTable(consumer, tuple)` (`qosorch.cpp:877`) に委譲。

他コンシューマなし: `WRED_PROFILE` は QosOrch のみが購読する (cfgmgr 非経由)。
ただし `QUEUE.wred_profile` で名前参照されるため、`QosOrch::handleQueueTable()` が `task_need_retry` を発行して WRED_PROFILE エントリの先行作成を待つ (`qosorch.cpp:1864-1870`)。

## 段階 2: CFG → APPL 翻訳

`WRED_PROFILE` は **APP_DB への中間書き込みを行わない**。`QosOrch` が `CONFIG_DB` から直接読み取り、`WredMapHandler::convertFieldValuesToAttributes()` (`qosorch.cpp:585-762`) でフィールドを SAI 属性に変換する。

| CFG フィールド | 変換処理 | SAI 属性 |
|---|---|---|
| `ecn` | `ecn_map.at(value)` ルックアップ (`qosorch.cpp:36-44`) | `SAI_WRED_ATTR_ECN_MARK_MODE` |
| `wred_green_enable` | `convertBool()` → bool | `SAI_WRED_ATTR_GREEN_ENABLE` |
| `wred_yellow_enable` | `convertBool()` → bool | `SAI_WRED_ATTR_YELLOW_ENABLE` |
| `wred_red_enable` | `convertBool()` → bool | `SAI_WRED_ATTR_RED_ENABLE` |
| `green_min_threshold` / `max_threshold` | uint64 bytes | `SAI_WRED_ATTR_GREEN_MIN_THRESHOLD` / `MAX_THRESHOLD` |
| `yellow_min_threshold` / `max_threshold` | uint64 bytes | `SAI_WRED_ATTR_YELLOW_MIN_THRESHOLD` / `MAX_THRESHOLD` |
| `red_min_threshold` / `max_threshold` | uint64 bytes | `SAI_WRED_ATTR_RED_MIN_THRESHOLD` / `MAX_THRESHOLD` |
| `green_drop_probability` | uint64 (0-100%) | `SAI_WRED_ATTR_GREEN_DROP_PROBABILITY` |
| `yellow_drop_probability` | uint64 (0-100%) | `SAI_WRED_ATTR_YELLOW_DROP_PROBABILITY` |
| `red_drop_probability` | uint64 (0-100%) | `SAI_WRED_ATTR_RED_DROP_PROBABILITY` |

暗黙追加 (`addQosItem()`):
- `*_enable=true` かつ `*_drop_probability` 未指定 → `SAI_WRED_ATTR_*_DROP_PROBABILITY = 100` を自動補完 (`qosorch.cpp:836-850`)
- `SAI_WRED_ATTR_WEIGHT` = 0 を常に先頭に付与 (`qosorch.cpp:794`)

**2 フェーズ閾値適用**: 閾値変更で `現在 min > 新 max` または `現在 max < 新 min` になる属性は deferred リストへ退避し、残りを先に SAI に投入してから deferred を適用する (`qosorch.cpp:636-644`)。

## 段階 3: APPL → SAI (orchagent → syncd → SAI)

`WredMapHandler::addQosItem()` → `sai_wred_api->create_wred()` (`qosorch.cpp:855`):

```
sai_wred_api->create_wred(&sai_object, gSwitchId, attrs_count, attrs_data)
  SAI_WRED_ATTR_WEIGHT                         ← 0 (固定)
  SAI_WRED_ATTR_GREEN_ENABLE                   ← wred_green_enable
  SAI_WRED_ATTR_GREEN_MIN_THRESHOLD            ← green_min_threshold
  SAI_WRED_ATTR_GREEN_MAX_THRESHOLD            ← green_max_threshold
  SAI_WRED_ATTR_GREEN_DROP_PROBABILITY         ← green_drop_probability (省略時 100)
  SAI_WRED_ATTR_YELLOW_ENABLE / *_THRESHOLD / *_PROBABILITY  ← 同様
  SAI_WRED_ATTR_RED_ENABLE / *_THRESHOLD / *_PROBABILITY     ← 同様
  SAI_WRED_ATTR_ECN_MARK_MODE                 ← ecn フィールドから
```

ランタイム更新 (`modifyQosItem()`):
```
sai_wred_api->set_wred_attribute(sai_object, &attr)  // 属性個別に set
```

WRED 属性は SAI 上 **mutable** — `set_wred_attribute()` でランタイム変更可能 (`qosorch.cpp:774`)。
ただし閾値変更は 2 フェーズ適用が必要 (詳細: 段階 2)。

WRED オブジェクト作成後、`QUEUE.wred_profile` 参照が解決した時点で `applyWredProfileToQueue()` が呼ばれ、キューに紐付け:
```
sai_queue_api->set_queue_attribute(queue_oid, SAI_QUEUE_ATTR_WRED_PROFILE_ID = wred_oid)
```

## 段階 4: タイミング・副作用

- **config reload**: `QosOrch` は warm start 非対応 (warm start 分岐なし)。reload 時は WRED_PROFILE を再作成。`QUEUE.wred_profile` 参照が先に処理された場合は `task_need_retry` でキューに残り、WRED_PROFILE 作成後に再処理される。
- **runtime 変更 (SET)**: `modifyQosItem()` → `set_wred_attribute()` で差分適用。閾値変更は 2 フェーズ適用あり。`ecn` / `wred_*_enable` も runtime mutable。
- **DEL 操作**: `sai_wred_api->remove_wred(sai_object)` 後、`QOS_WRED_PROFILE_TABLE` の参照エントリを削除。QUEUE から先に unbind しないと SAI エラーになる可能性がある。
- **VoQ スイッチ**: `gMySwitchType == "voq"` の場合、`applyWredProfileToQueue()` が物理キューではなく VoQ ID を使用 (`qosorch.cpp:1709-1730`)。
- **AZURE_LOSSLESS 自動生成**: `qos_config.j2` テンプレートが起動時に `WRED_PROFILE|AZURE_LOSSLESS` を CONFIG_DB に書き込む (`qos_config.j2:489-506`)。`ecn=ecn_all`、RoCE キュー (queue 3, 4) に自動 bind。
- **db_migrator 変換**: 旧 DB の `wred_profile` フィールド値 `|AZURE_LOSSLESS|` 形式を `AZURE_LOSSLESS` に変換 (`db_migrator.py:574-585`)。

evidence: `sonic-swss/orchagent/qosorch.cpp`, `orchdaemon.cpp`
