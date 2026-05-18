# queue-state Phase C — 暗黙参照テーブル (cross-refs)

slug: queue-state
phase: C
table: QUEUE_COUNTER_CAPABILITIES (STATE_DB)
writer: portsorch (initCounterCapabilities)

## 調査根拠

`sonic-swss/orchagent/portsorch.cpp:1850-1918` の `initCounterCapabilities()` 全行精読。
`sonic-swss/orchagent/flexcounterorch.cpp:95,276-281` の WRED_ECN_QUEUE FlexCounter 有効化ロジック確認。
`sonic-utilities/scripts/wredstat:196-204` および `utilities_common/portstat.py:290-330` の consumer 実装確認。

## 特定した暗黙参照

| 参照先 | DB / 場所 | 方向 | 契機 | 根拠コード |
|--------|-----------|------|------|-----------|
| SAI `sai_query_stats_capability(gSwitchId, SAI_OBJECT_TYPE_QUEUE, ...)` | SAI / プラットフォーム | READ | `initCounterCapabilities()` が orchagent 初期化時に 1 回呼び出す。クエリ結果に基づいて `isSupported` フラグを確定する | `portsorch.cpp:1882-1916` |
| `PORT_COUNTER_CAPABILITIES` | STATE_DB | WRITE（兄弟テーブル） | 同じ `initCounterCapabilities()` 内で `SAI_OBJECT_TYPE_PORT` ケイパビリティを問い合わせ、`WRED_ECN_PORT_*` キーを書き込む。QUEUE 側と PORT 側は独立して成否が決まる | `portsorch.cpp:1927-1970` |
| `FLEX_COUNTER_TABLE\|WRED_ECN_QUEUE` | CONFIG_DB | READ（間接） | `counterpoll wred-queue enable` により `FLEX_COUNTER_STATUS = enable` が書かれると `FlexCounterOrch` が `addWredQueueFlexCounters()` を呼ぶ。`QUEUE_COUNTER_CAPABILITIES.isSupported = "false"` のポートのカウンタは FlexCounter に登録されず COUNTERS_DB に出現しない | `flexcounterorch.cpp:276-281`, `portsorch.cpp:9574-9593` |
| `COUNTERS_DB COUNTERS:<queue_oid>` | COUNTERS_DB | READ（downstream consumer） | `wredstat` スクリプトが `COUNTERS_DB` から WRED/ECN カウンタ値を取得する際、当該フィールドが登録されていなければ `None` を返す。`QUEUE_COUNTER_CAPABILITIES.isSupported = "false"` の場合 `syncd` がポーリング対象に追加しないため `STATUS_NA` が表示される | `wredstat:198-204` |

## 補足

- `QUEUE_COUNTER_CAPABILITIES` は **書き手が `portsorch` のみ**の読み取り専用テーブル。consumer は `wredstat` / `portstat.py` / `counterpoll`。
- `isSupported` は orchagent 起動のたびに上書きされるが、SAI ケイパビリティクエリ結果が一貫していれば同じ値になる。
- `FLEX_COUNTER_TABLE|WRED_ECN_QUEUE` との関係は間接的：FlexCounter の enable/disable が `addWredQueueFlexCounters()` の呼び出し可否を制御し、その内部で `wred_queue_stat_manager.setCounterIdList()` が syncd 側の登録対象を変更する。`QUEUE_COUNTER_CAPABILITIES` 自体は FlexCounter の設定を読まない。
